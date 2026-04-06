"""
Context Engine 重试机制

提供可配置的重试逻辑，用于处理 transient errors。
"""

import time
import random
from typing import Callable, Type, Tuple, Any, Optional
from functools import wraps
from engine.logger import Logger


class RetryError(Exception):
    """重试失败异常"""
    def __init__(self, message: str, attempts: int, last_exception: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    logger: Logger = None
):
    """重试装饰器

    Args:
        max_attempts: 最大重试次数
        base_delay: 初始延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        backoff_factor: 退避因子（指数退避）
        jitter: 是否添加随机抖动
        retry_on: 需要重试的异常类型
        logger: 日志记录器

    Example:
        @retry(max_attempts=3, retry_on=(sqlite3.OperationalError,))
        def database_operation():
            # 执行数据库操作
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            _logger = logger if logger else Logger()

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    # 最后一次尝试失败，抛出异常
                    if attempt >= max_attempts:
                        _logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            error_type=type(e).__name__,
                            error_message=str(e),
                            attempts=attempt
                        )
                        raise RetryError(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            attempts=max_attempts,
                            last_exception=e
                        ) from e

                    # 计算延迟时间（指数退避 + 抖动）
                    delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    _logger.warning(
                        f"Function {func.__name__} failed, retrying...",
                        error_type=type(e).__name__,
                        error_message=str(e),
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay_seconds=round(delay, 2)
                    )

                    time.sleep(delay)

            # 理论上不会到这里
            raise RetryError(
                f"Function {func.__name__} failed after {max_attempts} attempts",
                attempts=max_attempts,
                last_exception=last_exception
            )

        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    default: Any = None,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    logger: Logger = None,
    log_errors: bool = True
) -> Any:
    """安全执行函数，捕获异常并返回默认值

    Args:
        func: 要执行的函数
        default: 失败时返回的默认值
        retry_on: 需要捕获的异常类型
        logger: 日志记录器
        log_errors: 是否记录错误

    Returns:
        函数结果或默认值

    Example:
        result = safe_execute(
            lambda: parse_file(path),
            default=None,
            logger=logger
        )
    """
    try:
        return func()
    except retry_on as e:
        if log_errors:
            _logger = logger if logger else Logger()
            _logger.error(
                f"Safe execution failed for function",
                error_type=type(e).__name__,
                error_message=str(e),
                function_name=getattr(func, '__name__', 'unknown')
            )
        return default


class CircuitBreaker:
    """熔断器模式，防止级联失败

    当失败率超过阈值时，熔断器打开，直接拒绝请求。
    经过一定时间后，熔断器进入半开状态，允许少量请求通过测试。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
        logger: Logger = None
    ):
        """初始化熔断器

        Args:
            failure_threshold: 失败阈值（连续失败次数）
            recovery_timeout: 恢复超时时间（秒）
            expected_exception: 预期的异常类型
            logger: 日志记录器
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.logger = logger or Logger()

        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过熔断器调用函数

        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数结果

        Raises:
            Exception: 熔断器打开时抛出异常
        """
        if self._is_open():
            self.logger.warning(
                f"Circuit breaker is OPEN, rejecting call to {getattr(func, '__name__', 'unknown')}"
            )
            raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _is_open(self) -> bool:
        """检查熔断器是否打开"""
        if self.state == 'open':
            # 检查是否可以进入半开状态
            if self.last_failure_time and \
               time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'half-open'
                self.logger.info("Circuit breaker transitioned to HALF-OPEN")
                return False
            return True
        return False

    def _on_success(self):
        """成功时更新状态"""
        self.failure_count = 0
        self.last_failure_time = None
        if self.state == 'half-open':
            self.state = 'closed'
            self.logger.info("Circuit breaker transitioned to CLOSED")

    def _on_failure(self):
        """失败时更新状态"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            if self.state != 'open':
                self.state = 'open'
                self.logger.warning(
                    f"Circuit breaker transitioned to OPEN after {self.failure_count} failures"
                )

    def get_state(self) -> str:
        """获取熔断器状态"""
        return self.state

    def get_stats(self) -> dict:
        """获取熔断器统计信息"""
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time
        }


__all__ = ['retry', 'safe_execute', 'CircuitBreaker', 'RetryError']

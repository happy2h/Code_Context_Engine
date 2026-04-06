"""
Context Engine 日志模块

提供结构化日志记录，支持不同日志级别和 JSON 输出。
"""

import logging
import json
import sys
import time
from typing import Any, Dict
from contextlib import contextmanager
from functools import wraps

# 日志级别映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}


class ContextFormatter(logging.Formatter):
    """结构化日志格式化器，支持 JSON 输出"""

    def __init__(self, json_output: bool = False):
        super().__init__()
        self.json_output = json_output

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        if self.json_output:
            # JSON 格式输出
            log_data = {
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.%Z', time.localtime(record.created)),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'line': record.lineno
            }

            # 添加异常信息
            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)

            # 添加额外字段
            if hasattr(record, 'extra'):
                log_data.update(record.extra)

            return json.dumps(log_data, ensure_ascii=False)
        else:
            # 文本格式输出
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
            level = record.levelname.ljust(8)
            name = record.name.ljust(20)
            message = record.getMessage()

            result = f"{timestamp} | {level} | {name} | {message}"

            # 添加异常信息
            if record.exc_info:
                result += f"\n{self.formatException(record.exc_info)}"

            return result


class Logger:
    """日志管理器"""

    _instance = None
    _initialized = False

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化日志管理器"""
        if not self._initialized:
            self.logger = logging.getLogger('context-engine')
            self.logger.setLevel(logging.INFO)

            # 默认处理器
            handler = logging.StreamHandler(sys.stdout)
            formatter = ContextFormatter(json_output=False)
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

            self._initialized = True

    @staticmethod
    def setup(level: str = 'INFO', json_output: bool = False,
              output_file: str = None) -> 'Logger':
        """配置日志系统

        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            json_output: 是否使用 JSON 格式输出
            output: 可选，输出文件路径
        """
        instance = Logger()

        # 清除现有处理器
        instance.logger.handlers.clear()

        # 设置日志级别
        log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
        instance.logger.setLevel(log_level)

        # 添加控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = ContextFormatter(json_output=json_output)
        console_handler.setFormatter(console_formatter)
        instance.logger.addHandler(console_handler)

        # 添加文件处理器（如果指定）
        if output_file:
            file_handler = logging.FileHandler(output_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_formatter = ContextFormatter(json_output=json_output)
            file_handler.setFormatter(file_formatter)
            instance.logger.addHandler(file_handler)

        return instance

    def debug(self, msg: str, **kwargs):
        """记录 DEBUG 级别日志"""
        self._log(logging.DEBUG, msg, kwargs)

    def info(self, msg: str, **kwargs):
        """记录 INFO 级别日志"""
        self._log(logging.INFO, msg, kwargs)

    def warning(self, msg: str, **kwargs):
        """记录 WARNING 级别日志"""
        self._log(logging.WARNING, msg, kwargs)

    def error(self, msg: str, exc_info=None, **kwargs):
        """记录 ERROR 级别日志

        Args:
            msg: 日志消息
            exc_info: 异常信息
            **kwargs: 额外字段
        """
        self._log(logging.ERROR, msg, kwargs, exc_info)

    def critical(self, msg: str, exc_info=None, **kwargs):
        """记录 CRITICAL 级别日志

        Args:
            msg: 日志消息
            exc_info: 异常信息
            **kwargs: 额外字段
        """
        self._log(logging.CRITICAL, msg, kwargs, exc_info)

    def _log(self, level: int, msg: str, extra: Dict[str, Any] = None, exc_info=None):
        """内部日志记录方法"""
        if extra:
            self.logger.log(level, msg, extra=extra, exc_info=exc_info)
        else:
            self.logger.log(level, msg, exc_info=exc_info)


# 性能监控上下文管理器
@contextmanager
def performance_timer(logger: Logger, operation: str, **kwargs):
    """性能监控上下文管理器，记录操作耗时

    Args:
        logger: 日志记录器
        operation: 操作名称
        **kwargs: 额外字段

    Example:
        with performance_timer(logger, "index_file", file="test.py"):
            # 执行索引操作
            pass
    """
    start_time = time.time()
    logger.debug(f"Starting {operation}", **kwargs)

    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"Completed {operation}", duration_ms=round(duration * 1000, 2), **kwargs)


# 性能监控装饰器
def log_performance(logger: Logger = None, operation: str = None):
    """性能监控装饰器，记录函数执行耗时

    Args:
        logger: 日志记录器（如果为 None，使用默认实例）
        operation: 操作名称（如果为 None，使用函数名）

    Example:
        @log_performance()
        def parse_file(path):
            # 解析文件
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger if logger else Logger()
            _operation = operation if operation else func.__name__

            start_time = time.time()
            _logger.debug(f"Starting {_operation}")

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                _logger.debug(
                    f"Completed {_operation}",
                    duration_ms=round(duration * 1000, 2),
                    success=True
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                _logger.error(
                    f"Failed {_operation}: {str(e)}",
                    duration_ms=round(duration * 1000, 2),
                    success=False,
                    exc_info=sys.exc_info()
                )
                raise

        return wrapper
    return decorator


# 异常日志记录装饰器
def log_errors(logger: Logger = None, reraise: bool = True):
    """异常日志记录装饰器，捕获并记录异常

    Args:
        logger: 日志记录器（如果为 None，使用默认实例）
        reraise: 是否重新抛出异常

    Example:
        @log_errors(reraise=False)
        def risky_operation():
            # 可能失败的操作
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger if logger else Logger()

            try:
                return func(*args, **kwargs)
            except Exception as e:
                _logger.error(
                    f"Exception in {func.__name__}",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=sys.exc_info()
                )
                if reraise:
                    raise

        return wrapper
    return decorator


# 导出函数和类
__all__ = [
    'Logger',
    'performance_timer',
    'log_performance',
    'log_errors'
]

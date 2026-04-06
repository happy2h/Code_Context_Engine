"""
Context Engine 配置管理

支持环境变量和 .env 文件配置。
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """配置管理类"""

    @staticmethod
    def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量，优先从 .env 文件读取"""
        # 先尝试从 .env 文件读取
        env_file = Path.cwd() / ".env"
        if env_file.exists():
            import dotenv
            dotenv.load_dotenv(env_file)

        return os.environ.get(name, default)

    @staticmethod
    def get_db_path(repo_path: str | None = None) -> str:
        """获取数据库文件路径"""
        # 如果指定了 CE_DB_PATH，直接使用
        db_path = Config.get_env("CE_DB_PATH")
        if db_path:
            return os.path.expanduser(db_path)

        # 否则根据仓库路径生成哈希作为文件名
        if repo_path:
            import hashlib
            repo_hash = hashlib.sha256(repo_path.encode()).hexdigest()[:16]
            db_dir = os.path.expanduser("~/.context")  # 修正：之前写的是 ~/.context-engine
            os.makedirs(db_dir, exist_ok=True)
            return os.path.join(db_dir, f"{repo_hash}.db")

        return os.path.expanduser("~/.context-engine/default.db")

    @staticmethod
    def get_repo_root() -> str:
        """获取索引的仓库根目录"""
        repo_root = Config.get_env("CE_REPO_ROOT")
        if repo_root:
            return repo_root
        return os.getcwd()

    @staticmethod
    def get_exclude_patterns() -> str:
        """获取排除目录/文件模式"""
        return Config.get_env("CE_EXCLUDE_PATTERNS", "node_modules,__pycache__,.git,dist,build")

    @staticmethod
    def get_max_file_size() -> int:
        """获取最大文件大小（字节）"""
        size = Config.get_env("CE_MAX_FILE_SIZE", "500000")
        return int(size)

    @staticmethod
    def get_parallel_workers() -> int:
        """获取并行解析的线程数"""
        workers = Config.get_env("CE_PARALLEL_WORKERS", "4")
        return int(workers)

    @staticmethod
    def get_watcher_debounce() -> float:
        """获取文件变更防抖时间（秒）"""
        debounce = Config.get_env("CE_WATCHER_DEBOUNCE", "0.5")
        return float(debounce)

    @staticmethod
    def get_log_level() -> str:
        """获取日志级别"""
        return Config.get_env("CE_LOG_LEVEL", "INFO")

    @staticmethod
    def get_enable_cache() -> bool:
        """是否启用查询缓存"""
        value = Config.get_env("CE_ENABLE_CACHE", "true")
        return value.lower() in ('true', '1', 'yes')

    @staticmethod
    def get_cache_size() -> int:
        """获取缓存大小（条目数）"""
        size = Config.get_env("CE_CACHE_SIZE", "1000")
        return int(size)

    @staticmethod
    def get_json_logs() -> bool:
        """是否使用 JSON 格式输出日志"""
        value = Config.get_env("CE_JSON_LOGS", "false")
        return value.lower() in ('true', '1', 'yes')

    @staticmethod
    def get_log_file() -> str | None:
        """获取日志文件路径（可选）"""
        return Config.get_env("CE_LOG_FILE", None)

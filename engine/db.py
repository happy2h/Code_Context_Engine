"""
Context Engine 数据库层

提供 SQLite 数据库连接、Schema 初始化和 CRUD 操作。
"""

import sqlite3
import os
import time
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class FileRecord:
    """文件记录"""
    id: int
    path: str
    abs_path: str
    lang: str
    content_hash: str
    size_bytes: int
    parsed_at: float
    line_count: int
    status: str


@dataclass
class SymbolRecord:
    """符号记录"""
    id: int
    file: str
    lang: str
    name: str
    kind: str
    signature: Optional[str]
    docstring: Optional[str]
    body: str
    line_start: int
    line_end: int
    col_start: int
    col_end: int
    parent_name: Optional[str]
    is_exported: int
    complexity: int

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "file": self.file,
            "lang": self.lang,
            "name": self.name,
            "kind": self.kind,
            "signature": self.signature,
            "docstring": self.docstring,
            "body": self.body,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "col_start": self.col_start,
            "col_end": self.col_end,
            "parent": self.parent_name,
            "is_exported": bool(self.is_exported),
            "complexity": self.complexity
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """转换为简要字典（不含 body）"""
        return {
            "id": self.id,
            "file": self.file,
            "lang": self.lang,
            "name": self.name,
            "kind": self.kind,
            "signature": self.signature,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "parent": self.parent_name,
            "is_exported": bool(self.is_exported)
        }


class Database:
    """数据库管理器"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_schema()
        self._optimize_database()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _init_schema(self):
        """初始化数据库 Schema"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 创建 files 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL UNIQUE,
                    abs_path TEXT NOT NULL,
                    lang TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    parsed_at REAL NOT NULL,
                    line_count INTEGER NOT NULL,
                    status TEXT DEFAULT 'ok'
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_files_lang ON files(lang)
            """)

            # 创建 symbols 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    signature TEXT,
                    docstring TEXT,
                    body TEXT NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER NOT NULL,
                    col_start INTEGER NOT NULL,
                    col_end INTEGER NOT NULL,
                    parent_name TEXT,
                    is_exported INTEGER DEFAULT 0,
                    complexity INTEGER DEFAULT 0,
                    UNIQUE(file_id, name, line_start)
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbols_parent ON symbols(parent_name)
            """)

            # 创建 call_edges 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS call_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caller_id INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
                    callee_name TEXT NOT NULL,
                    callee_id INTEGER REFERENCES symbols(id),
                    call_line INTEGER,
                    call_type TEXT DEFAULT 'direct',
                    UNIQUE(caller_id, callee_name, call_line)
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_edges_caller ON call_edges(caller_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_edges_callee ON call_edges(callee_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_edges_name ON call_edges(callee_name)
            """)

            # 创建 FTS5 全文索引虚拟表
            # 使用 external content table 模式
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
                    name,
                    signature,
                    docstring,
                    content='symbols',
                    content_rowid='id'
                )
            """)

            # 创建触发器：INSERT 时自动同步到 FTS5
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS symbols_ai AFTER INSERT ON symbols BEGIN
                    INSERT INTO symbols_fts(rowid, name, signature, docstring)
                    VALUES (new.id, new.name, new.signature, new.docstring);
                END
            """)

            # 创建触发器：DELETE 时自动从 FTS5 删除
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS symbols_ad AFTER DELETE ON symbols BEGIN
                    DELETE FROM symbols_fts WHERE rowid = old.id;
                END
            """)

            # 创建触发器：UPDATE 时自动更新 FTS5
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS symbols_au AFTER UPDATE ON symbols BEGIN
                    DELETE FROM symbols_fts WHERE rowid = old.id;
                    INSERT INTO symbols_fts(rowid, name, signature, docstring)
                    VALUES (new.id, new.name, new.signature, new.docstring);
                END
            """)

            # 创建 index_meta 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS index_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # 初始化元数据
            cursor.execute("""
                INSERT OR IGNORE INTO index_meta (key, value)
                VALUES ('schema_version', '1')
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO index_meta (key, value)
                VALUES ('engine_version', '1.0.0')
            """)

            conn.commit()

    def _optimize_database(self):
        """优化数据库配置，启用 WAL 模式等"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 启用 WAL 模式（Write-Ahead Logging），提高并发性能
            cursor.execute("PRAGMA journal_mode = WAL")

            # 设置 WAL 自动检查点
            cursor.execute("PRAGMA wal_autocheckpoint = 1000")

            # 启用外键约束
            cursor.execute("PRAGMA foreign_keys = ON")

            # 设置同步模式为 NORMAL（平衡性能和数据安全）
            cursor.execute("PRAGMA synchronous = NORMAL")

            # 设置缓存大小（页数，默认 -2000 即约 2MB）
            cursor.execute("PRAGMA cache_size = -2000")

            # 设置内存映射 I/O（提升大文件读取性能）
            cursor.execute("PRAGMA mmap_size = 30000000000")  # 约 30GB

            # 优化临时表存储
            cursor.execute("PRAGMA temp_store = MEMORY")

            conn.commit()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # 启用外键约束，确保级联删除正常工作
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def execute(self, sql: str, params: List[Any] = None) -> List[sqlite3.Row]:
        """执行 SQL 查询"""
        params = params or []
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchall()

    def fetchone(self, sql: str, params: List[Any] = None) -> Optional[sqlite3.Row]:
        """查询单条记录"""
        params = params or []
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchone()

    def fetchall(self, sql: str, params: List[Any] = None) -> List[sqlite3.Row]:
        """查询所有记录"""
        params = params or []
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchall()

    # Files 表操作
    def insert_file(self, path: str, abs_path: str, lang: str,
                    content_hash: str, size_bytes: int, line_count: int,
                    status: str = 'ok') -> int:
        """插入文件记录，返回文件 ID"""
        with self.transaction() as cursor:
            cursor.execute("""
                INSERT INTO files (path, abs_path, lang, content_hash, size_bytes,
                                  parsed_at, line_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [path, abs_path, lang, content_hash, size_bytes,
                   time.time(), line_count, status])
            return cursor.lastrowid

    def get_file(self, path: str) -> Optional[FileRecord]:
        """根据路径获取文件记录"""
        row = self.fetchone("SELECT * FROM files WHERE path = ?", [path])
        if row:
            return FileRecord(**dict(row))
        return None

    def get_file_by_id(self, file_id: int) -> Optional[FileRecord]:
        """根据 ID 获取文件记录"""
        row = self.fetchone("SELECT * FROM files WHERE id = ?", [file_id])
        if row:
            return FileRecord(**dict(row))
        return None

    def delete_file(self, path: str):
        """删除文件记录（级联删除符号和调用边）"""
        with self.transaction() as cursor:
            cursor.execute("DELETE FROM files WHERE path = ?", [path])

    def get_all_files(self) -> List[FileRecord]:
        """获取所有文件记录"""
        rows = self.fetchall("SELECT * FROM files")
        return [FileRecord(**dict(r)) for r in rows]

    # Symbols 表操作
    def bulk_insert_symbols(self, file_id: int, symbols: List[Dict[str, Any]]):
        """批量插入符号记录"""
        if not symbols:
            return

        with self.transaction() as cursor:
            for sym in symbols:
                cursor.execute("""
                    INSERT OR REPLACE INTO symbols
                    (file_id, name, kind, signature, docstring, body,
                     line_start, line_end, col_start, col_end,
                     parent_name, is_exported, complexity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    file_id,
                    sym['name'],
                    sym['kind'],
                    sym.get('signature'),
                    sym.get('docstring'),
                    sym['body'],
                    sym['line_start'],
                    sym['line_end'],
                    sym['col_start'],
                    sym['col_end'],
                    sym.get('parent_name'),
                    sym.get('is_exported', 0),
                    sym.get('complexity', 0)
                ])

    def get_symbols_by_file(self, file_id: FileRecord | str | int, include_body: bool = True) -> List[SymbolRecord]:
        """获取文件的所有符号"""
        if isinstance(file_id, FileRecord):
            file_id = file_id.id

        body_sql = ", body" if include_body else ", '' AS body"
        sql = f"""
            SELECT s.id, f.path AS file, f.lang AS lang, s.name, s.kind, s.signature,
                   s.docstring{body_sql}, s.line_start, s.line_end, s.col_start,
                   s.col_end, s.parent_name, s.is_exported, s.complexity
            FROM symbols s
            JOIN files f ON f.id = s.file_id
            WHERE s.file_id = ?
        """
        rows = self.fetchall(sql, [file_id])
        return [SymbolRecord(**dict(r)) for r in rows]

    # Call edges 表操作
    def bulk_insert_call_edges(self, call_edges: List[Dict[str, Any]]):
        """批量插入调用边"""
        if not call_edges:
            return

        with self.transaction() as cursor:
            for edge in call_edges:
                cursor.execute("""
                    INSERT OR REPLACE INTO call_edges
                    (caller_id, callee_name, callee_id, call_line, call_type)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    edge['caller_id'],
                    edge['callee_name'],
                    edge.get('callee_id'),
                    edge.get('call_line'),
                    edge.get('call_type', 'direct')
                ])

    # Meta 表操作
    def get_meta(self, key: str, default: str = None) -> Optional[str]:
        """获取元数据"""
        row = self.fetchone("SELECT value FROM index_meta WHERE key = ?", [key])
        if row:
            return row['value']
        return default

    def set_meta(self, key: str, value: str):
        """设置元数据"""
        with self.transaction() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO index_meta (key, value) VALUES (?, ?)
            """, [key, value])

    def get_index_status(self) -> Dict[str, Any]:
        """获取索引状态"""
        status = {
            "schema_version": self.get_meta("schema_version"),
            "engine_version": self.get_meta("engine_version"),
            "repo_root": self.get_meta("repo_root"),
            "created_at": self.get_meta("created_at"),
            "last_full_index": self.get_meta("last_full_index"),
        }

        # 统计数据
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM files")
            status["total_files"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM symbols")
            status["total_symbols"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM call_edges")
            status["total_call_edges"] = cursor.fetchone()[0]

        return status

"""
Context Engine 查询引擎

提供符号查询、调用图查询等功能。
"""

import os
import hashlib
import json
from typing import Optional, List, Dict, Any
from collections import OrderedDict
from engine.db import Database, SymbolRecord, FileRecord


class LRUCache:
    """简单的 LRU 缓存实现"""

    def __init__(self, max_size: int = 1000):
        """初始化缓存

        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _make_key(self, *args) -> str:
        """生成缓存键"""
        # 使用参数的 JSON 表示生成哈希键
        key_parts = []
        for arg in args:
            if arg is None:
                key_parts.append('None')
            elif isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                key_parts.append(json.dumps(arg, sort_keys=True))
        key_str = '|'.join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            self.hits += 1
            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            return self.cache[key]
        self.misses += 1
        return None

    def put(self, key: str, value: Any):
        """设置缓存值"""
        # 如果键已存在，删除旧值
        if key in self.cache:
            del self.cache[key]

        # 添加新值
        self.cache[key] = value

        # 如果超过最大大小，删除最旧的条目
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self):
        """清空缓存"""
        self.cache.clear.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate * 100, 2)
        }


class QueryEngine:
    """查询引擎"""

    def __init__(self, db_path: str, enable_cache: bool = True, cache_size: int = 1000):
        """初始化查询引擎

        Args:
            db_path: 数据库文件路径
            enable_cache: 是否启用查询缓存
            cache_size: 缓存最大条目数
        """
        self.db_path = db_path
        self.db = Database(db_path)
        self.enable_cache = enable_cache
        self.cache = LRUCache(max_size=cache_size) if enable_cache else None

    def _cached_query(self, cache_key: str, query_func):
        """执行带缓存的查询

        Args:
            cache_key: 缓存键
            query_func: 查询函数

        Returns:
            查询结果
        """
        if not self.enable_cache:
            return query_func()

        # 尝试从缓存获取
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # 执行查询并存入缓存
        result = query_func()
        self.cache.put(cache_key, result)
        return result

    def get_symbol(self, name: str, file: Optional[str] = None,
                    kind: Optional[str] = None) -> Optional[SymbolRecord]:
        """获取指定名称的符号

        Args:
            name: 符号名称，支持通配符
            file: 可选，限定文件范围
            kind: 可选，符号类型

        Returns:
            符号记录或 None
        """
        # 使用缓存
        cache_key = self.cache._make_key('get_symbol', name, file, kind) if self.cache else None

        def _query():
            sql = """
                SELECT
                    s.id,
                    f.path AS file,
                    f.lang AS lang,
                    s.name,
                    s.kind,
                    s.signature,
                    s.docstring,
                    s.body,
                    s.line_start,
                    s.line_end,
                    s.col_start,
                    s.col_end,
                    s.parent_name,
                    s.is_exported,
                    s.complexity
                FROM symbols s
                JOIN files f ON f.id = s.file_id
                WHERE s.name = ?
            """
            params = [name]

            if file:
                sql += " AND f.path LIKE ?"
                params.append(f"%{file}%")

            if kind:
                sql += " AND s.kind = ?"
                params.append(kind)

            sql += " LIMIT 1"

            row = self.db.fetchone(sql, params)
            if row:
                return SymbolRecord(**dict(row))
            return None

        return self._cached_query(cache_key, _query) if cache_key else _query()

    def get_file_outline(self, file_path: str) -> List[SymbolRecord]:
        """获取文件内所有符号大纲（不含函数体）

        Args:
            file_path: 文件路径

        Returns:
            符号列表
        """
        # 获取文件记录
        file_record = self.db.get_file(file_path)
        if not file_record:
            return []

        # 获取符号（不含 body）
        return self.db.get_symbols_by_file(file_record.id, include_body=False)

    def get_index_status(self) -> dict:
        """获取索引状态和统计信息"""
        status = self.db.get_index_status()

        # 添加缓存统计信息
        if self.enable_cache and self.cache:
            status['cache_stats'] = self.cache.get_stats()

        return status

    def clear_cache(self):
        """清空查询缓存"""
        if self.cache:
            self.cache.clear()

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """获取缓存统计信息"""
        if self.cache:
            return self.cache.get_stats()
        return None

    def get_callers(self, symbol_name: str, depth: int = 1) -> List[dict]:
        """获取调用指定符号的上层函数

        Args:
            symbol_name: 符号名称
            depth: 查询深度

        Returns:
            调用者列表
        """
        if depth < 1:
            return []

        # 使用递归 CTE 查找多跳调用者
        sql = """
            WITH RECURSIVE callers(id, name, depth) AS (
                -- Base case: 直接调用者
                SELECT s.id, s.name, 1
                FROM call_edges e
                JOIN symbols s ON s.id = e.caller_id
                WHERE e.callee_id = (SELECT id FROM symbols WHERE name = ? LIMIT 1)

                UNION ALL

                -- Recursive case: 间接调用者
                SELECT s.id, s.name, c.depth + 1
                FROM call_edges e
                JOIN symbols s ON s.id = e.caller_id
                JOIN callers c ON c.id = e.callee_id
                WHERE c.depth < ?
            )
            SELECT DISTINCT
                s.id,
                f.path AS file,
                f.lang,
                s.name,
                s.kind,
                s.signature,
                s.docstring,
                s.body,
                s.line_start,
                s.line_end,
                s.col_start,
                s.col_end,
                s.parent_name,
                s.is_exported,
                s.complexity,
                callers.depth
            FROM callers
            JOIN symbols s ON s.id = callers.id
            JOIN files f ON f.id = s.file_id
            ORDER BY callers.depth, s.name
        """

        rows = self.db.fetchall(sql, [symbol_name, depth])

        # 转换为符号记录并添加深度信息
        results = []
        for row in rows:
            row_dict = dict(row)
            caller_depth = row_dict.pop('depth')
            symbol_rec = SymbolRecord(**row_dict)
            results.append({
                "depth": caller_depth,
                "symbol": symbol_rec.to_dict()
            })

        return results

    def get_callees(self, symbol_name: str, depth: int = 1) -> List[dict]:
        """获取指定符号调用的下层函数

        Args:
            symbol_name: 符号名称
            depth: 查询深度

        Returns:
            被调用函数列表
        """
        if depth < 1:
            return []

        # 使用递归 CTE 查找多跳被调用函数
        sql = """
            WITH RECURSIVE callees(id, name, depth) AS (
                -- Base case: 直接调用的函数
                SELECT e.callee_id, e.callee_name, 1
                FROM call_edges e
                WHERE e.caller_id = (SELECT id FROM symbols WHERE name = ? LIMIT 1)
                  AND e.callee_id IS NOT NULL

                UNION ALL

                -- Recursive case: 间接调用的函数
                SELECT e.callee_id, e.callee_name, c.depth + 1
                FROM call_edges e
                JOIN callees c ON c.id = e.caller_id
                WHERE e.callee_id IS NOT NULL
                  AND c.depth < ?
            )
            SELECT DISTINCT
                s.id,
                f.path AS file,
                f.lang,
                s.name,
                s.kind,
                s.signature,
                s.docstring,
                s.body,
                s.line_start,
                s.line_end,
                s.col_start,
                s.col_end,
                s.parent_name,
                s.is_exported,
                s.complexity,
                callees.depth
            FROM callees
            JOIN symbols s ON s.id = callees.id
            JOIN files f ON f.id = s.file_id
            ORDER BY callees.depth, s.name
        """

        rows = self.db.fetchall(sql, [symbol_name, depth])

        # 转换为符号记录并添加深度信息
        results = []
        for row in rows:
            row_dict = dict(row)
            callee_depth = row_dict.pop('depth')
            symbol_rec = SymbolRecord(**row_dict)
            results.append({
                "depth": callee_depth,
                "symbol": symbol_rec.to_dict()
            })

        return results

    def get_context_window(self, symbol_name: str, depth: int = 1) -> dict:
        """获取符号的调用上下文窗口

        Args:
            symbol_name: 符号名称
            depth: 查询深度

        Returns:
            包含中心符号、调用者和被调用者的字典
        """
        symbol = self.get_symbol(symbol_name)
        if not symbol:
            return {
                "found": False,
                "message": f"Symbol '{symbol_name}' not found"
            }

        # 获取调用者和被调用者
        callers = self.get_callers(symbol_name, depth)
        callees = self.get_callees(symbol_name, depth)

        # 计算总行数
        total_lines = symbol.line_end - symbol.line_start + 1
        for caller in callers:
            caller_sym = caller["symbol"]
            total_lines += caller_sym["line_end"] - caller_sym["line_start"] + 1
        for callee in callees:
            callee_sym = callee["symbol"]
            total_lines += callee_sym["line_end"] - callee_sym["line_start"] + 1

        # 估算 token 数量（按 4 字符/token）
        total_chars = len(symbol.body)
        for caller in callers:
            total_chars += len(caller["symbol"].get("body", ""))
        for callee in callees:
            total_chars += len(callee["symbol"].get("body", ""))
        token_estimate = total_chars // 4

        return {
            "found": True,
            "center": symbol.to_dict(),
            "callers": callers,
            "callees": callees,
            "total_lines": total_lines,
            "token_estimate": token_estimate
        }

    def search(self, query: str, limit: int = 10,
                lang: Optional[str] = None) -> List[SymbolRecord]:
        """全文搜索符号（使用 FTS5）

        Args:
            query: 搜索查询（支持 FTS5 MATCH 语法）
            limit: 返回结果数量
            lang: 可选，限定语言

        Returns:
            符号列表，按相关性排序
        """
        sql = """
            SELECT
                s.id,
                f.path AS file,
                f.lang AS lang,
                s.name,
                s.kind,
                s.signature,
                s.docstring,
                s.body,
                s.line_start,
                s.line_end,
                s.col_start,
                s.col_end,
                s.parent_name,
                s.is_exported,
                s.complexity,
                fts.rank AS score
            FROM symbols_fts fts
            JOIN symbols s ON s.id = fts.rowid
            JOIN files f ON f.id = s.file_id
            WHERE symbols_fts MATCH ?
        """
        params = [query]

        if lang:
            sql += " AND f.lang = ?"
            params.append(lang)

        sql += " ORDER BY score LIMIT ?"
        params.append(limit)

        rows = self.db.fetchall(sql, params)
        # 移除 score 字段后创建 SymbolRecord
        return [SymbolRecord(**{k: v for k, v in dict(r).items() if k != 'score'}) for r in rows]

    def list_symbols(self, kind: Optional[str] = None,
                      lang: Optional[str] = None,
                      file: Optional[str] = None) -> List[SymbolRecord]:
        """按条件筛选符号列表

        Args:
            kind: 可选，符号类型
            lang: 可选，语言类型
            file: 可选，文件路径

        Returns:
            符号列表
        """
        sql = """
            SELECT
                s.id,
                f.path AS file,
                f.lang AS lang,
                s.name,
                s.kind,
                s.signature,
                s.docstring,
                s.body,
                s.line_start,
                s.line_end,
                s.col_start,
                s.col_end,
                s.parent_name,
                s.is_exported,
                s.complexity
            FROM symbols s
            JOIN files f ON f.id = s.file_id
            WHERE 1=1
        """
        params = []

        if kind:
            sql += " AND s.kind = ?"
            params.append(kind)

        if lang:
            sql += " AND f.lang = ?"
            params.append(lang)

        if file:
            sql += " AND f.path LIKE ?"
            params.append(f"%{file}%{file}%")

        rows = self.db.fetchall(sql, params)
        return [SymbolRecord(**dict(r)) for r in rows]

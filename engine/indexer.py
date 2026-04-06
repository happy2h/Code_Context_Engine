"""
Context Engine 索引构建器

负责全量和增量索引构建。
"""

import os
import time
import hashlib
from pathlib import Path
from typing import List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import pathspec
from engine.logger import Logger, log_performance, log_errors


@dataclass
class IndexResult:
    """索引结果"""
    files_processed: int
    symbols_count: int
    call_edges_count: int
    errors: int
    duration: float


class Indexer:
    """索引构建器"""

    def __init__(self, repo_root: str, db_path: str):
        self.repo_root = os.path.abspath(repo_root)
        self.db_path = db_path

        from engine.db import Database
        from engine.parser import SymbolExtractor
        from config import Config

        self.db = Database(db_path)
        self.parser = SymbolExtractor()
        self.config = Config
        self.logger = Logger()

        # 初始化排除规则
        self._init_excludes()

    def _init_excludes(self):
        """初始化文件排除规则"""
        exclude_patterns = self.config.get_exclude_patterns()
        self.excludes = pathspec.PathSpec.from_lines(
            'gitwildmatch',
            exclude_patterns.split(',')
        )

        # 加载 .gitignore
        gitignore_path = os.path.join(self.repo_root, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                gitignore_patterns = f.read().splitlines()
            if gitignore_patterns:
                gitignore_spec = pathspec.PathSpec.from_lines(
                    'gitwildmatch',
                    gitignore_patterns
                )
                self.excludes = pathspec.PathSpec(
                    [self.excludes, gitignore_spec]
                )

    def _is_excluded(self, rel_path: str) -> bool:
        """检查文件是否被排除"""
        return self.excludes.match_file(rel_path)

    def _discover_files(self) -> List[str]:
        """发现仓库中的所有代码文件"""
        files = []
        max_size = self.config.get_max_file_size()

        for root, dirs, filenames in os.walk(self.repo_root):
            # 过滤排除的目录
            dirs[:] = [d for d in dirs if not self._is_excluded(
                os.path.relpath(os.path.join(root, d), self.repo_root)
            )]

            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, self.repo_root)

                # 跳过排除的文件
                if self._is_excluded(rel_path):
                    continue

                # 检查是否为代码文件
                lang = self.parser.detect_language(file_path)
                if not lang:
                    continue

                # 检查文件大小
                file_size = os.path.getsize(file_path)
                if file_size > max_size:
                    continue

                files.append(file_path)

        return files

    @log_performance(operation="full_index")
    def full_index(self) -> IndexResult:
        """执行全量索引构建"""
        start_time = time.time()

        # 更新元数据
        self.db.set_meta('repo_root', self.repo_root)
        self.db.set_meta('created_at', time.strftime('%Y-%m-%dT%H:%M:%S'))

        # 发现文件
        files = self._discover_files()
        self.logger.info(f"Discovered {len(files)} files")

        # 并行解析
        workers = self.config.get_parallel_workers()
        self.logger.debug(f"Using {workers} parallel workers")
        all_symbols = []
        all_call_edges = []
        errors = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._parse_file, file_path): file_path
                for file_path in files
            }

            for future in as_completed(futures):
                file_path = futures[future]
                try:
                    result = future.result()
                    if result:
                        symbols, call_edges, file_id = result
                        all_symbols.extend([(s, file_id) for s in symbols])
                        all_call_edges.extend([(e, file_id) for e in call_edges])
                        self.logger.debug(f"Parsed: {os.path.relpath(file_path, self.repo_root)}")
                except Exception as e:
                    errors += 1
                    self.logger.error(f"Error parsing {file_path}", exc_info=e)

        # 写入数据库
        self._write_to_db(all_symbols, all_call_edges)

        # 解析跨文件调用关系
        self._resolve_cross_file_calls()

        # 更新索引完成时间
        self.db.set_meta('last_full_index', time.strftime('%Y-%m-%dT%H:%M:%S'))

        duration = time.time() - start_time

        result = IndexResult(
            files_processed=len(files),
            symbols_count=len(all_symbols),
            call_edges_count=len(all_call_edges),
            errors=errors,
            duration=duration
        )

        self.logger.info(
            f"Full index completed",
            files_processed=len(files),
            symbols_count=len(all_symbols),
            call_edges_count=len(all_call_edges),
            errors=errors,
            duration_seconds=round(duration, 2)
        )

        return result

    @log_errors()
    def _parse_file(self, file_path: str) -> tuple | None:
        """解析单个文件"""
        rel_path = os.path.relpath(file_path, self.repo_root)
        lang = self.parser.detect_language(file_path)
        if not lang:
            return None

        # 计算哈希
        content_hash = self.parser.calculate_hash(file_path)

        # 检查是否已存在且未变更
        existing = self.db.get_file(rel_path)
        if existing and existing.content_hash == content_hash:
            return None  # 跳过未变更文件

        # 提取符号
        symbols, call_edges = self.parser.extract(file_path, lang)

        # 删除旧记录
        if existing:
            self.db.delete_file(rel_path)

        # 插入文件记录
        line_count = self._count_lines(file_path)
        file_size = os.path.getsize(file_path)
        file_id = self.db.insert_file(
            path=rel_path,
            abs_path=file_path,
            lang=lang,
            content_hash=content_hash,
            size_bytes=file_size,
            line_count=line_count
        )

        return symbols, call_edges, file_id

    def _write_to_db(self, all_symbols: List[tuple], all_call_edges: List[tuple]):
        """批量写入数据库"""
        # 按文件 ID 分组符号
        symbols_by_file = {}
        for sym, file_id in all_symbols:
            if file_id not in symbols_by_file:
                symbols_by_file[file_id] = []
            symbols_by_file[file_id].append(sym)

        # 批量插入符号
        for file_id, symbols in symbols_by_file.items():
            self.db.bulk_insert_symbols(file_id, symbols)

        # 批量插入调用边（需要先建立 symbol_id 映射）
        self._insert_call_edges(all_call_edges)

    def _insert_call_edges(self, all_call_edges: List[tuple]):
        """批量插入调用边"""
        # 建立符号名称到 ID 的映射
        symbol_map = {}
        rows = self.db.fetchall("""
            SELECT s.id, s.name, f.path
            FROM symbols s
            JOIN files f ON f.id = s.file_id
        """)
        for row in rows:
            key = (row['name'], row['path'])
            symbol_map[key] = row['id']

        # 也有同名符号的情况，按文件分组
        file_symbols = {}
        for row in rows:
            file_path = row['path']
            if file_path not in file_symbols:
                file_symbols[file_path] = {}
            file_symbols[file_path][row['name']] = row['id']

        # 插入调用边
        for edge, file_id in all_call_edges:
            caller_name = edge['caller_name']
            callee_name = edge['callee_name']

            # 查找 caller_id
            caller_id = None
            for file_path, symbols in file_symbols.items():
                if caller_name in symbols:
                    caller_id = symbols[caller_name]
                    break

            if caller_id:
                self.db.bulk_insert_call_edges([{
                    'caller_id': caller_id,
                    'callee_name': callee_name,
                    'callee_id': None,  # 稍后解析
                    'call_line': edge.get('call_line'),
                    'call_type': edge.get('call_type', 'direct')
                }])

    def _resolve_cross_file_calls(self, affected_files: List[str] = None):
        """解析跨文件调用关系，填充 callee_id

        Args:
            affected_files: 可选，仅处理指定文件的调用边（用于增量更新）
        """
        # 查询需要处理的调用边
        sql = """
            SELECT id, caller_id, callee_name, callee_id
            FROM call_edges
            WHERE callee_id IS NULL
        """
        params = []

        if affected_files:
            # 仅处理指定文件相关的调用边
            placeholders = ','.join('?' * len(affected_files))
            sql = f"""
                SELECT ce.id, ce.caller_id, ce.callee_name, ce.callee_id
                FROM call_edges ce
                JOIN symbols s ON s.id = ce.caller_id
                JOIN files f ON f.id = s.file_id
                WHERE ce.callee_id IS NULL AND f.path IN ({placeholders})
            """
            params = affected_files

        edges = self.db.fetchall(sql, params)

        if not edges:
            return

        # 建立符号名称到 ID 的全局映射（用于快速查找）
        # 使用列表存储所有同名符号，返回第一个匹配的
        symbol_name_map = {}

        # 建立符号名称到 ID 的映射（按文件分组）
        # key: (file_path, symbol_name) -> value: symbol_id
        file_symbol_map = {}

        rows = self.db.fetchall("""
            SELECT s.id, s.name, f.path, f.id AS file_id, s.kind
            FROM symbols s
            JOIN files f ON f.id = s.file_id
        """)
        for row in rows:
            file_path = row['path']
            symbol_name = row['name']
            symbol_id = row['id']

            # 添加到全局名称映射
            if symbol_name not in symbol_name_map:
                symbol_name_map[symbol_name] = []
            symbol_name_map[symbol_name].append(symbol_id)

            # 添加到文件特定映射
            file_symbol_map[(file_path, symbol_name)] = symbol_id

        # 批量更新调用边
        updates = []
        for edge in edges:
            callee_name = edge['callee_name']
            edge_id = edge['id']

            # 首先尝试精确匹配
            # 1. 查找调用者所在文件中是否有同名符号
            caller_id = edge['caller_id']
            caller_file = None

            # 获取调用者所在的文件路径
            caller_rows = self.db.fetchall("""
                SELECT f.path
                FROM symbols s
                JOIN files f ON f.id = s.file_id
                WHERE s.id = ?
            """, [caller_id])
            if caller_rows:
                caller_file = caller_rows[0]['path']

            # 2. 优先查找同一文件中的符号
            callee_id = None
            if caller_file:
                key = (caller_file, callee_name)
                if key in file_symbol_map:
                    callee_id = file_symbol_map[key]

            # 3. 如果同一文件中没有，查找所有文件中同名符号
            if not callee_id and callee_name in symbol_name_map:
                # 返回第一个匹配的符号
                callee_id = symbol_name_map[callee_name][0]

            if callee_id:
                updates.append((callee_id, edge_id))

        # 批量执行更新
        if updates:
            with self.db.transaction() as cursor:
                for callee_id, edge_id in updates:
                    cursor.execute("""
                        UPDATE call_edges
                        SET callee_id = ?
                        WHERE id = ?
                    """, [callee_id, edge_id])

            print(f"Resolved {len(updates)} cross-file call edges")

    def _count_lines(self, file_path: str) -> int:
        """统计文件行数"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)

    def incremental_update(self, changed_files: List[str]) -> IndexResult:
        """对变更文件执行增量重索引

        Args:
            changed_files: 变更的文件列表（绝对路径）
        """
        start_time = time.time()

        all_symbols = []
        all_call_edges = []
        errors = 0

        for file_path in changed_files:
            try:
                # 检查文件是否存在
                if not os.path.exists(file_path):
                    # 文件删除：级联删除
                    rel_path = os.path.relpath(file_path, self.repo_root)
                    self.db.delete_file(rel_path)
                    continue

                # 检查是否为代码文件
                lang = self.parser.detect_language(file_path)
                if not lang:
                    continue

                # 计算新哈希
                new_hash = self.parser.calculate_hash(file_path)

                # 获取旧记录
                rel_path = os.path.relpath(file_path, self.repo_root)
                old_record = self.db.get_file(rel_path)

                # 如果旧记录存在且哈希相同，跳过
                if old_record and old_record.content_hash == new_hash:
                    continue

                # 删除旧记录
                if old_record:
                    self.db.delete_file(rel_path)

                # 重新解析
                symbols, call_edges = self.parser.extract(file_path, lang)

                # 插入新记录
                line_count = self._count_lines(file_path)
                file_size = os.path.getsize(file_path)
                file_id = self.db.insert_file(
                    path=rel_path,
                    abs_path=file_path,
                    lang=lang,
                    content_hash=new_hash,
                    size_bytes=file_size,
                    line_count=line_count
                )

                all_symbols.extend([(s, file_id) for s in symbols])
                all_call_edges.extend([(e, file_id) for e in call_edges])

            except Exception as e:
                errors += 1
                print(f"Error updating {file_path}: {e}")

        # 写入数据库
        if all_symbols or all_call_edges:
            self._write_to_db(all_symbols, all_call_edges)
            # 重新解析跨文件调用关系（仅处理变更文件相关）
            affected_rel_paths = [os.path.relpath(f, self.repo_root) for f in changed_files]
            self._resolve_cross_file_calls(affected_rel_paths)

        duration = time.time() - start_time

        return IndexResult(
            files_processed=len(changed_files),
            symbols_count=len(all_symbols),
            call_edges_count=len(all_call_edges),
            errors=errors,
            duration=duration
        )

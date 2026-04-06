"""
Context Engine 文件系统监听器

监听文件变化，触发增量索引更新。
"""

import os
import threading
import time
from typing import Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class RepoWatcher(FileSystemEventHandler):
    """仓库文件监听器"""

    DEBOUNCE_SECONDS = 0.5  # 防抖：500ms 内多次变更合并处理

    def __init__(self, indexer, repo_root: str):
        super().__init__()
        self._indexer = indexer
        self._repo_root = repo_root
        self._pending: Set[str] = set()  # 待处理的变更文件
        self._timer = None
        self._lock = threading.Lock()
        self._observer = None

    def on_modified(self, event):
        """文件修改事件"""
        if not event.is_directory and self._is_code_file(event.src_path):
            self._schedule(event.src_path)

    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory and self._is_code_file(event.src_path):
            self._schedule(event.src_path)

    def on_deleted(self, event):
        """文件删除事件"""
        if not event.is_directory and self._is_code_file(event.src_path):
            self._schedule(event.src_path)

    def _is_code_file(self, file_path: str) -> bool:
        """检查是否为代码文件"""
        from engine.parser import SymbolExtractor
        parser = SymbolExtractor()
        lang = parser.detect_language(file_path)
        return lang is not None

    def _schedule(self, path: str):
        """安排文件更新任务（带防抖）"""
        with self._lock:
            self._pending.add(path)

            if self._timer:
                self._timer.cancel()

            self._timer = threading.Timer(
                self.DEBOUNCE_SECONDS,
                self._flush
            )
            self._timer.start()

    def _flush(self):
        """执行待处理的文件更新"""
        with self._lock:
            files = list(self._pending)
            self._pending.clear()

        if not files:
            return

        print(f"Processing {len(files)} changed files...")
        result = self._indexer.incremental_update(files)
        print(f"Update completed: {result.files_processed} files, "
              f"{result.symbols_count} symbols, {result.duration:.2f}s")

    def start(self):
        """启动监听"""
        self._observer = Observer()
        self._observer.schedule(self, self._repo_root, recursive=True)
        self._observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止监听"""
        if self._observer:
            self._observer.stop()
            self._observer.join()

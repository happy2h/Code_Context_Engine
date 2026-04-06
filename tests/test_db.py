"""
数据库层测试
"""

import pytest
import os
import tempfile
from engine.db import Database


class TestDatabase:
    """数据库测试"""

    def setup_method(self):
        """设置测试环境"""
        # 创建临时数据库文件
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = Database(self.db_path)

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_database_creation(self):
        """测试数据库创建"""
        assert os.path.exists(self.db_path)

    def test_insert_file(self):
        """测试文件插入"""

        file_id = self.db.insert_file(
            path="test.py",
            abs_path="/abs/path/test.py",
            lang="python",
            content_hash="abc123",
            size_bytes=100,
            line_count=10
        )

        assert file_id > 0

        # 检查是否插入成功
        file_record = self.db.get_file("test.py")
        assert file_record is not None
        assert file_record.path == "test.py"
        assert file_record.lang == "python"
        assert file_record.content_hash == "abc123"

    def test_get_file(self):
        """测试文件查询"""
        file_id = self.db.insert_file(
            path="module.py",
            abs_path="/abs/path/module.py",
            lang="python",
            content_hash="hash456",
            size_bytes=200,
            line_count=20
        )

        file_record = self.db.get_file("module.py")
        assert file_record is not None
        assert file_record.id == file_id

    def test_bulk_insert_symbols(self):
        """测试批量插入符号"""
        # 先插入文件
        file_id = self.db.insert_file(
            path="test.py",
            abs_path="/abs/path/test.py",
            lang="python",
            content_hash="hash1",
            size_bytes=100,
            line_count=10
        )

        # 批量插入符号
        symbols = [
            {
                "name": "function1",
                "kind": "function",
                "signature": "def function1():",
                "docstring": "Docstring for function1",
                "body": "def function1():\n    pass",
                "line_start": 1,
                "line_end": 2,
                "col_start": 1,
                "col_end": 8,
                "parent_name": None,
                "is_exported": 0,
                "complexity": 1
            },
            {
                "name": "function2",
                "kind": "function",
                "signature": "def function2():",
                "docstring": None,
                "body": "def function2():\n    return 1",
                "line_start": 4,
                "line_end": 5,
                "col_start": 1,
                "col_end": 8,
                "parent_name": None,
                "is_exported": 0,
                "complexity": 1
            }
        ]

        self.db.bulk_insert_symbols(file_id, symbols)

        # 检查是否插入成功
        file_symbols = self.db.get_symbols_by_file(file_id)
        assert len(file_symbols) == 2
        assert file_symbols[0].name == "function1"
        assert file_symbols[1].name == "function2"

    def test_delete_file(self):
        """测试文件删除"""
        file_id = self.db.insert_file(
            path="to_delete.py",
            abs_path="/abs/path/to_delete.py",
            lang="python",
            content_hash="hash1",
            size_bytes=100,
            line_count=10
        )

        # 插入符号
        symbols = [{
            "name": "func",
            "kind": "function",
            "signature": "def func():",
            "docstring": None,
            "body": "def func():\n    pass",
            "line_start": 1,
            "line_end": 2,
            "col_start": 1,
            "col_end": 4,
            "parent_name": None,
            "is_exported": 0,
            "complexity": 1
        }]
        self.db.bulk_insert_symbols(file_id, symbols)

        # 删除文件
        self.db.delete_file("to_delete.py")

        # 检查文件是否被删除
        file_record = self.db.get_file("to_delete.py")
        assert file_record is None

        # 检查符号是否被级联删除
        file_symbols = self.db.get_symbols_by_file(file_id)
        assert len(file_symbols) == 0

    def test_meta_operations(self):
        """测试元数据操作"""
        self.db.set_meta("test_key", "test_value")

        value = self.db.get_meta("test_key")
        assert value == "test_value"

        default_value = self.db.get_meta("non_existent", "default")
        assert default_value == "default"

    def test_get_index_status(self):
        """测试获取索引状态"""
        status = self.db.get_index_status()

        assert "schema_version" in status
        assert "engine_version" in status
        assert "total_files" in status
        assert "total_symbols" in status
        assert "total_call_edges" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

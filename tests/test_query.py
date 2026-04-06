"""
查询引擎测试
"""

import pytest
import os
import tempfile
from engine.query import QueryEngine


class TestQueryEngine:
    """查询引擎测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.engine = QueryEngine(self.db_path)

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_get_symbol_not_found(self):
        """测试查询不存在的符号"""
        result = self.engine.get_symbol("non_existent_function")
        assert result is None

    def test_get_file_outline_empty(self):
        """测试获取空文件大纲"""
        outline = self.engine.get_file_outline("non_existent.py")
        assert outline == []

    def test_get_index_status(self):
        """测试获取索引状态"""
        status = self.engine.get_index_status()
        assert "schema_version" in status
        assert "engine_version" in status
        assert "total_files" in status

    def test_search_empty(self):
        """测试搜索空数据库"""
        results = self.engine.search("test")
        assert results == []

    def test_list_symbols_empty(self):
        """测试列出空数据库的符号"""
        results = self.engine.list_symbols()
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

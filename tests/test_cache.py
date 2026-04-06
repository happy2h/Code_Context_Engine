"""
测试查询引擎的缓存功能
"""

import pytest
import tempfile
import os
from engine.query import QueryEngine, LRUCache


class TestLRUCache:
    """测试 LRU 缓存"""

    def test_cache_put_and_get(self):
        """测试基本的 put 和 get 操作"""
        cache = LRUCache(max_size=3)

        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        cache.put('key3', 'value3')

        assert cache.get('key1') == 'value1'
        assert cache.get('key2') == 'value2'
        assert cache.get('key3') == 'value3'

    def test_cache_lru_eviction(self):
        """测试 LRU 淘汰策略"""
        cache = LRUCache(max_size=3)

        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        cache.put('key3', 'value3')

        # 访问 key1 使其成为最近使用
        cache.get('key1')

        # 添加 key4，应该淘汰 key2
        cache.put('key4', 'value4')

        assert cache.get('key1') == 'value1'  # 最近使用，保留
        assert cache.get('key2') is None      # 最久未使用，淘汰
        assert cache.get('key3') == 'value3'
        assert cache.get('key4') == 'value4'

    def test_cache_update(self):
        """测试更新已存在的键"""
        cache = LRUCache(max_size=3)

        cache.put('key1', 'value1')
        cache.put('key1', 'value2')

        assert cache.get('key1') == 'value2'

    def test_cache_clear(self):
        """测试清空缓存"""
        cache = LRUCache(max_size=3)

        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        cache.clear()

        assert cache.get('key1') is None
        assert cache.get('key2') is None
        assert cache.get_stats()['size'] == 0

    def test_cache_stats(self):
        """测试缓存统计"""
        cache = LRUCache(max_size=3)

        cache.put('key1', 'value1')
        cache.get('key1')  # 命中
        cache.get('key2')  # 未命中

        stats = cache.get_stats()
        assert stats['size'] == 1
        assert stats['max_size'] == 3
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 50.0

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        cache = LRUCache(max_size=3)

        # 不同参数类型
        key1 = cache._make_key('test', 123, True)
        key2 = cache._make_key('test', 123, True)
        key3 = cache._make_key('test', 456, True)

        assert key1 == key2
        assert key1 != key3


class TestQueryEngineCache:
    """测试查询引擎的缓存集成"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            yield db_path

    def test_cache_enabled_by_default(self, temp_db):
        """测试缓存默认启用"""
        engine = QueryEngine(db_path=temp_db)
        assert engine.enable_cache is True
        assert engine.cache is not None

    def test_cache_disabled(self, temp_db):
        """测试禁用缓存"""
        engine = QueryEngine(db_path=temp_db, enable_cache=False)
        assert engine.enable_cache is False
        assert engine.cache is None

    def test_cache_clear(self, temp_db):
        """测试清空查询缓存"""
        engine = QueryEngine(db_path=temp_db)
        engine.clear_cache()

        if engine.cache:
            assert engine.cache.get_stats()['size'] == 0

    def test_get_cache_stats(self, temp_db):
        """测试获取缓存统计"""
        engine = QueryEngine(db_path=temp_db)

        stats = engine.get_cache_stats()
        if stats:
            assert 'size' in stats
            assert 'hits' in stats
            assert 'misses' in stats
            assert 'hit_rate' in stats

    def test_cached_query_execution(self, temp_db):
        """测试缓存查询的执行"""
        engine = QueryEngine(db_path=temp_db, enable_cache=True)

        # 初始化一些测试数据
        from engine.db import Database
        db = Database(temp_db)

        # 插入测试文件和符号
        file_id = db.insert_file(
            path='test.py',
            abs_path='/tmp/test.py',
            lang='python',
            content_hash='abc123',
            size_bytes=100,
            line_count=10
        )

        db.bulk_insert_symbols(file_id, [{
            'name': 'test_func',
            'kind': 'function',
            'signature': 'def test_func():',
            'docstring': 'Test function',
            'body': 'def test_func():\n    pass',
            'line_start': 1,
            'line_end': 3,
            'col_start': 0,
            'col_end': 20,
            'is_exported': 1
        }])

        # 第一次查询
        result1 = engine.get_symbol('test_func')
        assert result1 is not None

        # 第二次查询（应命中缓存）
        result2 = engine.get_symbol('test_func')
        assert result2 is not None

        # 检查缓存统计
        stats = engine.get_cache_stats()
        if stats:
            # 应该有至少一次命中（第二次查询）
            assert stats['hits'] >= 1

    def test_cache_with_disabled_engine(self, temp_db):
        """测试禁用缓存的引擎仍然工作"""
        engine = QueryEngine(db_path=temp_db, enable_cache=False)

        # 初始化一些测试数据
        from engine.db import Database
        db = Database(temp_db)

        file_id = db.insert_file(
            path='test.py',
            abs_path='/tmp/test.py',
            lang='python',
            content_hash='abc123',
            size_bytes=100,
            line_count=10
        )

        db.bulk_insert_symbols(file_id, [{
            'name': 'test_func',
            'kind': 'function',
            'signature': 'def test_func():',
            'docstring': 'Test function',
            'body': 'def test_func():\n    pass',
            'line_start': 1,
            'line_end': 3,
            'col_start': 0,
            'col_end': 20,
            'is_exported': 1
        }])

        # 即使缓存禁用，查询仍应工作
        result = engine.get_symbol('test_func')
        assert result is not None

"""
性能基准测试

用于建立性能基线并检测性能回归。
运行方法: pytest tests/test_benchmark.py --benchmark-only
"""

import pytest
import tempfile
import os
import time
from pathlib import Path

# 创建临时目录 fixture
@pytest.fixture
def tmpdir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

# 尝试导入 pytest-benchmark，如果不可用则跳过
try:
    import pytest_benchmark
    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False

requires_benchmark = pytest.mark.skipif(
    not HAS_BENCHMARK,
    reason="pytest-benchmark not installed"
)


class TestDatabaseBenchmark:
    """数据库操作性能基准"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            yield db_path

    @requires_benchmark
    def test_insert_file_performance(self, temp_db, benchmark):
        """测试文件插入性能"""
        from engine.db import Database
        import hashlib

        def insert_files():
            db = Database(temp_db)
            for i in range(100):
                db.insert_file(
                    path=f'file_{i}.py',
                    abs_path=f'/tmp/file_{i}.py',
                    lang='python',
                    content_hash=hashlib.sha256(f'content_{i}'.encode()).hexdigest(),
                    size_bytes=100,
                    line_count=10
                )

        benchmark(insert_files)

    @requires_benchmark
    def test_bulk_insert_symbols_performance(self, temp_db, benchmark):
        """测试批量符号插入性能"""
        from engine.db import Database

        db = Database(temp_db)
        file_id = db.insert_file(
            path='test.py',
            abs_path='/tmp/test.py',
            lang='python',
            content_hash='abc123',
            size_bytes=100,
            line_count=100
        )

        symbols = [{
            'name': f'func_{i}',
            'kind': 'function',
            'signature': f'def func_{i}():',
            'docstring': f'Function {i}',
            'body': f'def func_{i}():\n    pass',
            'line_start': i * 10 + 1,
            'line_end': i * 10 + 5,
            'col_start': 0,
            'col_end': 20,
            'is_exported': 1
        } for i in range(1000)]

        def bulk_insert():
            db.bulk_insert_symbols(file_id, symbols)

        benchmark(bulk_insert)

    @requires_benchmark
    def test_query_symbol_performance(self, temp_db, benchmark):
        """测试符号查询性能"""
        from engine.db import Database
        import hashlib

        db = Database(temp_db)

        # 插入测试数据
        file_id = db.insert_file(
            path='test.py',
            abs_path='/tmp/test.py',
            lang='python',
            content_hash=hashlib.sha256(b'test').hexdigest(),
            size_bytes=10000,
            line_count=1000
        )

        symbols = [{
            'name': f'func_{i}',
            'kind': 'function',
            'signature': f'def func_{i}():',
            'docstring': f'Function {i}',
            'body': f'def func_{i}():\n    pass',
            'line_start': i * 10 + 1,
            'line_end': i * 10 + 5,
            'col_start': 0,
            'col_end': 20,
            'is_exported': 1
        } for i in range(100)]

        db.bulk_insert_symbols(file_id, symbols)

        def query_symbol():
            db.fetchone(
                "SELECT * FROM symbols WHERE name = ?",
                ['func_50']
            )

        benchmark(query_symbol)


class TestQueryEngineBenchmark:
    """查询引擎性能基准"""

    @pytest.fixture
    def setup_engine(self, tmpdir):
        """设置测试引擎"""
        from engine.query import QueryEngine
        from engine.db import Database
        import hashlib
        db_path = os.path.join(tmpdir, 'test.db')

        db = Database(db_path)

        # 插入测试数据
        for file_num in range(10):
            file_id = db.insert_file(
                path=f'test_{file_num}.py',
                abs_path=f'/tmp/test_{file_num}.py',
                lang='python',
                content_hash=hashlib.sha256(f'content_{file_num}'.encode()).hexdigest(),
                size_bytes=1000,
                line_count=100
            )

            symbols = [{
                'name': f'func_{file_num}_{i}',
                'kind': 'function',
                'signature': f'def func_{file_num}_{i}():',
                'docstring': f'Function {i} in file {file_num}',
                'body': f'def func_{file_num}_{i}():\n    pass',
                'line_start': i * 10 + 1,
                'line_end': i * 10 + 5,
                'col_start': 0,
                'col_end': 25,
                'is_exported': 1
            } for i in range(100)]

            db.bulk_insert_symbols(file_id, symbols)

        engine = QueryEngine(db_path=db_path, enable_cache=False)
        return engine

    @requires_benchmark
    def test_get_symbol_performance(self, setup_engine, benchmark):
        """测试获取符号性能"""
        def get_symbol():
            setup_engine.get_symbol('func_5_50')

        benchmark(get_symbol)

    @requires_benchmark
    def test_search_performance(self, setup_engine, benchmark):
        """测试搜索性能"""
        def search():
            setup_engine.search('func_5', limit=10)

        benchmark(search)

    @requires_benchmark
    def test_list_symbols_performance(self, setup_engine, benchmark):
        """测试列出符号性能"""
        def list_symbols():
            setup_engine.list_symbols(kind='function')

        benchmark(list_symbols)


class TestCacheBenchmark:
    """缓存性能基准"""

    @requires_benchmark
    def test_cache_put_performance(self, benchmark):
        """测试缓存写入性能"""
        from engine.query import LRUCache

        cache = LRUCache(max_size=10000)

        def put_to_cache():
            for i in range(100):
                cache.put(f'key_{i}', f'value_{i}')

        benchmark(put_to_cache)

    @requires_benchmark
    def test_cache_get_performance(self, benchmark):
        """测试缓存读取性能"""
        from engine.query import LRUCache

        cache = LRUCache(max_size=1000)

        # 预填充缓存
        for i in rangearing(1000):
            cache.put(f'key_{i}', f'value_{i}')

        def get_from_cache():
            cache.get('key_500')

        benchmark(get_from_cache)

    @requires_benchmark
    def test_cache_hit_rate(self):
        """测试缓存命中率"""
        from engine.query import LRUCache

        cache = LRUCache(max_size=100)

        # 填充缓存
        for i in range(100):
            cache.put(f'key_{i}', f'value_{i}')

        # 访问前 50 个键（应该命中）
        for i in range(50):
            cache.get(f'key_{i}')

        # 访问不存在的键（应该未命中）
        for i in range(50):
            cache.get(f'nonexistent_{i}')

        stats = cache.get_stats()
        hit_rate = stats['hit_rate']

        # 命中率应该在 50% 左右
        assert 45 <= hit_rate <= 55
        assert stats['hits'] == 50
        assert stats['misses'] == 50


class TestParserBenchmark:
    """解析器性能基准"""

    @pytest.fixture
    def sample_python_file(self, tmpdir):
        """创建测试用的 Python 文件"""
        file_path = os.path.join(tmpdir, 'sample.py')

        # 创建包含 100 个函数的文件
        with open(file_path, 'w') as f:
            for i in range(100):
                f.write(f'''
def function_{i}(param1: str, param2: int) -> bool:
    """Documentation for function {i}

    This is a multi-line docstring.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        A boolean value
    """
    # Some code here
    result = param1 + str(param2)
    return len(result) > 0

''')

        return file_path

    @requires_benchmark
    def test_parse_file_performance(self, sample_python_file, benchmark):
        """测试文件解析性能"""
        from engine.parser import SymbolExtractor

        extractor = SymbolExtractor()

        def parse_file():
            extractor.extract(sample_python_file, 'python')

        benchmark(parse_file)

    @requires_benchmark
    def test_hash_calculation_performance(self, sample_python_file, benchmark):
        """测试哈希计算性能"""
        from engine.parser import SymbolExtractor

        extractor = SymbolExtractor()

        def calculate_hash():
            extractor.calculate_hash(sample_python_file)

        benchmark(calculate_hash)


class TestIndexerBenchmark:
    """索引器性能基准"""

    @pytest.fixture
    def sample_repo(self, tmpdir):
        """创建测试用的仓库结构"""
        tmpdir = tmpdir

        # 创建 50 个 Python 文件，每个文件包含 20 个函数
        for file_num in range(50):
            file_path = os.path.join(tmpdir, f'module_{file_num}.py')

            with open(file_path, 'w') as f:
                for i in range(20):
                    f.write(f'''
def func_{file_num}_{i}():
    """Function {i} in module {file_num}"""
    return {i}

def call_{file_num}_{i}():
    """Calls func_{file_num}_{i}"""
    return func_{file_num}_{i}()

''')

        return tmpdir

    @requires_benchmark
    def test_full_index_performance(self, sample_repo, benchmark):
        """测试全量索引性能"""
        from engine.indexer import Indexer
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')

            indexer = Indexer(repo_root=sample_repo, db_path=db_path)

            def run_index():
                indexer.full_index()

            result = benchmark(run_index)

            # 验证结果
            assert result.files_processed == 50
            assert result.symbols_count == 1000  # 50 files * 20 functions
            assert result.errors == 0


# 简单的性能测试（不需要 pytest-benchmark）
class TestSimplePerformance:
    """简单的性能测试，不需要 benchmark 插件"""

    def test_query_cache_performance(self):
        """测试查询缓存的基本性能"""
        from engine.query import LRUCache
        import time

        cache = LRUCache(max_size=1000)

        # 写入性能
        start = time.time()
        for i in range(1000):
            cache.put(f'key_{i}', f'value_{i}')
        write_time = time.time() - start

        assert write_time < 0.1  # 写入 1000 条目应 < 100ms

        # 读取性能
        start = time.time()
        for i in range(1000):
            cache.get(f'key_{i}')
        read_time = time.time() - start

        assert read_time < 0.01  # 读取 1000 条目应 < 10ms

        # 命中率
        stats = cache.get_stats()
        assert stats['hit_rate'] == 100.0

    def test_database_connection_overhead(self):
        """测试数据库连接开销"""
        from engine.db import Database
        import tempfile
        time

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')

            # 测试首次连接（包含初始化）
            start = time.time()
            db1 = Database(db_path)
            first_connect_time = time.time() - start

            # 测试后续连接
            start = time.time()
            db2 = Database(db_path)
            second_connect_time = time.time() - start

            # 首次连接应较慢（初始化）
            # 后续连接应该很快
            assert second_connect_time < first_connect_time

    def test_performance_requirements(self):
        """验证性能要求"""
        # 这里放置关键性能要求的测试
        # 这些测试应该持续运行，用于 CI/CD

        # 缓存操作应该非常快
        from engine.query import LRUCache
        cache = LRUCache(max_size=100)

        start = time.time()
        cache.put('test', 'value')
        assert (time.time() - start) < 0.001  # < 1ms

        start = time.time()
        cache.get('test')
        assert (time.time() - start) < 0.001  # < 1ms

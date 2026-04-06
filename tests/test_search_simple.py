"""
全文搜索功能测试 - 简化版
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.db import Database
from engine.query import QueryEngine
from engine.parser import SymbolExtractor


def test_fts_schema():
    """测试 FTS5 表和触发器创建"""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)

        # 检查 FTS5 表是否存在
        result = db.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='symbols_fts'
        """)
        assert len(result) == 1, "FTS5 表未创建"

        # 检查触发器是否存在
        triggers = db.execute("""
            SELECT name FROM sqlite_master
            WHERE type='trigger' AND name LIKE 'symbols_%'
        """)
        trigger_names = [t['name'] for t in triggers]
        assert 'symbols_ai' in trigger_names, "INSERT 触发器未创建"
        assert 'symbols_ad' in trigger_names, "DELETE 触发器未创建"
        assert 'symbols_au' in trigger_names, "UPDATE 触发器未创建"

        print("✓ FTS5 表和触发器创建成功")

    finally:
        os.unlink(db_path)


def test_search_by_name():
    """测试按名称搜索"""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)
        query = QueryEngine(db_path)

        # 创建测试数据
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
            test_file = f.name
            f.write("""
def authenticate_user(username, password):
    \"\"\"User authentication function\"\"\"
    pass

def validate_session_token(token):
    \"\"\"Validate session token\"\"\"
    pass
""")

        try:
            # 解析并索引测试文件
            extractor = SymbolExtractor()
            symbols, _ = extractor.extract(test_file, 'python')

            file_id = db.insert_file(
                path='test.py',
                abs_path=test_file,
                lang='python',
                content_hash='test_hash',
                size_bytes=100,
                line_count=10
            )
            db.bulk_insert_symbols(file_id, symbols)

            # 测试搜索
            results = query.search('authenticate', limit=10)

            assert len(results) > 0, "搜索未返回结果"
            assert results[0].name == 'authenticate_user', "搜索结果不匹配"

            print(f"✓ 按名称搜索成功: 找到 {len(results)} 个结果")

        finally:
            os.unlink(test_file)

    finally:
        os.unlink(db_path)


def test_search_by_docstring():
    """测试按文档字符串搜索"""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)
        query = QueryEngine(db_path)

        # 创建测试数据
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
            test_file = f.name
            f.write("""
def payment_processor(order_id, amount):
    \"\"\"Process payment logic\"\"\"
    pass

class UserService:
    \"\"\"User service class\"\"\"
    pass
""")

        try:
            # 解析并索引测试文件
            extractor = SymbolExtractor()
            symbols, _ = extractor.extract(test_file, 'python')

            file_id = db.insert_file(
                path='test.py',
                abs_path=test_file,
                lang='python',
                content_hash='test_hash',
                size_bytes=100,
                line_count=10
            )
            db.bulk_insert_symbols(file_id, symbols)

            # 搜索包含"payment"的结果
            results = query.search('payment', limit=10)

            # 应该找到 payment_processor 函数
            payment_found = any(
                r.name == 'payment_processor' and r.kind == 'function'
                for r in results
            )
            assert payment_found, "未找到 payment_processor 函数"

            print(f"✓ 按文档字符串搜索成功: 找到 {len(results)} 个结果")

        finally:
            os.unlink(test_file)

    finally:
        os.unlink(db_path)


def test_fts_trigger_sync():
    """测试触发器自动同步到 FTS5"""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)
        query = QueryEngine(db_path)

        # 插入测试符号
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
            test_file = f.name
            f.write('''
def test_function():
    """Test docstring"""
    pass
''')

        try:
            extractor = SymbolExtractor()
            symbols, _ = extractor.extract(test_file, 'python')

            file_id = db.insert_file(
                path='test.py',
                abs_path=test_file,
                lang='python',
                content_hash='test_hash',
                size_bytes=50,
                line_count=5
            )
            db.bulk_insert_symbols(file_id, symbols)

            # 检查 FTS5 表是否自动同步
            fts_count = db.fetchone("SELECT COUNT(*) as count FROM symbols_fts")
            assert fts_count['count'] > 0, "FTS5 表未自动同步"

            # 测试搜索
            results = query.search('test', limit=10)
            assert len(results) > 0, "FTS5 搜索失败"

            print("✓ FTS5 触发器同步成功")

        finally:
            os.unlink(test_file)

    finally:
        os.unlink(db_path)


if __name__ == '__main__':
    test_fts_schema()
    test_fts_trigger_sync()
    test_search_by_name()
    test_search_by_docstring()
    print("\n✅ 全文搜索基础测试通过！")

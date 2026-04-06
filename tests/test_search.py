"""
全文搜索功能测试
"""
import os
import tempfile
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.db import Database
from engine.query import QueryEngine
from engine.parser import SymbolExtractor


def test_fts_schema():
    """测试 FTS5 表和触发器创建"""
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
    \"\"\"用户认证函数\"\"\"
    pass

def validate_session_token(token):
    \"\"\"验证会话令牌\"\"\"
    pass
""")

        try:
            # 解析并索引测试文件
            extractor = SymbolExtractor()
            symbols = extractor.extract(test_file, 'python')

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
    \"\"\"处理订单支付逻辑\"\"\"
    pass

class UserService:
    \"\"\"用户服务类\"\"\"
    pass
""")

        try:
            # 解析并索引测试文件
            extractor = SymbolExtractor()
            symbols = extractor.extract(test_file, 'python')

            file_id = db.insert_file(
                path='test.py',
                abs_path=test_file,
                lang='python',
                content_hash='test_hash',
                size_bytes=100,
                line_count=10
            )
            db.bulk_insert_symbols(file_id, symbols)

            # 搜索包含"用户"的结果
            results = query.search('用户', limit=10)

            # 应该找到 UserService 类
            user_service_found = any(
                r.name == 'UserService' and r.kind == 'class'
                for r in results
            )
            assert user_service_found, "未找到 UserService 类"

            print(f"✓ 按文档字符串搜索成功: 找到 {len(results)} 个结果")

        finally:
            os.unlink(test_file)

    finally:
        os.unlink(db_path)


def test_search_with_lang_filter():
    """测试带语言过滤的搜索"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)
        query = QueryEngine(db_path)

        # 创建 Python 测试文件
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
            py_file = f.name
            f.write("""
def authenticate(username, password):
    \"\"\"Python 认证函数\"\"\"
    pass
""")

        # 创建 TypeScript 测试文件
        with tempfile.NamedTemporaryFile(suffix='.ts', mode='w', delete=False) as f:
            ts_file = f.name
            f.write("""
function authenticate(username: string, password: string): boolean {
    return true;
}
""")

        try:
            extractor = SymbolExtractor()

            # 索引 Python 文件
            py_symbols = extractor.extract(py_file, 'python')
            py_file_id = db.insert_file(
                path='test.py',
                abs_path=py_file,
                lang='python',
                content_hash='py_hash',
                size_bytes=100,
                line_count=5
            )
            db.bulk_insert_symbols(py_file_id, py_symbols)

            # 索引 TypeScript 文件
            ts_symbols = extractor.extract(ts_file, 'typescript')
            ts_file_id = db.insert_file(path='test.ts', abs_path=ts_file,
                lang='typescript', content_hash='ts_hash',
                size_bytes=100, line_count=5)
            db.bulk_insert_symbols(ts_file_id, ts_symbols)

            # 搜索所有语言的 authenticate
            all_results = query.search('authenticate', limit=10)
            assert len(all_results) == 2, f"应找到 2 个结果，实际找到 {len(all_results)}"

            # 只搜索 Python
            py_results = query.search('authenticate', limit=10, lang='python')
            assert len(py_results) == 1, f"应找到 1 个 Python 结果，实际找到 {len(py_results)}"
            assert py_results[0].lang == 'python', "结果语言不匹配"

            print("✓ 语言过滤搜索成功")

        finally:
            os.unlink(py_file)
            os.unlink(ts_file)

    finally:
        os.unlink(db_path)


def test_search_integration():
    """集成测试：使用完整的索引流程测试搜索"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    # 创建临时测试目录
    with tempfile.TemporaryDirectory() as test_dir:
        test_repo = Path(test_dir)

        # 创建测试文件
        (test_repo / 'auth.py').write_text("""
def authenticate_user(username, password):
    \"\"\"用户认证函数\"\"\"
    pass

def validate_token(token):
    \"\"\"验证令牌有效性\"\"\"
    pass
""")

        (test_repo / 'payment.py').write_text("""
def process_payment(order_id, amount):
    \"\"\"处理支付\"\"\"
    pass
""")

    try:
        # 运行索引
        indexer = Indexer(db_path, test_repo)
        indexer.build_index()

        # 测试搜索
        query = QueryEngine(db_path)

        # 搜索"用户"
        user_results = query.search('用户', limit=5)
        assert len(user_results) > 0, "未找到包含'用户'的结果"

        # 搜索"认证"
        auth_results = query.search('认证', limit=5)
        assert len(auth_results) > 0, "未找到包含'认证'的结果"

        # 搜索"支付"
        payment_results = query.search('支付', limit=5)
        assert len(payment_results) > 0, "未找到包含'支付'的结果"

        print(f"✓ 集成测试成功:")
        print(f"  - '用户': {len(user_results)} 个结果")
        print(f"  - '认证': {len(auth_results)} 个结果")
        print(f"  - '支付': {len(payment_results)} 个结果")

    finally:
        os.unlink(db_path)


if __name__ == '__main__':
    test_fts_schema()
    test_search_by_name()
    test_search_by_docstring()
    test_search_with_lang_filter()
    test_search_integration()
    print("\n✅ 所有全文搜索测试通过！")

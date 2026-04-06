"""
文件监听器和增量更新测试
"""
import os
import sys
import time
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.db import Database
from engine.indexer import Indexer
from engine.parser import SymbolExtractor


def test_incremental_update():
    """测试增量更新功能"""
    # 创建临时测试目录
    with tempfile.TemporaryDirectory() as test_dir:
        test_repo = Path(test_dir)

        # 在测试目录内创建数据库
        db_path = str(test_repo / "test.db")

        # 创建初始文件
        (test_repo / 'auth.py').write_text('''
def authenticate(username, password):
    """Authenticate user"""
    return True
''')

        (test_repo / 'utils.py').write_text('''
def helper():
    """Helper function"""
    pass
''')

        # 运行初始全量索引
        indexer = Indexer(str(test_repo), db_path)
        result = indexer.full_index()

        assert result.files_processed == 2, f"Should process 2 files, got {result.files_processed}"
        assert result.symbols_count == 2, f"Should extract 2 symbols, got {result.symbols_count}"

        print(f"✓ Initial index: {result.files_processed} files, {result.symbols_count} symbols")

        # 修改文件
        (test_repo / 'auth.py').write_text('''
def authenticate(username, password):
    """Authenticate user - updated"""
    print("Login attempt")
    return True

def logout(token):
    """Logout user"""
    pass
''')

        # 运行增量更新
        changed_files = [str(test_repo / 'auth.py')]
        result = indexer.incremental_update(changed_files)

        assert result.files_processed == 1, f"Should process 1 file, got {result.files_processed}"
        assert result.symbols_count == 2, f"Should have 2 symbols after update, got {result.symbols_count}"

        print(f"✓ Incremental update: {result.files_processed} files, {result.symbols_count} symbols")

        # 验证数据库状态
        db = Database(db_path)
        auth_file = db.get_file('auth.py')
        symbols = db.get_symbols_by_file(auth_file.id) if auth_file else []

        # 应该有 authenticate 和 logout 两个函数
        symbol_names = [s.name for s in symbols]
        assert 'authenticate' in symbol_names, "Should have authenticate symbol"
        assert 'logout' in symbol_names, "Should have logout symbol"

        # authenticate 应该有更新的 docstring
        auth_sym = next(s for s in symbols if s.name == 'authenticate')
        assert 'updated' in auth_sym.docstring, "authenticate should have updated docstring"

        print("✓ Database state verified after update")


def test_incremental_update_skip_unchanged():
    """测试增量更新跳过未变更文件"""
    # 创建临时测试目录
    with tempfile.TemporaryDirectory() as test_dir:
        test_repo = Path(test_dir)
        db_path = str(test_repo / "test.db")

        # 创建初始文件
        test_file = test_repo / 'test.py'
        test_file.write_text('''
def test_func():
    """Test function"""
    pass
''')

        # 运行初始全量索引
        indexer = Indexer(str(test_repo), db_path)
        result = indexer.full_index()

        assert result.symbols_count == 1, "Should extract 1 symbol"

        print("✓ Initial index created")

        # 运行增量更新（文件未变更）
        result = indexer.incremental_update([str(test_file)])

        assert result.symbols_count == 0, "Should skip unchanged file (0 symbols)"

        print("✓ Incremental update skipped unchanged file")

        # 验证数据库中仍然只有 1 个符号
        db = Database(db_path)
        all_symbols = db.execute("SELECT COUNT(*) as count FROM symbols")
        assert all_symbols[0]['count'] == 1, "Should still have 1 symbol in DB"

        print("✓ Database unchanged for unmodified file")


def test_incremental_update_file_deletion():
    """测试文件删除的增量更新"""
    # 创建临时测试目录
    with tempfile.TemporaryDirectory() as test_dir:
        test_repo = Path(test_dir)
        db_path = str(test_repo / "test.db")

        # 创建初始文件
        test_file = test_repo / 'to_delete.py'
        test_file.write_text('''
def delete_me():
    """This will be deleted"""
    pass
''')

        (test_repo / 'keep.py').write_text('''
def keep_me():
    """This stays"""
    pass
''')

        # 运行初始全量索引
        indexer = Indexer(str(test_repo), db_path)
        result = indexer.full_index()

        assert result.symbols_count == 2, "Should extract 2 symbols"

        print("✓ Initial index created with 2 files")

        # 删除文件
        test_file.unlink()

        # 运行增量更新
        result = indexer.incremental_update([str(test_file)])

        print(f"✓ Deleted file processed")

        # 验证数据库状态
        db = Database(db_path)
        all_symbols = db.execute("SELECT COUNT(*) as count FROM symbols")
        assert all_symbols[0]['count'] == 1, "Should have 1 symbol after deletion"

        # 确保保留的文件还在
        keep_file = db.get_file('keep.py')
        keep_symbols = db.get_symbols_by_file(keep_file.id) if keep_file else []
        assert len(keep_symbols) == 1, "keep.py should still have its symbol"

        print("✓ File deletion handled correctly")


def test_incremental_update_call_edges():
    """测试增量更新后调用边正确解析"""
    # 创建临时测试目录
    with tempfile.TemporaryDirectory() as test:  # rename to avoid conflict
        test_repo = Path(test)
        db_path = str(test_repo / "test.db")

        # 创建初始文件
        (test_repo / 'caller.py').write_text('''
def caller():
    """Calls helper"""
    helper()
''')

        (test_repo / 'callee.py').write_text('''
def helper():
    """Helper function"""
    pass
''')

        # 运行初始全量索引
        indexer = Indexer(str(test_repo), db_path)
        result = indexer.full_index()

        print(f"✓ Initial index: {result.symbols_count} symbols, {result.call_edges_count} call edges")

        # 修改 caller 文件添加新的调用
        (test_repo / 'caller.py').write_text('''
def caller():
    """Calls helper and other"""
    helper()
    other()
''')

        (test_repo / 'callee.py').write_text('''
def helper():
    """Helper function"""
    pass

def other():
    """Other function"""
    pass
''')

        # 运行增量更新
        result = indexer.incremental_update([str(test_repo / 'caller.py'), str(test_repo / 'callee.py')])

        print(f"✓ Incremental update: {result.symbols_count} symbols, {result.call_edges_count} call edges")

        # 验证调用边
        db = Database(db_path)
        call_edges = db.execute("""
            SELECT COUNT(*) as count
            FROM call_edges
            WHERE callee_id IS NOT NULL
        """)

        print(f"✓ Resolved call edges: {call_edges[0]['count']}")

        # 应该有解析的调用边
        assert call_edges[0]['count'] > 0, "Should have resolved call edges"


if __name__ == '__main__':
    test_incremental_update()
    test_incremental_update_skip_unchanged()
    test_incremental_update_file_deletion()
    test_incremental_update_call_edges()
    print("\n✅ 所有增量更新测试通过！")

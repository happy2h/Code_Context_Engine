"""
调用图测试 (Phase 2)
"""

import pytest
import os
import tempfile
from engine.indexer import Indexer
from engine.query import QueryEngine
from engine.parser import SymbolExtractor


class TestCallGraph:
    """调用图功能测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")

        # 创建测试文件
        self.repo_root = self.temp_dir
        self.sample_file = os.path.join(self.repo_root, "test_calls.py")

        with open(self.sample_file, 'w') as f:
            f.write("""
def helper(x):
    return x * 2

def indirect_caller():
    return helper(5)

def direct_caller():
    result = helper(10)
    return indirect_caller()

def main():
    return direct_caller()
""")

        # 初始化索引器并执行索引
        self.indexer = Indexer(self.repo_root, self.db_path)
        self.indexer.full_index()

        # 初始化查询引擎
        self.engine = QueryEngine(self.db_path)

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_get_callers_direct(self):
        """测试获取直接调用者"""
        callers = self.engine.get_callers("helper", depth=1)

        # helper 被两个函数直接调用
        assert len(callers) >= 2

        caller_names = [c["symbol"]["name"] for c in callers]
        assert "indirect_caller" in caller_names
        assert "direct_caller" in caller_names

    def test_get_callers_multi_hop(self):
        """测试获取多跳调用者"""
        callers = self.engine.get_callers("helper", depth=2)

        # depth=2 应该包含 main -> direct_caller -> indirect_caller -> helper
        caller_names = [c["symbol"]["name"] for c in callers]
        assert "main" in caller_names

        # 验证深度信息
        main_caller = next(c for c in callers if c["symbol"]["name"] == "main")
        assert main_caller["depth"] > 1

    def test_get_callers_depth_zero(self):
        """测试深度为 0 的情况"""
        callers = self.engine.get_callers("helper", depth=0)
        assert callers == []

    def test_get_callees_direct(self):
        """测试获取直接被调用函数"""
        callees = self.engine.get_callees("direct_caller", depth=1)

        # direct_caller 直接调用 helper 和 indirect_caller
        callee_names = [c["symbol"]["name"] for c in callees]
        assert "helper" in callee_names
        assert "indirect_caller" in callee_names

    def test_get_callees_multi_hop(self):
        """测试获取多跳被调用函数"""
        callees = self.engine.get_callees("main", depth=2)

        # main -> direct_caller -> (helper, indirect_caller)
        callee_names = [c["symbol"]["name"] for c in callees]
        assert "direct_caller" in callee_names
        assert "helper" in callee_names
        assert "indirect_caller" in callee_names

    def test_get_context_window(self):
        """测试获取上下文窗口"""
        context = self.engine.get_context_window("indirect_caller", depth=1)

        assert context["found"] is True
        assert "center" in context
        assert "callers" in context
        assert "callees" in context
        assert "total_lines" in context
        assert "token_estimate" in context

        # 验证中心符号
        assert context["center"]["name"] == "indirect_caller"

        # 验证调用者
        assert len(context["callers"]) > 0

        # 验证被调用函数
        assert len(context["callees"]) > 0
        callee_names = [c["symbol"]["name"] for c in context["callees"]]
        assert "helper" in callee_names

    def test_get_context_window_not_found(self):
        """测试查询不存在的符号的上下文窗口"""
        context = self.engine.get_context_window("non_existent_function")
        assert context["found"] is False
        assert "message" in context

    def test_recursive_calls(self):
        """测试递归调用检测"""
        # 创建包含递归调用的文件
        recursive_file = os.path.join(self.repo_root, "recursive.py")

        with open(recursive_file, 'w') as f:
            f.write("""
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def main():
    return factorial(5)
""")

        # 重新索引
        self.indexer.full_index()
        self.engine = QueryEngine(self.db_path)

        # 验证递归调用被正确记录
        callees = self.engine.get_callees("factorial", depth=1)
        callee_names = [c["symbol"]["name"] for c in callees]
        assert "factorial" in callee_names  # 递归调用

    def test_cross_file_calls(self):
        """测试跨文件调用关系"""
        # 创建第二个文件
        file2 = os.path.join(self.repo_root, "module2.py")

        with open(file2, 'w') as f:
            f.write("""
def cross_file_function():
    return 42

def use_cross_file():
    return cross_file_function() + 1
""")

        # 修改第一个文件，添加跨文件调用
        with open(self.sample_file, 'w') as f:
            f.write("""
import sys

def helper(x):
    return x * 2

def use_external():
    # 这个调用在解析时不会被记录，因为是另一个模块的函数
    # 但同名函数会被解析
    return helper(5) + cross_file_function()

def main():
    return use_external()
""")

        # 重新索引
        self.indexer.full_index()
        self.engine = QueryEngine(self.db_path)

        # 验证跨文件调用被解析
        callees = self.engine.get_callees("use_external", depth=1)
        # helper 调用应该被记录
        callee_names = [c["symbol"]["name"] for c in callees]
        assert "helper" in callee_names


class TestCallGraphIntegration:
    """调用图集成测试 - 使用实际测试样本"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.repo_root = self.temp_dir

        # 复制测试样本文件到临时目录
        import shutil

        # 复制 Python 样本
        src_path = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "call_graph_sample.py"
        )
        self.py_sample = os.path.join(self.repo_root, "call_graph_sample.py")
        shutil.copy(src_path, self.py_sample)

        # 复制 TypeScript 样本
        src_path = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "call_graph_sample.ts"
        )
        self.ts_sample = os.path.join(self.repo_root, "call_graph_sample.ts")
        shutil.copy(src_path, self.ts_sample)

        # 初始化索引器并执行索引
        self.indexer = Indexer(self.repo_root, self.db_path)
        result = self.indexer.full_index()
        print(f"Indexed {result.files_processed} files, {result.symbols_count} symbols")

        # 初始化查询引擎
        self.engine = QueryEngine(self.db_path)

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_python_sample_call_graph(self):
        """测试 Python 样本的调用图"""
        # helper_function 应该被多个函数调用
        callers = self.engine.get_callers("helper_function", depth=2)
        caller_names = [c["symbol"]["name"] for c in callers]

        assert "fibonacci" in caller_names
        assert "process_data" in caller_names

        # process_data 的调用链
        callees = self.engine.get_callees("process_data", depth=1)
        callee_names = [c["symbol"]["name"] for c in callees]
        assert "helper_function" in callee_names

    def test_recursive_factorial(self):
        """测试递归 factorial 函数"""
        callers = self.engine.get_callers("recursive_factorial", depth=1)
        caller_names = [c["symbol"]["name"] for c in callers]
        assert "recursive_factorial" in caller_names  # 自调用

    def test_main_entry_orchestration(self):
        """测试 main_entry 函数的编排调用"""
        callees = self.engine.get_callees("main_entry", depth=1)
        callee_names = [c["symbol"]["name"] for c in callees]

        # main_entry 应该调用 process_data 和 fibonacci
        assert "process_data" in callee_names
        assert "fibonacci" in callee_names

    def test_typescript_method_calls(self):
        """测试 TypeScript 方法调用"""
        # UserService.validateUser 应该调用私有方法
        callees = self.engine.get_callees("validateUser", depth=1)
        callee_names = [c["symbol"]["name"] for c in callees]

        assert "validateEmail" in callee_names
        assert "validateName" in callee_names

    def test_typescript_class_interaction(self):
        """测试 TypeScript 类之间的交互"""
        # AuthService 应该使用 UserService
        callees = self.engine.get_callees("authenticate", depth=1)
        callee_names = [c["symbol"]["name"] for c in callees]

        # findUserById 应该被调用
        assert "findUserById" in callee_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

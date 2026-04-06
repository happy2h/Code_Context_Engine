"""
解析器测试
"""

import pytest
from pathlib import Path
from engine.parser import SymbolExtractor


class TestSymbolExtractor:
    """符号提取器测试"""

    def setup_method(self):
        """设置测试环境"""
        self.parser = SymbolExtractor()

    def test_detect_language_python(self):
        """测试 Python 语言检测"""
        assert self.parser.detect_language("test.py") == "python"
        assert self.parser.detect_language("module.py") == "python"
        assert self.parser.detect_language("README.md") is None

    def test_detect_language_typescript(self):
        """测试 TypeScript 语言检测"""
        assert self.parser.detect_language("test.ts") == "typescript"
        assert self.parser.detect_language("component.tsx") == "typescript"

    def test_detect_language_javascript(self):
        """测试 JavaScript 语言检测"""
        assert self.parser.detect_language("test.js") == "javascript"
        assert self.parser.detect_language("component.jsx") == "javascript"

    def test_detect_language_go(self):
        """测试 Go 语言检测"""
        assert self.parser.detect_language("main.go") == "go"

    def test_detect_language_rust(self):
        """测试 Rust 语言检测"""
        assert self.parser.detect_language("main.rs") == "rust"

    def test_detect_language_java(self):
        """测试 Java 语言检测"""
        assert self.parser.detect_language("Main.java") == "java"

    def test_extract_python_functions(self):
        """测试 Python 函数提取"""
        fixtures_dir = Path(__file__).parent / "fixtures"
        sample_file = fixtures_dir / "sample_python.py"

        symbols, call_edges = self.parser.extract(str(sample_file), "python")

        # 检查是否提取到符号
        assert len(symbols) > 0

        # 检查是否有类
        classes = [s for s in symbols if s['kind'] == 'class']
        assert any('UserService' in s['name'] for s in classes)

        # 检查是否有函数
        functions = [s for s in symbols if s['kind'] == 'function']
        function_names = [f['name'] for f in functions]
        assert 'authenticate_user' in function_names
        assert 'validate_user' in function_names
        assert 'generate_token' in function_names

    def test_extract_python_class_methods(self):
        """测试 Python 类方法提取"""
        fixtures_dir = Path(__file__).parent / "fixtures"
        sample_file = fixtures_dir / "sample_python.py"

        symbols, call_edges = self.parser.extract(str(sample_file), "python")

        # 检查 UserService 类的方法
        user_service_methods = [
            s for s in symbols
            if s['parent_name'] == 'UserService'
        ]
        method_names = [m['name'] for m in user_service_methods]
        assert '__init__' in method_names
        assert 'get_user' in method_names
        assert 'create_user' in method_names

    def test_extract_python_docstrings(self):
        """测试 Python docstring 提取"""
        fixtures_dir = Path(__file__).parent / "fixtures"
        sample_file = fixtures_dir / "sample_python.py"

        symbols, call_edges = self.parser.extract(str(sample_file), "python")

        # 检查是否有 docstring
        with_docstring = [s for s in symbols if s.get('docstring')]
        assert len(with_docstring) > 0

        # 检查特定函数的 docstring
        auth_func = next(
            (s for s in symbols if s['name'] == 'authenticate_user'),
            None
        )
        assert auth_func is not None
        assert auth_func.get('docstring') is not None
        assert '用户认证' in auth_func['docstring']

    def test_extract_typescript_symbols(self):
        """测试 TypeScript 符号提取"""
        fixtures_dir = Path(__file__).parent / "fixtures"
        sample_file = fixtures_dir / "sample_typescript.ts"

        symbols, call_edges = self.parser.extract(str(sample_file), "typescript")

        # 检查是否提取到符号
        assert len(symbols) > 0

        # 检查是否有类
        classes = [s for s in symbols if s['kind'] == 'class']
        assert any('AuthService' in s['name'] for s in classes)

    def test_calculate_hash(self):
        """测试哈希计算"""
        fixtures_dir = Path(__file__).parent / "fixtures"
        sample_file = fixtures_dir / "sample_python.py"

        hash1 = self.parser.calculate_hash(str(sample_file))
        hash2 = self.parser.calculate_hash(str(sample_file))

        # 相同文件的哈希应该相同
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 生成 64 字符的十六进制字符串


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

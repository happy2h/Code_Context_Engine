"""
Context Engine 解析层

使用 tree-sitter 解析源文件，提取符号信息和调用关系。
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import hashlib
from engine.logger import Logger
from engine.retry import safe_execute


class SymbolExtractor:
    """符号提取器基类"""

    # 语言对应的 tree-sitter 节点类型
    FUNCTION_NODES = {
        "python": ["function_definition", "class_definition", "decorated_definition"],
        "typescript": ["function_declaration", "method_definition", "arrow_function", "class_declaration"],
        "javascript": ["function_declaration", "method_definition", "arrow_function", "class_declaration"],
        "go": ["function_declaration", "method_declaration", "type_declaration"],
        "rust": ["function_item", "impl_item", "struct_item", "enum_item"],
        "java": ["method_declaration", "class_declaration", "interface_declaration"],
    }

    # 调用节点类型
    CALL_NODES = {
        "python": "call",
        "typescript": "call_expression",
        "javascript": "call_expression",
        "go": "call_expression",
        "rust": "call_expression",
        "java": "call_expression",
    }

    def __init__(self):
        self._parsers = {}
        self._languages = {}
        self.logger = Logger()
        self._init_parsers()

    def _init_parsers(self):
        """初始化各语言的解析器"""
        try:
            from tree_sitter import Language, Parser
        except ImportError:
            raise ImportError("tree-sitter not installed. Run: pip install tree-sitter")

        # 导入各语言的 grammar
        lang_modules = {
            "python": "tree_sitter_python",
            "typescript": "tree_sitter_typescript",
            "javascript": "tree_sitter_javascript",
            "go": "tree_sitter_go",
            "rust": "tree_sitter_rust",
            "java": "tree_sitter_java",
        }

        for lang, module_name in lang_modules.items():
            try:
                lang_module = __import__(module_name)
                language = Language(lang_module.language())

                parser = Parser(language)

                self._languages[lang] = language
                self._parsers[lang] = parser
            except ImportError:
                print(f"Warning: {module_name} not installed, skipping {lang} support")
            except Exception as e:
                print(f"Warning: Failed to initialize parser for {lang}: {e}")

    def detect_language(self, file_path: str) -> Optional[str]:
        """根据文件扩展名检测语言"""
        ext = Path(file_path).suffix.lower()

        lang_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
        }

        return lang_map.get(ext)

    def calculate_hash(self, file_path: str) -> str:
        """计算文件内容的 SHA256 哈希"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def extract(self, file_path: str, lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """从文件提取所有符号信息

        Args:
            file_path: 文件路径
            lang: 语言类型，如果为 None 则自动检测

        Returns:
            符号信息列表
        """
        if lang is None:
            lang = self.detect_language(file_path)

        if lang is None:
            return []

        if lang not in self._parsers:
            self.logger.warning(f"No parser available for language: {lang}", file=file_path)
            return []

        # 安全读取文件内容
        source = safe_execute(
            lambda: Path(file_path).read_bytes(),
            default=None,
            logger=self.logger
        )
        if source is None:
            self.logger.error(f"Failed to read file: {file_path}")
            return []

        # 解析文件
        parser = self._parsers[lang]
        tree = parser.parse(source)

        # 遍历 AST 提取符号
        symbols = []
        call_edges = []

        self._walk(tree.root_node, source, lang, symbols, call_edges, parent_name=None)

        # 计算符号复杂度
        for sym in symbols:
            sym['complexity'] = self._estimate_complexity(sym['body'])

        return symbols, call_edges

    def _walk(self, node, source: bytes, lang: str,
              symbols: List[Dict], call_edges: List[Dict],
              parent_name: Optional[str] = None,
              current_symbol: Optional[Dict] = None):
        """递归遍历 AST 节点

        Args:
            node: tree-sitter 节点
            source: 源码字节数组
            lang: 语言类型
            symbols: 符号列表（输出）
            call_edges: 调用边列表（输出）
            parent_name: 父级符号名称
            current_symbol: 当前符号信息（用于提取调用关系）
        """
        function_nodes = self.FUNCTION_NODES.get(lang, [])
        call_node_type = self.CALL_NODES.get(lang)

        # 提取符号
        if node.type in function_nodes:
            symbol = self._extract_symbol(node, source, lang, parent_name)
            if symbol:
                symbols.append(symbol)
                # 继续遍历子节点，但更新当前符号上下文
                for child in node.children:
                    self._walk(child, source, lang, symbols, call_edges,
                              symbol['name'], symbol)
            return

        # 提取调用关系
        if call_node_type and node.type == call_node_type and current_symbol:
            self._extract_call_edges(node, current_symbol, call_edges, lang)

        # 递归遍历子节点
        for child in node.children:
            self._walk(child, source, lang, symbols, call_edges, parent_name, current_symbol)

    def _extract_symbol(self, node, source: bytes, lang: str,
                        parent_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """从节点提取符号信息"""
        try:
            # 获取节点内容
            content = source[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')

            # 解析符号信息
            name, kind = self._extract_name_and_kind(node, lang)
            if not name:
                return None

            signature = self._extract_signature(node, lang, source)
            docstring = self._extract_docstring(node, lang, source)
            is_exported = self._extract_is_exported(node, lang)

            return {
                'name': name,
                'kind': kind,
                'signature': signature,
                'docstring': docstring,
                'body': content,
                'line_start': node.start_point[0] + 1,  # tree-sitter 是 0-based
                'line_end': node.end_point[0] + 1,
                'col_start': node.start_point[1] + 1,
                'col_end': node.end_point[1] + 1,
                'parent_name': parent_name,
                'is_exported': 1 if is_exported else 0,
            }
        except Exception as e:
            print(f"Error extracting symbol from node: {e}")
            return None

    def _extract_name_and_kind(self, node, lang: str) -> tuple[Optional[str], str]:
        """提取符号名称和类型"""
        kind = node.type

        # 根据 node 类型提取名称
        if lang == "python":
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "function"
            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "class"
            elif node.type == "decorated_definition":
                # 获取装饰的函数或类
                for child in node.children:
                    if child.type in ["function_definition", "class_definition"]:
                        return self._extract_name_and_kind(child, lang)

        elif lang in ["typescript", "javascript"]:
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "function"
            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "method"
            elif node.type == "arrow_function":
                return None, "function"  # 匿名函数
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "class"

        elif lang == "go":
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "function"
            elif node.type == "method_declaration":
                receiver = node.child_by_field_name("receiver")
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode('utf-8')
                    if receiver:
                        kind = "method"
                    return name, kind
            elif node.type == "type_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "type"

        elif lang == "rust":
            if node.type == "function_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "function"
            elif node.type == "struct_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "struct"
            elif node.type == "enum_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "enum"
            elif node.type == "impl_item":
                return None, "impl"

        elif lang == "java":
            if node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "method"
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "class"
            elif node.type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode('utf-8'), "interface"

        return None, kind

    def _extract_signature(self, node, lang: str, source: bytes) -> Optional[str]:
        """提取函数签名"""
        try:
            if lang == "python":
                if node.type == "function_definition":
                    # 找到 : 的位置，截取签名
                    content = source[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')
                    colon_pos = content.find(':')
                    if colon_pos != -1:
                        return content[:colon_pos].strip()
            elif lang in ["typescript", "javascript"]:
                if node.type == "function_declaration":
                    content = source[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')
                    brace_pos = content.find('{')
                    if brace_pos != -1:
                        return content[:brace_pos].strip()
            # 更多语言的签名提取...
        except Exception:
            pass
        return None

    def _extract_docstring(self, node, lang: str, source: bytes) -> Optional[str]:
        """提取文档字符串"""
        try:
            if lang == "python":
                if node.type == "function_definition":
                    # Python 函数体中的第一个字符串表达式是 docstring
                    body_node = node.child_by_field_name("body")
                    if body_node:
                        for child in body_node.children:
                            if child.type == "expression_statement":
                                string_node = child.children[0]
                                if string_node.type in ["string", "string_content"]:
                                    text = string_node.text.decode('utf-8', errors='ignore')
                                    # 去除引号
                                    if text.startswith('"""') or text.startswith("'''"):
                                        text = text[3:-3]
                                    elif text.startswith('"') or text.startswith("'"):
                                        text = text[1:-1]
                                    return text.strip()
            # 其他语言的注释提取可以后续添加
        except Exception:
            pass
        return None

    def _extract_is_exported(self, node, lang: str) -> bool:
        """判断是否为导出符号"""
        # TypeScript/JavaScript: 检查是否有 export 关键字
        if lang in ["typescript", "javascript"]:
            for child in node.children:
                if child.type == "export_clause" or (child.type == "identifier" and child.text == b"export"):
                    return True
        return False

    def _extract_call_edges(self, node, caller: Dict, call_edges: List[Dict], lang: str):
        """从调用节点提取调用关系"""
        try:
            function_node = node.child_by_field_name("function")
            if not function_node:
                return

            # 提取被调用的名称
            callee_name = self._extract_callee_name(function_node, lang)
            if callee_name:
                call_line = node.start_point[0] + 1
                call_edges.append({
                    'caller_name': caller['name'],
                    'callee_name': callee_name,
                    'call_line': call_line,
                    'call_type': 'direct'
                })
        except Exception:
            pass

    def _extract_callee_name(self, node, lang: str) -> Optional[str]:
        """提取被调用函数的名称"""
        try:
            if lang == "python":
                # 处理直接函数调用: func()
                if node.type == "identifier":
                    return node.text.decode('utf-8')
                # 处理方法调用: obj.method() 或 obj.attr.method()
                elif node.type == "attribute":
                    # 递归获取完整的链式调用路径
                    parts = []
                    current = node
                    while current:
                        if current.type == "identifier":
                            parts.append(current.text.decode('utf-8'))
                            break
                        elif current.type == "attribute":
                            # attribute: obj . attr
                            attr = current.child_by_field_name("attribute")
                            if attr:
                                if attr.type == "identifier":
                                    parts.append(attr.text.decode('utf-8'))
                                elif attr.type == "attribute":
                                    # 继续递归处理嵌套的 attribute
                                    sub_parts = []
                                    sub_current = attr
                                    while sub_current:
                                        if sub_current.type == "identifier":
                                            sub_parts.append(sub_current.text.decode('utf-8'))
                                            break
                                        elif sub_current.type == "attribute":
                                            sub_attr = sub_current.child_by_field_name("attribute")
                                            if sub_attr and sub_attr.type == "identifier":
                                                sub_parts.append(sub_attr.text.decode('utf-8'))
                                            val = sub_current.child_by_field_name("value")
                                            if val and val.type == "identifier":
                                                sub_parts.append(val.text.decode('utf-8'))
                                            break
                                        sub_current = None
                                    parts.extend(sub_parts)
                                    break
                            val = current.child_by_field_name("value")
                            if val and val.type == "identifier":
                                parts.append(val.text.decode('utf-8'))
                            break
                        current = None
                    if parts:
                        parts.reverse()
                        return ".".join(parts)

            elif lang in ["typescript", "javascript"]:
                # 处理直接函数调用: func()
                if node.type == "identifier":
                    return node.text.decode('utf-8')
                # 处理成员访问: obj.method() 或 obj?.method()
                elif node.type == "member_expression":
                    # 获取属性名
                    property = node.child_by_field_name("property")
                    if property:
                        if property.type == "property_identifier":
                            return property.text.decode('utf-8')
                        elif property.type == "identifier":
                            return property.text.decode('utf-8')
                # 处理链式调用: a.b.c()
                elif node.type == "call_expression":
                    func = node.child_by_field_name("function")
                    if func:
                        return self._extract_callee_name(func, lang)
                # 处理子表达式: (func)()
                elif node.type == "parenthesized_expression":
                    if node.children:
                        return self._extract_callee_name(node.children[0], lang)

            elif lang == "go":
                # 处理直接函数调用: func()
                if node.type == "identifier":
                    return node.text.decode('utf-8')
                # 处理选择器表达式: obj.method() 或 pkg.Func()
                elif node.type == "selector_expression":
                    # 获取字段名
                    field = node.child_by_field_name("field")
                    if field:
                        return field.text.decode('utf-8')
                # 处理包调用: pkg.Func()
                elif node.type == "identifier":
                    return node.text.decode('utf-8')

            elif lang == "rust":
                # 处理直接函数调用: func()
                if node.type == "identifier":
                    return node.text.decode('utf-8')
                # 处理路径表达式: std::vec::new()
                elif node.type == "identifier":
                    return node.text.decode('utf-8')
                # 处理字段表达式: obj.method()
                elif node.type == "field_expression":
                    field = node.child_by_field_name("field")
                    if field:
                        return field.text.decode('utf-8')

            elif lang == "java":
                # 处理直接方法调用: func()
                if node.type == "identifier":
                    return node.text.decode('utf-8')
                # 处理字段访问: obj.method()
                elif node.type == "field_access":
                    field = node.child_by_field_name("field")
                    if field:
                        return field.text.decode('utf-8')
                # 处理 this.method()
                elif node.type == "this":
                    return "this"

        except Exception:
            pass
        return None

    def _estimate_complexity(self, body: str) -> int:
        """估算圈复杂度"""
        complexity = 1  # 基础复杂度

        # 统计控制流关键字
        keywords = ["if", "elif", "else", "for", "while", "case", "switch",
                     "try", "except", "catch", "?", ":", "and", "or"]

        body_lower = body.lower()
        for keyword in keywords:
            complexity += body_lower.count(keyword)

        # 统计运算符
        operators = ["&&", "||", "??"]
        for op in operators:
            complexity += body.count(op)

        return complexity

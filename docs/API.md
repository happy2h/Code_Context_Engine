# Context Engine API 文档

本文档详细描述 Context Engine 提供的所有 MCP 工具接口。

## 工具列表

### 1. get_symbol

获取指定名称的符号（函数/类/方法）的完整源码。

**参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 符号名称，支持通配符（如 `parse*`） |
| file | string | 否 | 限定文件范围，支持部分匹配 |
| kind | string | 否 | 符号类型：`function`, `method`, `class` |

**返回值:**

```json
{
  "found": true,
  "symbol": {
    "id": 123,
    "file": "src/auth/token.py",
    "lang": "python",
    "name": "parseUserToken",
    "kind": "function",
    "signature": "def parseUserToken(raw: str) -> Token:",
    "docstring": "Parses and validates a JWT token string",
    "body": "def parseUserToken(raw: str) -> Token:\n    ...",
    "line_start": 42,
    "line_end": 67,
    "col_start": 0,
    "col_end": 28,
    "parent": null,
    "is_exported": true,
    "complexity": 3
  }
}
```

**未找到时返回:**

```json
{
  "found": false,
  "message": "Symbol 'parseUserToken' not found"
}
```

**示例:**

```python
# 获取指定符号
get_symbol(name="parseUserToken")

# 在特定文件中查找
get_symbol(name="handleLogin", file="auth.py")

# 获取特定类型的符号
get_symbol(name="User", kind="class")

# 使用通配符
get_symbol(name="parse*")
```

---

### 2. search_code

根据查询搜索符号（全文搜索），基于 SQLite FTS5 实现。

**参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| query | string | 是 | 搜索查询字符串（支持 FTS5 MATCH 语法） |
| limit | integer | 否 | 返回结果数量，默认 10 |
| lang | string | 否 | 限定语言类型：`python`, `typescript`, `go` 等 |

**返回值:**

```json
{
  "query": "用户认证",
  "total": 5,
  "results": [
    {
      "id": 123,
      "file": "src/auth/token.py",
      "lang": "python",
      "name": "parseUserToken",
      "kind": "function",
      "signature": "def parseUserToken(raw: str) -> Token:",
      "line_start": 42,
      "line_end": 67,
      "parent": null,
      "is_exported": true
    }
  ]
}
```

**搜索语法:**

- 简单关键词：`parse token`
- 短语匹配：`"user authentication"`
- 布尔运算：`parse AND token`, `function OR method`
- 前缀匹配：`parse*`
- 排除关键词：`parse -token`

**示例:**

```python
# 简单搜索
search_code(query="用户认证")

# 限制结果数量
search_code(query="parse", limit=20)

# 限定语言
search_code(query="async function", lang="javascript")

# 复杂查询
search_code(query="parse AND (token OR auth)")
```

---

### 3. get_callers

获取调用指定符号的所有上层函数（调用者）。

**参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| symbol_name | string | 是 | 符号名称 |
| depth | integer | 否 | 查询深度，默认 1（仅直接调用者），最大 10 |

**返回值:**

```json
{
  "symbol_name": "validateToken",
  "depth": 2,
  "total": 3,
  "callers": [
    {
      "depth": 1,
      "symbol": {
        "id": 456,
        "file": "src/auth/middleware.py",
        "name": "authMiddleware",
        "kind": "function",
        ...
      }
    },
    {
      "depth": 2,
      "symbol": {
        "id": 789,
        "file": "src/api/routes.py",
        "name": "handleLogin",
        "kind": "function",
        ...
      }
    }
  ]
}
```

**示例:**

```python
# 获取直接调用者
get_callers(symbol_name="validateToken")

# 获取多层调用者（包括间接调用）
get_callers(symbol_name="validateToken", depth=2)
```

---

### 4. get_callees

获取指定符号调用的所有下层函数（被调用函数）。

**参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| symbol_name | string | 是 | 符号名称 |
| depth | integer | 否 | 查询深度，默认 1（仅直接调用），最大 10 |

**返回值:**

```json
{
  "symbol_name": "handleLogin",
  "depth": 2,
  "total": 4,
  "callees": [
    {
      "depth": 1,
      "symbol": {
        "id": 123,
        "file": "src/auth/token.py",
        "name":": parseUserToken",
        "kind": "function",
        ...
      }
    },
    {
      "depth": 1,
      "symbol": {
        "id": 234,
        "file": "src/auth/validate.py",
        "name": "validateSession",
        "kind": "function",
        ...
      }
    }
  ]
}
```

**示例:**

```python
# 获取直接调用的函数
get_callees(symbol_name="handleLogin")

# 获取多层调用关系
get_callees(symbol_name="handleRequest", depth=3)
```

---

### 5. get_context_window

获取符号的完整上下文窗口，包含调用者和被调用者。

**参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| symbol_name | string | 是 | 符号名称 |
| depth | integer | 否 | 查询深度，默认 1，最大 10 |

**返回值:**

```json
{
  "found": true,
  "center": {
    "id": 123,
    "file": "src/api/handler.py",
    "name": "handleLogin",
    "kind": "function",
    ...
  },
  "callers": [
    {
      "depth": 1,
      "symbol": { ... }
    }
  ],
  "callees": [
    {
      "depth": 1,
      "symbol": { ... }
    }
  ],
  "total_lines": 127,
  "token_estimate": 680
}
```

**未找到时返回:**

```json
{
  "found": false,
  "message": "Symbol 'handleLogin' not found"
}
```

**说明:**
- `total_lines`: 上下文窗口包含的总行数
- `token_estimate`: 粗略的 token 估算（约 4 字符/token）

**示例:**

```python
# 获取基本上下文
get_context_window(symbol_name="handleLogin")

# 获取更深的调用上下文
get_context_window(symbol_name="processData", depth=2)
```

---

### 6. get_file_outline

获取文件内所有符号的大纲（不含函数体）。

**参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file_path | string | 是 | 文件路径（相对于仓库根） |

**返回值:**

```json
{
  "file": "src/auth/token.py",
  "symbols": [
    {
      "id": 123,
      "file": "src/auth/token.py",
      "lang": "python",
      "name": "parseUserToken",
      "kind": "function",
      "signature": "def parseUserToken(raw: str) -> Token:",
      "line_start": 42,
      "line_end": 67,
      "parent": null,
      "is_exported": true
    },
    {
      "id": 124,
      "file": "src/auth/token.py",
      "name": "validateSession",
      "kind": "function",
      ...
    }
  ]
}
```

**示例:**

```python
get_file_outline(file_path="src/api/users.py")
```

---

### 7. list_symbols

根据条件筛选符号列表。

**参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| kind | string | 否 | 符号类型：`function`, `method`, `class` |
| lang | string | 否 | 语言类型：`python`, `typescript`, `go` 等 |
| file | string | 否 | 文件路径（支持部分匹配） |

**返回值:**

```json
{
  "total": 25,
  "symbols": [
    {
      "id": 123,
      "file": "src/auth/token.py",
      "name": "parseUserToken",
      "kind": "function",
      ...
    }
  ]
}
```

**示例:**

```python
# 列出所有函数
list_symbols(kind="function")

# 列出 Python 中的所有类
list_symbols(kind="class", lang="python")

# 列出特定文件中的符号
list_symbols(file="auth.py")
```

---

### 8. index_status

获取当前索引状态和统计信息。

**参数:**

无

**返回值:**

```json
{
  "schema_version": "1",
  "engine_version": "1.0.0",
  "repo_root": "/path/to/repo",
  "created_at": "2024-01-01T00:00:00",
  "last_full_index": "2024-01-01T12:00:00",
  "total_files": 150,
  "total_symbols": 2345,
  "total_call_edges": 5678,
  "cache_stats": {
    "size": 125,
    "max_size": 1000,
    "hits": 8923,
    "misses": 456,
    "hit_rate": 95.13
  }
}
```

**示例:**

```python
index_status()
```

---

## 符号记录字段说明

所有返回的符号记录包含以下字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 符号唯一标识符 |
| file | string | 文件路径（相对于仓库根） |
| lang | string | 语言类型 |
| name | string | 符号名称 |
| kind | string | 符号类型：`function`, `method`, `class`, `variable` |
| signature | string | 完整函数签名（仅函数/方法） |
| docstring | string | 文档字符串/注释 |
| body | string | 完整源码（`get_file_outline` 不包含此字段） |
| line_start | integer | 起始行号（从 1 开始） |
| line_end | integer | 结束行号 |
| col_start | integer | 起始列号 |
| col_end | integer | 结束列号 |
| parent | string | 所属类名（方法时填充） |
| is_exported | boolean | 是否为导出符号（`public`, `export`） |
| complexity | integer | 圈复杂度估算 |

---

## 性能建议

### 查询优化

1. **使用缓存**: 相同查询会自动缓存，重复调用无需担心性能
2. **合理使用深度**: 调用图查询深度不宜过大（建议 ≤ 3）
3. **限制结果数量**: 搜索时设置合理的 `limit` 参数

### 索引优化

1. **及时索引**: 代码变更后确保索引已更新
2. **排除无用文件**: 通过 `.gitignore` 和配置排除不必要的文件
3. **调整并行度**: 根据 CPU 核心数调整 `CE_PARALLEL_WORKERS`

---

## 错误处理

所有工具在遇到错误时会返回包含错误信息的响应：

```json
{
  "error": "错误类型",
  "message": "详细错误信息"
}
```

常见错误：

- `SymbolNotFoundError`: 符号未找到
- `FileNotFoundError`: 文件不存在
- `DatabaseError`: 数据库操作失败
- `ParseError`: 解析文件失败

# Context Engine

基于 tree-sitter 的代码索引与查询引擎，通过 MCP stdio 协议与 Claude Code 通信，提供符号查找、调用图遍历、文件大纲等能力。

## 特性

- **多语言支持**: Python, TypeScript, JavaScript, Go, Rust, Java
- **符号提取**: 函数、类、方法的完整信息（签名、注释、源码）
- **调用图分析**: 支持多层调用关系查询（调用者/被调用者）
- **全文搜索**: 基于 SQLite FTS5 的高效语义搜索
- **增量更新**: 文件变化时自动更新索引
- **高性能**: L 查询缓存、WAL 模式、并行索引构建

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-org/context-engine.git
cd context-engine

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置

创建 `.env` 文件（可选）：

```env
CE_DB_PATH=~/.context-engine/my-repo.db
CE_REPO_ROOT=/path/to/your/repo
CE_LOG_LEVEL=INFO
CE_ENABLE_CACHE=true
CE_CACHE_SIZE=1000
```

### 索引仓库

```bash
# 全量索引
ce index /path/to/your/repo

# 查看索引状态
ce status
```

### 启动 MCP Server

```bash
ce serve
```

### 集成到 Claude Code

在项目根目录创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "context-engine": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/context-engine/server.py"],
      "env": {
        "CE_REPO_ROOT": "${workspaceFolder}",
        "CE_DB_PATH": "${workspaceFolder}/.ce/index.db",
        "CE_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

## MCP 工具

### get_symbol

获取指定名称的符号（函数/类/方法）的完整源码。

**参数:**
- `name` (必填): 符号名称
- `file` (可选): 限定文件范围
- `kind` (可选): 符号类型（function/method/class）

**示例:**
```python
get_symbol(name="parseUserToken")
get_symbol(name="handleLogin", file="auth.py")
```

### search_code

根据查询搜索符号（全文搜索）。

**参数:**
- `query` (必填): 搜索查询字符串
- `limit` (可选): 返回结果数量，默认 10
- `lang` (可选): 限定语言类型

**示例:**
```python
search_code(query="用户认证")
search_code(query="parse", limit=20, lang="python")
```

### get_callers

获取调用指定符号的所有上层函数（调用者）。

**参数:**
- `symbol_name` (必填): 符号名称
- `depth` (可选): 查询深度，默认 1

**示例:**
```python
get_callers(symbol_name="validateToken", depth=2)
```

### get_callees

获取指定符号调用的所有下层函数（被调用函数）。

**参数:**
- `symbol_name` (必填): 符号名称
- `depth` (可选): 查询深度，默认 1

**示例:**
```python
get_callees(symbol_name="handleRequest", depth=2)
```

### get_context_window

获取符号的完整上下文窗口，包含调用者和被调用者。

**参数:**
- `symbol_name` (必填): 符号名称
- `depth` (可选): 查询深度，默认 1

**示例:**
```python
get_context_window(symbol_name="processData", depth=1)
```

### get_file_outline

获取文件内所有符号的大纲（不含函数体）。

**参数:**
- `file_path` (必填): 文件路径

**示例:**
```python
get_file_outline(file_path="src/api/users.py")
```

### list_symbols

根据条件筛选符号列表。

**参数:**
- `kind` (可选): 符号类型（function/method/class）
- `lang` (可选): 语言类型
- `file` (可选): 文件路径

**示例:**
```python
list_symbols(kind="function", lang="python")
list_symbols(file="auth.py")
```

### index_status

获取当前索引状态和统计信息。

**示例:**
```python
index_status()
```

## CLI 命令

### ce index

对指定仓库执行全量索引。

```bash
ce index /path/to/repo
```

### ce status

显示当前索引状态和统计信息。

```bash
ce status
```

### ce watch

启动文件监听，自动增量更新。

```bash
ce watch /path/to/repo
```

### ce query

命令行直接查询符号（调试用）。

```bash
ce query "parseUserToken"
```

### ce search

全文搜索符号。

```bash
ce search "用户认证逻辑"
```

### ce reindex

强制重建全量索引。

```bash
ce reindex --force
```

### ce serve

以 MCP Server 模式启动。

```bash
ce serve
```

## 配置选项

| 环境变量 | 默认值 | 说明 |
|-----------|--------|------|
| `CE_DB_PATH` | `~/.context-engine/{repo_hash}.db` | SQLite 数据库文件路径 |
| `CE_REPO_ROOT` | 当前工作目录 | 索引的仓库根目录 |
| `CE_EXCLUDE_PATTERNS` | `node_modules,__pycache__,.git,dist,build` | 排除目录/文件模式 |
| `CE_MAX_FILE_SIZE` | `500000` | 最大文件大小（字节） |
| `CE_PARALLEL_WORKERS` | `4` | 并行解析的线程数 |
| `CE_WATCHER_DEBOUNCE` | `0.5` | 文件变更防抖时间（秒） |
| `CE_LOG_LEVEL` | `INFO` | 日志级别：DEBUG/INFO/WARNING/ERROR |
| `CE_ENABLE_CACHE` | `true` | 是否启用查询缓存 |
| `CE_CACHE_SIZE` | `1000` | 缓存最大条目数 |
| `CE_JSON_LOGS` | `false` | 是否使用 JSON 格式输出日志 |
| `CE_LOG_FILE` | `None` | 日志文件路径（可选） |

## 性能指标

| 指标 | 目标值 | 测量方法 |
|------|--------|----------|
| 全量索引（10 万行仓库） | < 30 秒 | `ce index + time` |
| 增量更新（单文件修改） | < 200 ms | watchdog 事件到 DB 写入完成 |
| get_symbol 查询 | < 5 ms (p99) | 1000 次随机查询取 p99 |
| search_code 全文搜索 | < 30 ms (p99) | FTS5 查询基准测试 |
| get_context_window (depth=2) | < 100 ms (p99) | 递归 CTE 查询基准 |
| DB 文件大小（10 万行仓库） | < 50 MB | `du -sh *.db` |
| 内存占用（MCP Server 空闲） | < 80 MB | psutil 监控 |

## 已知限制

- **动态语言精度**: Python 的动态类型导致部分间接调用无法静态分析
- **跨语言仓库**: 同一函数调用跨语言暂不追踪
- **宏/装饰器**: 高度宏展开的代码符号提取可能不完整
- **全文搜索质量**: FTS5 基于词法匹配，中文代码注释需配合分词

## 开发

### 运行测试

```bash
pytest tests/
pytest --cov=engine --cov-report=html
```

### 性能基准测试

```bash
pytest tests/test_benchmark.py
```

### 代码风格

```bash
black engine/ server.py cli.py
flake8 engine/ server.py cli.py
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

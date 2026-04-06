# Context Engine Windows 安装使用手册

Context Engine 是一个基于 tree-sitter 的代码索引与查询引擎，通过 MCP stdio 协议与 Claude Code 通信，提供符号查找、调用图遍历、全文搜索等能力。

## 目录

1. [环境准备](#环境准备)
2. [安装项目](#安装项目)
3. [配置虚拟环境](#配置虚拟环境)
4. [使用 ce 命令](#使用-ce-命令)
5. [配置 MCP 服务](#配置-mcp-服务)
6. [集成到 Claude Code](#集成到-claude-code)
7. [常见问题](#常见问题)

## 环境准备

### 1. 安装 Python

Context Engine 需要 Python 3.11 或更高版本。

**下载地址**: https://www.python.org/downloads/windows/

安装时注意：
- 勾选 "Add Python to PATH" 选项
- 安装完成后，在 PowerShell 或 CMD 中运行以下命令验证：

```powershell
python --version
```

### 2. 安装 Poetry

Poetry 是现代 Python 项目管理和依赖打包工具。

**安装方法**（使用 PowerShell）：

```powershell
# 方法一：使用官方安装脚本
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# 方法二：使用 pip
pip install poetry
```

安装完成后，重启 PowerShell 或 CMD，验证安装：

```powershell
poetry --version
```

### 3. 配置 Poetry（可选）

建议配置 Poetry 使用虚拟环境在项目目录下：

```powershell
# 设置在项目中创建虚拟环境
poetry config virtualenvs.in-project true

# 设置使用系统 Python
poetry config virtualenvs.prefer-active-python true
```

## 安装项目

### 1. 克隆或下载项目

```powershell
# 使用 Git 克隆（推荐）
git clone https://github.com/happy2h/Code_Context_Engine.git
cd context-engine

# 或直接下载 ZIP 解压后进入目录
```

### 2. 使用 Poetry 安装依赖

```powershell
# 安装项目依赖
poetry install

# 如需安装开发依赖（测试工具等）
poetry install --with dev
```

### 3. 验证安装

```powershell
# 激活虚拟环境并检查 Python 版本
poetry run python --version

# 列出已安装的依赖
poetry show
```

## 配置虚拟环境

### 创建虚拟环境

Poetry 会自动创建虚拟环境，默认位置在：

```powershell
# 激活虚拟环境
poetry shell
```

激活后，命令行提示符前会出现 `(context-engine-py3.xx)` 前缀。

### 常用 Poetry 命令

```powershell
# 激活虚拟环境
poetry shell

# 在虚拟环境中执行命令
poetry run <command>

# 示例：运行 Python 脚本
poetry run python script.py

# 示例：运行 ce 命令
poetry run ce --help

# 退出虚拟环境
exit
```

### 手动安装依赖（不使用 Poetry）

如果不想使用 Poetry，可以使用传统的 venv 方式：

```powershell
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（
.venv\Scripts\activate

# 升级 pip
python -m pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

## 使用 ce 命令

`ce` 命令是 Context Engine 的命令行工具，提供索引、查询、搜索等功能。

### 基本用法

```powershell
# 在虚拟环境中执行 ce 命令
poetry run ce <command>

# 或激活虚拟环境后直接使用
poetry shell
ce <command>
```

### 索引仓库

```powershell
# 索引指定路径的仓库（替换为你的实际路径）
ce index D:\path\to\your\repository

# 使用当前目录作为仓库根目录
ce index .

# 强制重新索引
ce reindex --force
```

### 查看索引状态

```powershell
# 显示当前索引的统计信息
ce status
```

输出示例：
```
Index Status
============================================
Database: C:\Users\YourName\.context\abc123.db
Repository Root: D:\path\to\your\repository

Statistics
============================================
Files Indexed: 156
Symbols Indexed: 842
- Functions: 620
- Classes: 145
- Methods: 77

Last Updated: 2026-04-02 10:30:00
```

### 查询符号

```powershell
# 查询指定名称的符号
ce query "parseUserToken"

# 查询指定文件中的符号
ce query "handleLogin" --file auth.py
```

### 全文搜索

```powershell
# 搜索包含关键词的符号
ce search "用户认证"

# 搜索函数
ce search "parse" --kind function

# 指定语言搜索
ce search "database" --lang python
```

### 启动文件监听

```powershell
# 监听仓库变化，自动增量更新索引
ce watch D:\path\to\your\repository
```

### 查看 CLI 帮助

```powershell
# 查看所有命令
ce --help

# 查看特定命令的帮助
ce index --help
ce search --help
```

## 配置 MCP 服务

### 1. 创建配置文件

在 Context Engine 项目根目录创建 `.env` 文件：

```powershell
# 复制示例配置文件
copy .env.example .env
```

编辑 `.env` 文件，根据需要修改配置：

```env
# 数据库路径（Windows 路径格式）
CE_DB_PATH=C:\Users\YourName\.context-engine\my-repo.db

# 仓库根目录（Windows 路径格式）
CE_REPO_ROOT=D:\path\to\your\repository

# 日志级别
CE_LOG_LEVEL=INFO

# 启用查询缓存
CE_ENABLE_CACHE=true

# 缓存大小
CE_CACHE_SIZE=1000

# 排除的目录和文件
CE_EXCLUDE_PATTERNS=node_modules,__pycache__,.git,dist,build,venv,.venv

# 并行工作线程数
CE_PARALLEL_WORKERS=4
```

### 2. 测试 MCP 服务

```powershell
# 启动 MCP 服务（测试用）
poetry run python server.py
```

## 集成到 Claude Code

### 方法一：使用 .mcp.json 配置文件

在需要使用 Context Engine 的项目根目录创建 `.mcp.json` 文件：

```json
{
  "mcpServers": {
    "context-engine": {
      "type": "stdio",
      "command": "python",
      "args": ["D:\\path\\to\\context-engine\\server.py"],
      "env": {
        "CE_REPO_ROOT": "${workspaceFolder}",
        "CE_DB_PATH": "${workspaceFolder}\\.ce\\index.db",
        "CE_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

**注意事项**：
- 路径使用双反斜杠 `\\` 或正斜杠 `/`
- `${workspaceFolder}` 会被自动替换为当前项目目录
- `python` 命令需要在系统 PATH 中可用

### 方法二：在 Claude Code 配置中添加 MCP 服务器

在 Claude Code 的设置文件中添加 MCP 服务器配置：

1. 找到 Claude Code 配置文件位置：
   - Windows: `%APPDATA%\Claude\settings.json`

2. 编辑 `settings.json`，添加 MCP 配置：

```json
{
  "mcpServers": {
    "context-engine": {
      "type": "stdio",
      "command": "D:\\path\\to\\context-engine\\.venv\\Scripts\\python.exe",
      "args": ["D:\\path\\to\\context-engine\\server.py"],
      "env": {
        "CE_REPO_ROOT": "${workspaceFolder}",
        "CE_DB_PATH": "${workspaceFolder}\\.ce\\index.db",
        "CE_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

**建议**：使用虚拟环境中的 Python 解释器路径，确保依赖正确加载。

### 方法三：使用 Claude Code Desktop 应用

在 Claude Code Desktop 中：

1. 打开 MCP 设置
2. 添加新的 MCP 服务器
3. 配置如下：
   - 类型：stdio
   - 命令：`D:\path\to\context-engine\.venv\Scripts\python.exe`
   - 参数：`["D:\\path\\to\\context-engine\\server.py"]`
   - 环境变量：
     - `CE_REPO_ROOT`: `${workspaceFolder}`
     - `CE_DB_PATH`: `${workspaceFolder}\.ce\index.db`
     - `CE_LOG_LEVEL`: `WARNING`

### 首次使用注意事项

1. **创建索引**：首次使用时，Claude Code 会尝试访问索引数据库。如果数据库不存在，需要先运行索引：

```powershell
cd D:\path\to\your\project
ce index .
```

2. **路径问题**：确保所有配置中的路径使用正确的分隔符（`\\` 或 `/`）

3. **权限问题**：确保 Python 和 Context Engine 有读写目标目录的权限

## MCP 工具使用

集成成功后，Claude Code 可以使用以下工具：

### get_symbol

获取指定名称的符号完整源码。

**调用示例**：
```
获取 parseUserToken 函数的完整代码
```

### search_code

根据查询搜索符号（全文搜索）。

**调用示例**：
```
搜索包含"用户认证"的代码
搜索 parse 相关的函数
```

### get_callers

获取调用指定符号的所有上层函数。

**调用示例**：
```
查找哪些函数调用了 validateToken
```

### get_callees

获取指定符号调用的所有下层函数。

**调用示例**：
```
查找 handleRequest 调用了哪些函数
```

### get_context_window

获取符号的完整上下文窗口，包含调用者和被调用者。

**调用示例**：
```
获取 processData 函数的上下文
```

### get_file_outline

获取文件内所有符号的大纲。

**调用示例**：
```
获取 src/api/users.py 的文件大纲
```

### list_symbols

根据条件筛选符号列表。

**调用示例**：
```
列出所有 Python 函数
列出 auth.py 中的所有符号
```

## 常见问题

### Q1: 执行 ce 命令提示"找不到命令"

**解决方案**：
- 确保已激活虚拟环境：`poetry shell`
- 或使用完整路径：`poetry run ce <command>`

### Q2: Poetry 安装依赖时速度慢或失败

**解决方案**：

```powershell
# 配置使用国内镜像源
poetry source add --primary tsinghua https://pypi.tuna.tsinghua.edu.cn/simple

# 重新安装依赖
poetry install
```

### Q3: Windows 路径分隔符问题

**解决方案**：
- 在配置文件中使用双反斜杠 `\\` 或正斜杠 `/`
- 路径中的空格需要用引号包裹

### Q4: MCP 服务连接失败

**解决方案**：
1. 检查 Python 路径是否正确
2. 确认虚拟环境已激活或使用完整 Python 路径
3. 查看日志输出确认具体错误

### Q5: 索引大型仓库速度慢

**解决方案**：

```powershell
# 增加并行工作线程数（在 .env 文件中设置）
CE_PARALLEL_WORKERS=8

# 排除不必要的目录
CE_EXCLUDE_PATTERNS=node_modules,__pycache__,.git,dist,build,venv,.venv,tests,docs
```

### Q6: 中文搜索效果不佳

**解决方案**：
Context Engine 使用 SQLite FTS5 进行全文搜索，对中文支持有限。建议：
- 使用英文标识符命名
- 在 docstring 中添加英文关键词
- 或者使用 search_code 配合 file 参数缩小范围

## 性能优化建议

1. **启用查询缓存**：在 `.env` 中设置 `CE_ENABLE_CACHE=true`
2. **调整并行度**：根据 CPU 核心数设置 `CE_PARALLEL_WORKERS`
3. **排除不必要的文件**：合理配置 `CE_EXCLUDE_PATTERNS`
4. **限制文件大小**：使用 `CE_MAX_FILE_SIZE` 跳过过大文件

## 卸载

如需完全卸载 Context Engine：

```powershell
# 删除虚拟环境
poetry env remove python3.11

# 或手动删除项目目录
rm -r -force context-engine

# 删除数据库文件（根据 .env 配置中的路径）
rm C:\Users\YourName\.context\*.db
```

## 更多信息

- 项目 GitHub: https://github.com/your-org/context-engine
- MCP 协议文档: https://modelcontextprotocol.io/
- Claude Code 文档: https://docs.anthropic.com/claude/claude-code

---

**最后更新**: 2026-04-02

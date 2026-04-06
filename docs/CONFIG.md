# Context Engine 配置指南

本文档详细说明 Context Engine 的所有配置选项。

## 环境变量配置

Context Engine 支持通过环境变量进行配置。可以在 `.env` 文件中设置，或直接在 shell 中导出。

### 数据库配置

#### CE_DB_PATH

SQLite 数据库文件路径。

- **类型**: 字符串
- **默认值**: `~/.context-engine/{repo_hash}.db`
- **示例**:
  ```bash
  CE_DB_PATH=~/.context-engine/my-repo.db
  CE_DB_PATH=${workspaceFolder}/.ce/index.db
  ```

**说明**:
- 如果未指定，系统会根据仓库路径生成哈希作为文件名
- 目录路径不存在时会自动创建

#### CE_REPO_ROOT

索引的仓库根目录。

- **类型**: 字符串
- **默认值**: 当前工作目录
- **示例**:
  ```bash
  CE_REPO_ROOT=/path/to/your/repo
  CE_REPO_ROOT=${workspaceFolder}
  ```

### 排除规则配置

#### CE_EXCLUDE_PATTERNS

排除目录/文件的模式列表（逗号分隔）。

- **类型**: 字符串（逗号分隔）
- **默认值**: `node_modules,__pycache__,.git,dist,build`
- **示例**:
  ```bash
  CE_EXCLUDE_PATTERNS=node_modules,__pycache__,.git,dist,build,venv,.venv
  ```

**说明**:
- 支持 Git 风格的通配符模式
- 自动加载项目根目录下的 `.gitignore` 文件
- 排除规则会同时应用于文件发现和文件监听

#### CE_MAX_FILE_SIZE

要索引的最大文件大小（字节）。

- **类型**: 整数
- **默认值**: `500000` (约 500KB)
- **示例**:
  ```bash
  CE_MAX_FILE_SIZE=1000000  # 1MB
  CE_MAX_FILE_SIZE=500000     # 500KB (默认)
  ```

**说明**:
- 超过此大小的文件将被跳过，不进行索引
- 用于防止索引大生成文件（如 minified JS）

### 性能配置

#### CE_PARALLEL_WORKERS

并行解析的线程数。

- **类型**: 整数
- **默认值**: `4`
- **示例**:
  ```bash
  CE_PARALLEL_WORKERS=8
  ```

**说明**:
- 根据 CPU 核心数调整可获得最佳性能
- 建议设置为 CPU 核心数的 1-2 倍

#### CE_WATCHER_DEBOUNCE

文件变更防抖时间（秒）。

- **类型**: 浮点数
- **默认值**: `0.5`
- **示例**:
  ```bash
  CE_WATCHER_DEBOUNCE=0.3  # 300ms
  CE_WATCHER_DEBOUNCE=1.0  # 1秒
  ```

**说明**:
- 用于合并短时间内的多次文件变更
- 过短的防抖时间可能导致频繁的增量更新

#### CE_ENABLE_CACHE

是否启用查询缓存。

- **类型**: 布尔值
- **默认值**: `true`
- **示例**:
  ```bash
  CE_ENABLE_CACHE=true
  CE_ENABLE_CACHE=false
  ```

**说明**:
- 缓存热点查询结果可显著提升性能
- 禁用缓存可减少内存占用

#### CE_CACHE_SIZE

缓存最大条目数。

- **类型**: 整数
- **默认值**: `1000`
- **示例**:
  ```bash
  CE_CACHE_SIZE=2000
  ```

**说明**:
- 使用 LRU (Least Recently Used) 淘汰策略
- 增大缓存可提升命中率，但增加内存占用

### 日志配置

#### CE_LOG_LEVEL

日志级别。

- **类型**: 字符串
- **默认值**: `INFO`
- **可选值**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **示例**:
  ```bash
  CE_LOG_LEVEL=DEBUG
  CE_LOG_LEVEL=INFO
  CE_LOG_LEVEL=WARNING
  CE_LOG_LEVEL=ERROR
  ```

**说明**:
- `DEBUG`: 详细的调试信息
- `INFO`: 常规信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 仅错误信息
- `CRITICAL`: 严重错误

#### CE_JSON_LOGS

是否使用 JSON 格式输出日志。

- **类型**: 布尔值
- **默认值**: `false`
- **示例**:
  ```bash
  CE_JSON_LOGS=true
  CE_JSON_LOGS=false
  ```

**说明**:
- JSON 格式更适合日志聚合系统（如 ELK）
- 文本格式更适合人类阅读

#### CE_LOG_FILE

日志文件路径（可选）。

- **类型**: 字符串
- **默认值**: `None` (仅输出到控制台)
- **示例**:
  ```bash
  CE_LOG_FILE=/var/log/context-engine.log
  CE_LOG_FILE=./context-engine.log
  ```

**说明**:
- 设置后会同时输出到控制台和文件
- 文件不存在时会自动创建

## .env 文件配置

创建项目根目录下的 `.env` 文件：

```env
# 数据库配置
CE_DB_PATH=~/.context-engine/my-repo.db
CE_REPO_ROOT=/path/to/your/repo

# 排除规则
CE_EXCLUDE_PATTERNS=node_modules,__pycache__,.git,dist,build,venv,.venv
CE_MAX_FILE_SIZE=1000000

# 性能配置
CE_PARALLEL_WORKERS=8
CE_WATCHER_DEBOUNCE=0.5
CE_ENABLE_CACHE=true
CE_CACHE_SIZE=2000

# 日志配置
CE_LOG_LEVEL=INFO
CE_JSON_LOGS=false
CE_LOG_FILE=./context-engine.log
```

## .mcp.json 配置

在项目根目录创建 `.mcp.json` 以集成到 Claude Code：

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
        "CE_LOG_LEVEL": "WARNING",
        "CE_ENABLE_CACHE": "true"
      }
    }
  }
}
```

**说明**:
- `${workspaceFolder}` 是 Claude Code 提供的环境变量
- 所有环境变量都可以在此配置
- 注意：布尔值在 JSON 中需要使用字符串 `"true"` / `"false"`

## 配置优先级

配置优先级从高到低：

1. 环境变量（shell 中导出）
2. `.env` 文件
3. 默认值

**示例**:

```bash
# .env 文件中设置
CE_LOG_LEVEL=INFO

# shell 中导出会覆盖 .env
export CE_LOG_LEVEL=DEBUG
```

## 性能调优建议

### 开发环境

```env
CE_PARALLEL_WORKERS=4
CE_WATCHER_DEBOUNCE=0.5
CE_ENABLE_CACHE=true
CE_CACHE_SIZE=500
CE_LOG_LEVEL=INFO
```

### 生产环境

```env
CE_PARALLEL_WORKERS=8
CE_WATCHER_DEBOUNCE=1.0
CE_ENABLE_CACHE=true
CE_CACHE_SIZE=2000
CE_LOG_LEVEL=WARNING
CE_JSON_LOGS=true
```

### 大型仓库（10万+ 行）

```env
CE_PARALLEL_WORKERS=16
CE_MAX_FILE_SIZE=2000000
CE_ENABLE_CACHE=true
CE_CACHE_SIZE=5000
CE_LOG_LEVEL=WARNING
```

### 调试模式

```env
CE_LOG_LEVEL=DEBUG
CE_JSON_LOGS=false
CE_LOG_FILE=./debug.log
CE_ENABLE_CACHE=false  # 禁用缓存以便重复测试
```

## 配置验证

使用 `ce status` 命令检查当前配置：

```bash
ce status
```

输出示例：

```
Index Status:
  Files: 150
  Symbols: 2345
  Call Edges: 5678

Cache Statistics:
  Size: 125 / 1000
  Hits: 8923
  Misses: 456
  Hit Rate: 95.13%
```

## 配置文件位置

配置文件查找路径（按优先级）：

1. 当前工作目录下的 `.env`
2. 项目根目录下的 `.env`

**注意**: 配置文件在程序启动时加载，修改后需要重启程序。

## 常见问题

### Q: 如何查看当前使用的配置？

A: 查看日志启动信息，或设置 `CE_LOG_LEVEL=DEBUG` 查看详细配置。

### Q: 配置更改后如何生效？

A: 重启 MCP Server 或 CLI 程序。

### Q: 数据库可以跨项目共享吗？

A: 不建议。每个仓库应有独立的数据库文件以避免冲突。

### Q: 缓存占用多少内存？

A: 每个缓存条目约占用 1-10KB（取决于符号大小）。默认 1000 条目约占用 5-50MB。

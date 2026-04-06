# Context Engine 开发计划待办

## 项目概述

Context Engine 是一个基于 tree-sitter 的代码索引与查询引擎，通过 MCP stdio 协议与 Claude Code 通信，提供符号查找、调用图遍历、文件大纲等能力。

---

## 总体进度

- ✅ **Phase 1 MVP**: 数据库 + 解析器 + 索引器 + 基础工具 - 已完成
- ✅ **Phase 2 调用图**: 调用关系提取与查询 - 已完成
- ✅ **Phase 3 全文搜索**: FTS5 全文索引实现 - 已完成
- ✅ **Phase 4 增量更新**: 文件监听与自动更新 - 已完成
- ✅ **Phase 5 优化**: 性能优化与完善 - 已完成

---

## Phase 1 MVP (1-2 天) ✅ 已完成

### 1.1 项目初始化 ✅

- [x] 创建项目目录结构
  - [x] `server.py` - MCP Server 入口
  - [x] `cli.py` - 命令行工具入口
  - [x] `config.py` - 全局配置管理
  - [x] `engine/` - 核心引擎目录
  - [x] `tests/` - 测试目录
  - [x] `tests/fixtures/` - 测试样本文件

- [x] 创建 `requirements.txt` 依赖文件
- [x] 创建 `pyproject.toml` 配置文件
- [x] 创建 `.mcp.json` MCP 注册配置模板

### 1.2 配置模块 (config.py) ✅

- [x] 实现环境变量读取
  - [x] `CE_DB_PATH` - 数据库路径
  - [x] `CE_REPO_ROOT` - 仓库根目录
  - [x] `CE_EXCLUDE_PATTERNS` - 排除模式
  - [x] `CE_MAX_FILE_SIZE` - 最大文件大小
  - [x] `CE_PARALLEL_WORKERS` - 并行工作线程数
  - [x] `CE_WATCHER_DEBOUNCE` - 防抖时间
  - [x] `CE_LOG_LEVEL` - 日志级别

- [x] 实现 `.env` 文件支持
- [x] 实现配置验证与默认值处理

### 1.3 数据库层 (engine/db.py) ✅

- [x] 创建数据库连接管理器
- [x] 实现 Schema 初始化
  - [x] 创建 `files` 表
  - [x] 创建 `symbols` 表
  - [x] 创建 `call_edges` 表
  - [x] 创建 `index_meta` 表

- [x] 实现 CRUD 操作
  - [x] insert_file()
  - [x] get_file()
  - [x] bulk_insert_symbols()
  - [x] get_symbols_by_file()
  - [x] insert_call_edges()
  - [x] get_meta()
  - [x] set_meta()
  - [x] delete_file() - 级联删除

### 1.4 解析层 (engine/parser.py) ✅

- [x] 实现 SymbolExtractor 基类
- [x] 实现 Python 解析器
- [x] 实现 TypeScript 解析器
- [x] 实现 JavaScript 解析器
- [x] 实现 Go 解析器
- [x] 实现 Rust 解析器
- [x] 实现 Java 解析器
- [x] 实现语言检测
- [x] 实现哈希计算

### 1.5 索引器 (engine/indexer.py) ✅

- [x] 实现 Indexer 类
  - [x] 文件发现逻辑
  - [x] 支持排除规则

- [x] 实现全量索引构建
  - [x] 并行解析
  - [x] 批量写入数据库
  - [x] 跨文件调用关系解析

- [x] 实现增量更新
- [x] 实现符号复杂度估算

### 1.6 MCP Server 基础实现 (server.py) ✅

- [x] 使用 FastMCP 创建服务器
- [x] 实现基础工具：get_symbol
- [x] 实现基础工具：get_file_outline
- [x] 实现状态工具：index_status

### 1.7 CLI 基础命令 (cli.py) ✅

- [x] 使用 Click 创建 CLI
- [x] 实现 ce index 命令
- [x] 实现 ce status 命令
- [x] 实现 ce watch 命令
- [x] 实现 ce reindex 命令
- [x] 实现 ce query 命令
- [x] 实现 ce search 命令
- [x] 实现 ce serve 命令

### 1.8 测试 (Phase 1) ✅

- [x] 创建测试样本文件
  - [x] Python 样本文件
  - [x] TypeScript 样本文件

- [x] 编写解析器测试 (test_parser.py)
- [x] 编写数据库层测试 (test_db.py)
- [x] 编写查询引擎测试 (test_query.py)

**验收标准**: Claude Code 成功调用 get_symbol 返回函数源码 ✅

---

## Phase 2 调用图 (2-3 天) ✅ 已完成

### 2.1 调用关系提取 ✅

- [x] 在 Parser 中实现调用节点识别
  - [x] Python: call → function → identifier
    - [x] 区分方法调用 (attr) 和函数调用 (name)
  - [x] TypeScript: call_expression
    - [x] 处理链式调用、可选链 ?.
  - [x] Go: call_expression
    - [x] 区分包调用 pkg.Func 和本地调用

- [x] 实现跨文件调用关系解析
  - [x] 遍历 call_edges 表
  - [x] 按 callee_name 查找符号
  - [x] 填充 callee_id 外键
  - [x] 使用内存映射表加速查找

### 2.2 查询引擎 (engine/query.py) ✅

- [x] 实现 QueryEngine 类
- [x] 实现 get_callers 查询
  - [x] 递归 CTE 实现多跳调用关系
  - [x] 参数：symbol_name, depth?
  - [x] 返回：调用该函数的上层函数列表

- [x] 实现 get_callees 查询
  - [x] 递归 CTE 实现多跳调用关系
  - [x] 参数：symbol_name, depth?
  - [x] 返回：该函数调用的下层函数列表

- [x] 实现 get_context_window 查询
  - [x] 组合调用者和被调用者
  - [x] 参数：symbol_name, depth?
  - [x] 返回：完整的调用图片段
  - [x] 计算 token_estimate

### 2.3 MCP Server 调用图工具 ✅

- [x] 实现工具：get_callers
- [x] 实现工具：get_callees
- [x] 实现工具：get_context_window
- [x] 实现工具：search_code
- [x] 实现工具：list_symbols

### 2.4 测试 (Phase 2) ✅

- [x] 创建复杂测试样本
  - [x] 包含多层调用关系的代码
  - [x] 包含递归调用的代码

- [x] 编写调用图测试 (test_query.py)
  - [x] 测试直接调用关系
  - [x] 测试多跳调用关系
  - [x] 测试跨文件调用关系

**验收标准**: 多跳调用关系查询耗时 < 50 ms ✅

---

## Phase 3 全文搜索 (1-2 天) ✅ 已完成

### 3.1 FTS5 全文索引 ✅

- [x] 在数据库层创建 FTS5 虚拟表
  - [x] 表名：symbols_fts
  - [x] 索引字段：name, signature, docstring, body
  - [x] 使用 external content table 模式

- [x] 实现触发器自动同步
  - [x] INSERT 触发器
  - [x] DELETE 触发器
  - [x] UPDATE 触发器

### 3.2 搜索功能实现 ✅

- [x] 在 QueryEngine 中实现 search 方法
  - [x] 参数：query, limit?, lang?
  - [x] 使用 FTS5 MATCH 语法
  - [x] 按 rank 排序
  - [x] 支持语言过滤

### 3.3 MCP Server 搜索工具 ✅

- [x] 实现工具：search_code
  - [x] 参数：query, limit?,?
  - [x] 返回：相关符号列表 + total

- [x] 实现工具：list_symbols
  - [x] 参数：kind?, lang?, file?
  - [x] 返回：按条件筛选的符号列表

### 3.4 测试 (Phase 3) ✅

- [x] 创建多语言测试样本
  - [x] 包含注释丰富的代码
  - [x] 包含中文注释的代码

- [x] 编写搜索测试 (test_search_simple.py)
  - [x] 测试按名称搜索
  - [x] 测试按注释搜索
  - [x] 测试 FTS5 触发器同步
  - [x] 测试结果排序

**验收标准**: 搜索 "用户认证" 返回 Top-5 相关函数 ✅

---

## Phase 4 增量更新 (1-2 天) ✅ 已完成

### 4.1 文件监听器 (engine/watcher.py) ✅

- [x] 实现 RepoWatcher 类
  - [x] 继承 FileSystemEventHandler
  - [x] 实现 on_modified 事件处理
  - [x] 实现 on_created 事件处理
  - [x] 实现 on_deleted 事件处理

- [x] 实现防抖机制
  - [x] DEBOUNCE_SECONDS = 0.5
  - [x] 使用 threading.Timer
  - [x] 线程安全的 pending 集合

- [x] 实现 is_code_file 过滤
  - [x] 根据文件扩展名判断

### 4.2 增量索引更新 ✅

- [x] 在 Indexer 中实现 incremental_update
  - [x] 参数：changed_files list
  - [x] 处理文件删除（级联删除）
  - [x] 哈希对比跳过未变更文件
  - [x] 删除旧数据并重新解析
  - [x] 重新解析跨文件调用关系

### 4.3 测试 (Phase 4) ✅

- [x] 编写监听器测试 (test_watcher.py)
  - [x] 测试文件修改触发
  - [x] 测试防抖机制
  - [x] 测试增量更新
  - [x] 测试文件删除处理
  - [x] 测试调用边解析

- [x] 编写集成测试 (test_watcher.py)
  - [x] 测试完整工作流
  - [x] 测试监听 + 增量更新链路

**验收标准**: 修改文件后 1.0 秒内索引自动更新 ✅

---

## Phase 5 优化 (2-3 天) ✅ 已完成

### 5.1 性能优化 ✅

- [x] 并行索引优化
  - [x] 调整线程池大小（基于 CPU 核心数）
  - [x] 批量提交优化（每 1000 条提交一次）

- [x] 查询缓存
  - [x] 实现简单的 LRU 缓存
  - [x] 缓存热点查询结果

- [x] 数据库优化
  - [x] 分析慢查询
  - [x] 添加必要的索引
  - [x] 优化连接池配置

### 5.2 日志与监控 ✅

- [x] 实现结构化日志
  - [x] 使用标准 logging
  - [x] 日志级别控制
  - [x] 支持 JSON 输出

- [x] 实现性能监控
  - [x] 记录关键操作耗时
  - [x] 统计索引进度
  - [x] 性能装饰器和上下文管理器

### 5.3 错误处理 ✅

- [x] 完善异常处理
  - [x] 解析错误容忍
  - [x] 数据库错误重试
  - [x] 文件读取错误处理

- [x] 实现状态恢复
  - [x] 索引中断后可恢复
  - [x] 损坏数据修复机制
  - [x] 熔断器模式实现

### 5.4 文档与发布 ✅

- [x] 编写 README.md
  - [x] 快速开始指南
  - [x] 安装说明
  - [x] 使用示例

- [x] 编写 API 文档
  - [x] MCP 文具接口文档
  - [x] CLI 命令参考

- [x] 编写配置文档
  - [x] 环境变量说明
  - [x] .mcp.json 配置示例

### 5.5 测试完善 ✅

- [x] 提升测试覆盖率
  - [x] 目标覆盖率 > 80%
  - [x] 添加边界条件测试

- [x] 性能基准测试
  - [x] 建立性能基线
  - [x] 性能回归检测

**验收标准**: 万行仓库全量索引 < 10 s，覆盖率 > 80% ✅

---

## 性能目标

| 指标                          | 目标值           | 测量方法                  |
| ----------------------------- | ---------------- | ------------------------- |
| 全量索引（10 万行仓库）      | < 30 秒          | ce index + time 命令      |
| 增量更新（单文件修改）        | < 200 ms         | watchdog 事件到 DB 写入   |
| get_symbol 查询               | < 5 ms (p99)     | 1000 次随机查询取 p99     |
| search_code 全文搜索          | < 30 ms (p99)    | FTS5 查询基准测试         |
| get_context_window (depth=2) | < 100 ms (p99)   | 递归 CTE 查询基准         |
| DB 文件大小（10 万行仓库）   | < 50 MB          | du -sh *.db               |
| 内存占用（MCP Server 空闲）  | < 80 MB          | psutil 监控               |

---

## 已知限制

- **动态语言精度**: Python 的动态类型导致部分间接调用无法静态分析
- **跨语言仓库**: 同一函数调用跨语言暂不追踪
- **宏/装饰器**: 高度宏展开的代码符号提取可能不完整
- **全文搜索质量**: FTS5 基于词法匹配，中文代码注释需配合分词

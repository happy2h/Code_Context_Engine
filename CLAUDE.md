# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Context Engine is a code indexing and query engine that uses tree-sitter for parsing and SQLite (with FTS5) for storage. It communicates with Claude Code via the MCP stdio protocol, providing symbol lookup, call graph traversal, and full-text search capabilities.

## Core Architecture

### Engine Components (`engine/`)

- **`db.py`**: Database layer managing SQLite operations. Uses WAL mode for performance and FTS5 for full-text search. Defines `FileRecord` and `SymbolRecord` dataclasses.

- **`indexer.py`**: Builds full and incremental indexes. Uses `ThreadPoolExecutor` for parallel parsing (configurable via `CE_PARALLEL_WORKERS`). Filters files using `pathspec` based on `CE_EXCLUDE_PATTERNS`.

- **`parser.py`**: Symbol extraction using tree-sitter parsers. Supports Python, TypeScript, JavaScript, Go, Rust, Java. Extracts functions, classes, methods with signatures, docstrings, and source code.

- **`query.py`**: Query engine with LRU cache implementation. Provides symbol lookup, call graph queries (callers/callees), and context window generation.

- **`watcher.py`**: File system watcher using watchdog for incremental updates with debounce (`CE_WATCHER_DEBOUNCE`).

- **`logger.py`**: Structured logging system supporting plain text and JSON output.

### Entry Points

- **`cli.py`**: CLI tool using Click. Commands: `index`, `watch`, `status`, `query`, `search`, `reindex`, `serve`.

- **`server.py`**: MCP server using fastmcp. Exposes tools: `get_symbol`, `get_file_outline`, `index_status`, `get_callers`, `get_callees`, `get_context_window`, `search_code`, `list_symbols`.

- **`config.py`**: Configuration management via environment variables and `.env` files.

## Common Development Commands

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=engine --cov-report=html

# Run specific test file
pytest tests/test_parser.py

# Run performance benchmarks
pytest tests/test_benchmark.py
```

### Code Style

```bash
# Format code
black engine/ server.py cli.py

# Lint code
flake8 engine/ server.py cli.py
```

### CLI Operations

```bash
# Index a repository
ce index /path/to/repo

# Force rebuild index
ce reindex --force

# Watch for file changes
ce watch /path/to/repo

# Show index status
ce status

# Query a symbol
ce query "symbol_name"

# Full-text search
ce search "query text"

# Start MCP server
ce serve
```

## Configuration

Configuration is managed via environment variables or `.env` file in the project root:

| Variable | Default | Description |
|----------|---------|-------------|
| `CE_DB_PATH` | `~/.context/{repo_hash}.db` | SQLite database path |
| `CE_REPO_ROOT` | Current directory | Repository root directory |
| `CE_EXCLUDE_PATTERNS` | `node_modules,__pycache__,.git,dist,build` | File/directory exclusion patterns |
| `CE_MAX_FILE_SIZE` | `500000` | Maximum file size in bytes |
| `CE_PARALLEL_WORKERS` | `4` | Number of parallel parsing threads |
| `CE_WATCHER_DEBOUNCE` | `0.5` | File change debounce time in seconds |
| `CE_LOG_LEVEL` | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `CE_ENABLE_CACHE` | `true` | Enable query cache |
| `CE_CACHE_SIZE` | `1000` | Maximum cache entries |
| `CE_JSON_LOGS` | `false` | Output logs in JSON format |
| `CE_LOG_FILE` | `None` | Optional log file path |

## MCP Integration

The project provides an MCP server that integrates with Claude Code. The server is configured via `.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "context-engine": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/context-engine/server.py"],
      "env": {
        "CE_REPO_ROOT": "${workspaceFolder}",
        "CE_DB_PATH": "${workspaceFolder}/.ce/index.db"
      }
    }
  }
}
```

## Key Implementation Notes

- **Database Schema**: SQLite with FTS5 virtual table for full-text search on symbol names, signatures, and docstrings.
- **Call Graph**: Stored as `call_edges` table with `caller_id` and `callee_id` references to symbols.
- **Caching**: LRU cache in `query.py` keyed by query parameters hash (SHA256).
- **Incremental Updates**: File content hash comparison detects changes; only modified files are re-indexed.
- **Performance**: WAL mode for SQLite, parallel indexing, query caching, and lazy symbol body loading in outlines.

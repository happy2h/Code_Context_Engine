"""
Context Engine MCP Server

通过 MCP stdio 协议与 Claude Code 通信，
提供代码索引与查询能力。
"""

from fastmcp import FastMCP
import os
import sys

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.query import QueryEngine
from engine.logger import Logger
from config import Config

# 初始化日志系统
Logger.setup(
    level=Config.get_log_level(),
    json_output=Config.get_json_logs(),
    output_file=Config.get_log_file()
)

logger = Logger()

# 初始化 MCP Server
mcp = FastMCP(name="context-engine", version="1.0.0")

# 初始化查询引擎
db_path = Config.get_db_path()
logger.info(f"Initializing QueryEngine with db_path: {db_path}")
engine = QueryEngine(
    db_path=db_path,
    enable_cache=Config.get_enable_cache(),
    cache_size=Config.get_cache_size()
)


@mcp.tool(description="Get complete source code of a function or class by name")
def get_symbol(
    name: str,
    file: str | None = None,
    kind: str | None = None
) -> dict:
    """获取指定名称的符号（函数/类/方法）的完整源码

    Args:
        name: 符号名称，支持通配符（如 parse*）
        file: 可选，限定文件范围
        kind: 可选，符号类型（function/method/class）

    Returns:
        包含符号完整信息的字典
    """
    result = engine.get_symbol(name, file, kind)
    if not result:
        return {"found": False, "message": f"Symbol '{name}' not found"}
    return {"found": True, "symbol": result.to_dict()}


@mcp.tool(description="Get file outline with all symbols (without function bodies)")
def get_file_outline(file_path: str) -> dict:
    """获取文件内所有符号的大纲（不含函数体）

    Args:
        file_path: 文件路径

    Returns:
        包含文件符号大纲的字典
    """
    outline = engine.get_file_outline(file_path)
    return {
        "file": file_path,
        "symbols": [s.to_summary_dict() for s in outline]
    }


@mcp.tool(description="Get current index status and statistics")
def index_status() -> dict:
    """获取当前索引状态和统计信息

    Returns:
        包含索引统计信息的字典
    """
    return engine.get_index_status()


@mcp.tool(description="Get all callers of a symbol (functions that call this function)")
def get_callers(symbol_name: str, depth: int = 1) -> dict:
    """获取调用指定符号的所有上层函数（调用者）

    Args:
        symbol_name: 符号名称
        depth: 查询深度，默认 1（仅直接调用者），2 包含间接调用者

    Returns:
        包含调用者列表的字典，每个调用者包含 depth 和 symbol 信息
    """
    if depth < 1:
        depth = 1
    if depth > 10:
        depth = 10  # 限制最大深度

    callers = engine.get_callers(symbol_name, depth)

    return {
        "symbol_name": symbol_name,
        "depth": depth,
        "total": len(callers),
        "callers": callers
    }


@mcp.tool(description="Get all callees of a symbol (functions called by this function)")
def get_callees(symbol_name: str, depth: int = 1) -> dict:
    """获取指定符号调用的所有下层函数（被调用函数）

    Args:
        symbol_name: 符号名称
        depth: 查询深度，默认 1（仅直接调用），2 包含间接调用

    Returns:
        包含被调用函数列表的字典，每个被调用函数包含 depth 和 symbol 信息
    """
    if depth < 1:
        depth = 1
    if depth > 10:
        depth = 10  # 限制最大深度

    callees = engine.get_callees(symbol_name, depth)

    return {
        "symbol_name": symbol_name,
        "depth": depth,
        "total": len(callees),
        "callees": callees
    }


@mcp.tool(description="Get context window around a symbol including callers and callees")
def get_context_window(symbol_name: str, depth: int = 1) -> dict:
    """获取符号的完整上下文窗口，包含调用者和被调用者

    Args:
        symbol_name: 符号名称
        depth: 查询深度，默认 1

    Returns:
        包含中心符号、调用者、被调用者、总行数和 token 估算的字典
    """
    if depth < 1:
        depth = 1
    if depth > 10:
        depth = 10  # 限制最大深度

    return engine.get_context_window(symbol_name, depth)


@mcp.tool(description="Search symbols by natural language query (full-text search)")
def search_code(query: str, limit: int = 10, lang: str | None = None) -> dict:
    """根据查询搜索符号（全文搜索）

    Args:
        query: 搜索查询字符串
        limit: 返回结果数量，默认 10
        lang: 可选，限定语言类型

    Returns:
        包含搜索结果列表和总数的字典
    """
    results = engine.search(query, limit=limit, lang=lang)
    return {
        "query": query,
        "total": len(results),
        "results": [r.to_summary_dict() for r in results]
    }


@mcp.tool(description="List symbols by filtering conditions")
def list_symbols(kind: str | None = None, lang: str | None = None, file: str | None = None) -> dict:
    """根据条件筛选符号列表

    Args:
        kind: 可选，符号类型（function/method/class）
        lang: 可选，，语言类型
        file: 可选，文件路径

    Returns:
        包含符号列表的字典
    """
    results = engine.list_symbols(kind=kind, lang=lang, file=file)
    return {
        "total": len(results),
        "symbols": [r.to_summary_dict() for r in results]
    }


if __name__ == "__main__":
    mcp.run()

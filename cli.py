"""
Context Engine CLI

命令行工具用于索引构建、文件监听和查询。
"""

import os
import sys
import click

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.indexer import Indexer
from engine.watcher import RepoWatcher
from engine.db import Database
from config import Config


@click.group()
@click.version_option("1.0.0")
def cli():
    """Context Engine - 代码索引与查询引擎"""
    pass


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="强制重建索引")
def index(repo_path, force):
    """对指定仓库执行全量索引"""
    repo_path = os.path.abspath(repo_path)
    db_path = Config.get_db_path(repo_path)

    if force:
        # 删除现有数据库
        if os.path.exists(db_path):
            os.remove(db_path)
            click.echo(f"Removed existing database: {db_path}")

    click.echo(f"Indexing repository: {repo_path}")
    click.echo(f"Database: {db_path}")

    indexer = Indexer(repo_path, db_path)
    result = indexer.full_index()

    click.echo(f"Index completed:")
    click.echo(f"  Files processed: {result.files_processed}")
    click.echo(f"  Symbols extracted: {result.symbols_count}")
    click.echo(f"  Errors: {result.errors}")
    click.echo(f"  Duration: {result.duration:.2f}s")


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
def watch(repo_path):
    """启动文件监听，自动增量更新"""
    repo_path = os.path.abspath(repo_path)
    db_path = Config.get_db_path(repo_path)

    click.echo(f"Watching repository: {repo_path}")
    click.echo(f"Database: {db_path}")
    click.echo("Press Ctrl+C to stop...")

    indexer = Indexer(repo_path, db_path)
    watcher = RepoWatcher(indexer, repo_path)

    try:
        watcher.start()
    except KeyboardInterrupt:
        click.echo("\nStopped watching")


@cli.command()
@click.option("--db-path", type=click.Path(), help="指定数据库路径")
def status(db_path):
    """显示当前索引状态和统计信息"""
    if not db_path:
        db_path = os.path.expanduser("~/.context-engine/default.db")

    if not os.path.exists(db_path):
        click.echo(f"Database not found: {db_path}")
        return

    db = Database(db_path)
    status = db.get_index_status()

    click.echo("Index Status:")
    for key, value in status.items():
        click.echo(f"  {key}: {value}")


@cli.command()
@click.argument("name")
@click.option("--file", help="限定文件范围")
@click.option("--kind", help="符号类型")
def query(name, file, kind):
    """命令行直接查询符号（调试用）"""
    db_path = os.path.expanduser("~/.context-engine/default.db")

    if not os.path.exists(db_path):
        click.echo(f"Database not found: {db_path}")
        return

    from engine.query import QueryEngine
    engine = QueryEngine(db_path)

    result = engine.get_symbol(name, file, kind)
    if not result:
        click.echo(f"Symbol '{name}' not found")
        return

    click.echo(f"Found symbol: {result.name}")
    click.echo(f"  Kind: {result.kind}")
    click.echo(f"  File: {result.file_path}")
    click.echo(f"  Lines: {result.line_start} - {result.line_end}")
    click.echo(f"  Signature: {result.signature or 'N/A'}")
    if result.docstring:
        click.echo(f"  Docstring: {result.docstring[:100]}...")


@cli.command()
@click.argument("query")
@click.option("--limit", default=10, help="返回结果数量")
@click.option("--lang", help="限定语言")
def search(query, limit, lang):
    """全文搜索符号"""
    db_path = os.path.expanduser("~/.context-engine/default.db")

    if not os.path.exists(db_path):
        click.echo(f"Database not found: {db_path}")
        return

    from engine.query import QueryEngine
    engine = QueryEngine(db_path)

    results = engine.search(query, limit=limit, lang=lang)

    click.echo(f"Found {len(results)} results:")
    for r in results:
        click.echo(f"  - {r.name} ({r.kind}) in {r.file_path}")
        if r.docstring:
            click.echo(f"    {r.docstring[:80]}...")


@cli.command()
@click.option("--force", is_flag=True, help="强制重建全量索引")
@click.option("--repo-path", type=click.Path(exists=True), help="仓库路径")
def reindex(force, repo_path):
    """重建全量索引"""
    if not repo_path:
        repo_path = os.getcwd()

    index(repo_path, force)


@cli.command()
@click.option("--db", type=click.Path(), help="指定数据库路径")
def serve(db):
    """以 MCP Server 模式启动"""
    if db:
        os.environ["CE_DB_PATH"] = db

    click.echo("Starting Context Engine MCP Server...")
    from server import mcp
    mcp.run()


if __name__ == "__main__":
    cli()

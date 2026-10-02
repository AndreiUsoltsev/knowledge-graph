"""Console entry point; data commands return UTF-8 JSON."""
import argparse
import json
import sys

from .core import Graph, GraphError, LANGUAGES, RELATIONS, inspect_database
from .database import install_database, resolve_database
from . import __version__
from .agents import manage_agents


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise GraphError("USAGE_ERROR", message)


def nonnegative(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer") from None
    if number < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return number


def positive(value):
    number = nonnegative(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def parser():
    result = Parser(prog="knowledge-graph", description="Documentation knowledge graph. Data commands return JSON.")
    result.add_argument("--db", help="Exact database directory; otherwise discover the nearest .knowledge-graph")
    result.add_argument("--lang", choices=LANGUAGES, default="en", help="Document language (default: en)")
    result.add_argument("--version", action="version", version="%(prog)s " + __version__)
    commands = result.add_subparsers(dest="command", required=True, parser_class=Parser)
    install = commands.add_parser("install", help="Initialize DIR/.knowledge-graph from packaged knowledge")
    install.add_argument("directory", nargs="?", help="Project directory (default: current directory)")
    agents = commands.add_parser("agents", help="Install, inspect or remove agent rules and skills")
    operations = agents.add_subparsers(dest="agent_operation", required=True, parser_class=Parser)
    for operation in ("install", "uninstall", "doctor"):
        command = operations.add_parser(operation, help=operation.capitalize() + " agent integration")
        command.add_argument("--dir", help="Project directory (default: current directory)")
        command.add_argument("--scope", choices=("project", "user"), default="project")
        command.add_argument("--target", default="auto", help="auto, all, or comma-separated codex,cursor,claude,opencode")
        if operation != "doctor":
            command.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    commands.add_parser("entry", help="List starting nodes")
    search = commands.add_parser("search", help="Search metadata and document text")
    search.add_argument("text")
    search.add_argument("--limit", type=positive, default=20)
    node = commands.add_parser("node", help="Read one node and its links")
    node.add_argument("id")
    neighbors = commands.add_parser("neighbors", help="List neighboring nodes without their bodies")
    neighbors.add_argument("id")
    neighbors.add_argument("--direction", choices=("in", "out", "both"), default="both")
    neighbors.add_argument("--relation", choices=RELATIONS)
    walk = commands.add_parser("walk", help="Bounded breadth-first traversal")
    walk.add_argument("id")
    walk.add_argument("--depth", type=nonnegative, default=1)
    walk.add_argument("--max-nodes", type=positive, default=50)
    walk.add_argument("--direction", choices=("in", "out", "both"), default="both")
    walk.add_argument("--relation", choices=RELATIONS)
    path = commands.add_parser("path", help="Find a shortest path")
    path.add_argument("source")
    path.add_argument("target")
    path.add_argument("--direction", choices=("in", "out", "both"), default="both")
    commands.add_parser("validate", help="Validate the entire database")
    serve = commands.add_parser("gui", aliases=["serve"], help="Start the local browser viewer; Ctrl+C stops it")
    serve.add_argument("--port", type=positive, default=8765)
    serve.add_argument("--no-browser", action="store_true")
    return result


def output(value, stream=None):
    print(json.dumps(value, ensure_ascii=False, indent=2), file=stream or sys.stdout)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        args = parser().parse_args(argv)
        if args.command == "agents":
            if args.db is not None:
                raise GraphError("USAGE_ERROR", "Agent integration uses --dir/--scope, not --db.")
            data = manage_agents(args.agent_operation, directory=args.dir, scope=args.scope,
                                 target=args.target, dry_run=getattr(args, "dry_run", False))
            output({"success": True, "data": data})
            return 1 if args.agent_operation == "doctor" and not data["ready"] else 0
        if args.command == "install":
            if args.db is not None:
                raise GraphError("USAGE_ERROR", "install takes a project directory, not --db.")
            output({"success": True, "data": install_database(args.directory)})
            return 0
        database = resolve_database(args.db)
        if args.command == "validate":
            report, _ = inspect_database(database, args.lang)
            output({"success": report["valid"], "data": report,
                    **({"code": "INVALID_DATABASE", "message": "The database failed validation."} if not report["valid"] else {})})
            return 0 if report["valid"] else 1
        if args.command in ("gui", "serve"):
            from .server import serve
            serve(database, args.port, not args.no_browser, args.lang)
            return 0
        graph = Graph.load(database, args.lang)
        if args.command == "entry":
            data = graph.entries()
        elif args.command == "search":
            data = graph.search(args.text, args.limit)
        elif args.command == "node":
            data = graph.node(args.id)
        elif args.command == "neighbors":
            data = graph.neighbors(args.id, args.direction, args.relation)
        elif args.command == "walk":
            data = graph.walk(args.id, args.depth, args.max_nodes, args.direction, args.relation)
        elif args.command == "path":
            data = graph.path(args.source, args.target, args.direction)
        output({"success": True, "data": data})
        return 0
    except GraphError as exc:
        output(exc.response(), sys.stderr)
        return 2 if exc.code == "USAGE_ERROR" else 1
    except OSError as exc:
        output(GraphError("IO_ERROR", str(exc)).response(), sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

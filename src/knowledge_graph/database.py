"""Database discovery and atomic initialization from installed package resources."""
from importlib.resources import files
from pathlib import Path
import shutil
import tempfile

from .core import GraphError, inspect_database

DATABASE_DIRECTORY = ".knowledge-graph"


def resolve_database(explicit=None, cwd=None):
    if explicit is not None:
        database = Path(explicit).expanduser().resolve()
        if not database.exists():
            raise GraphError("DATABASE_NOT_FOUND", f"No database at {database}. Run 'knowledge-graph install [DIR]' first, or provide a valid --db PATH.")
        return database
    start = Path(cwd or Path.cwd()).resolve()
    for directory in (start, *start.parents):
        candidate = directory / DATABASE_DIRECTORY
        # Stop at the nearest database even if its manifest is damaged or missing.
        if candidate.exists() or candidate.is_symlink():
            return candidate
    raise GraphError("DATABASE_NOT_FOUND", "No .knowledge-graph database found. Run 'knowledge-graph install [DIR]' first, or provide --db PATH.")


def _copy_resources(source, destination):
    destination.mkdir()
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            _copy_resources(child, target)
        else:
            target.write_bytes(child.read_bytes())


def install_database(directory=None):
    project = Path(directory or Path.cwd()).expanduser().resolve()
    target = project / DATABASE_DIRECTORY
    if target.exists() or target.is_symlink():
        raise GraphError("DATABASE_EXISTS", f"Database directory already exists: {target}. Existing files were not changed.")
    project.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".knowledge-graph-install-", dir=project))
    try:
        prepared = staging / DATABASE_DIRECTORY
        _copy_resources(files("knowledge_graph").joinpath("seed"), prepared)
        report, graph = inspect_database(prepared)
        if not report["valid"] or report["warnings"]:
            raise GraphError("INVALID_SEED", "Packaged seed failed validation.", report)
        # Rename the complete directory on the same filesystem. Never merge into
        # an existing target (including one created by another installer).
        if target.exists() or target.is_symlink():
            raise GraphError("DATABASE_EXISTS", f"Database directory already exists: {target}.")
        try:
            prepared.rename(target)
        except OSError as exc:
            if target.exists() or target.is_symlink():
                raise GraphError("DATABASE_EXISTS", f"Database directory already exists: {target}.") from exc
            raise
        return {"database": str(target), "created": True, "nodes": len(graph.nodes),
                "edges": len(graph.edges), "languages": ["en", "ru"]}
    finally:
        if staging.resolve().parent != project:
            raise GraphError("UNSAFE_STAGING_PATH", "Temporary directory is outside the installation directory.")
        shutil.rmtree(staging)

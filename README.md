# Knowledge Graph

A local documentation graph for people and AI agents. Documents are Markdown files; a versioned JSON manifest connects them with typed, explained relationships. The package has a machine-readable CLI and a read-only browser viewer. Runtime dependencies are limited to the Python standard library. Python 3.10 or newer is required.

## Install the tool

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```powershell
uv tool install git+https://github.com/AndreiUsoltsev/knowledge-graph.git
```

For a local checkout, use `uv tool install D:/PythonProjects/knowledge-graph`. The same CLI is available as `python -m knowledge_graph` in an environment containing the package.

## Initialize a project's database

```powershell
knowledge-graph install D:/Projects/MyProject
knowledge-graph --db D:/Projects/MyProject/.knowledge-graph entry
knowledge-graph --db D:/Projects/MyProject/.knowledge-graph gui
```

`install [DIR]` creates `DIR/.knowledge-graph`, or uses the current directory when DIR is omitted. It copies and validates the packaged template before making the database available. An existing target is never overwritten (`DATABASE_EXISTS`). Initialization does not modify Git, agent instructions, or other project files. The template contains seven documents about this system and fifteen relationships; it contains no application-specific knowledge.

Without `--db`, commands look for the nearest `.knowledge-graph` directory from the current directory upwards. A broken nearest database produces validation errors instead of silently selecting a parent database. If none exists, `DATABASE_NOT_FOUND` suggests running `install`. `--db PATH` always names the exact database directory.

## Read the graph

```powershell
knowledge-graph entry
knowledge-graph search "navigation"
knowledge-graph node system.agent
knowledge-graph neighbors system.agent --direction out
knowledge-graph walk system.overview --depth 2 --max-nodes 20
knowledge-graph path system.overview system.validation
knowledge-graph validate
knowledge-graph --lang ru node system.agent
```

Use `--help` on any command for filters and limits. Data commands return `{ "success": true, "data": ... }` on stdout. Errors return `{ "success": false, "code": ..., "message": ... }` on stderr with a nonzero exit code. `validate` always writes its report to stdout and exits with 1 for an invalid database. Identifiers, relationship types and JSON keys never change with language. Search requires all query terms and reads the selected language, with English fallback for untranslated documents.

For an agent, start with `entry` or `search`, read the selected `node`, then use `neighbors` to choose the next document by relationship type, direction and explanation. Load neighbors' full documents only when needed. Use bounded `walk` for a map and `path` for a route. Check claims against the project's real sources and keep documentation current.

To connect this documentation to an agent, manually add instructions like these to your project's agent instructions:

> Use `knowledge-graph entry` or `knowledge-graph search "topic"` to discover documentation. Read `node ID`, inspect `neighbors ID`, and follow relevant explained relationships. Run `knowledge-graph validate` after editing the database. The documentation supplements source-code inspection.

## Connect coding agents

Version 0.2.0 installs a short persistent rule and an on-demand `knowledge-graph` skill for **Codex, Cursor, Claude Code and OpenCode**. Agents are instructed to use an existing database for documented architecture, behavior and conventions, then load only relevant nodes. Current source remains authoritative; CodeGraph is used first for code discovery in indexed repositories.

Install project integration separately from database initialization:

```powershell
knowledge-graph agents install --dir D:/Projects/MyProject --target all
knowledge-graph agents doctor --dir D:/Projects/MyProject --target all
```

Omit `--dir` when inside the project. Integration works before database creation and with an already populated database. It does not create or change `.knowledge-graph`, modify Git, register MCP servers or relax permissions. Restart the agent session after installation. Automatic use depends on agent configuration and instruction precedence; `doctor` checks installation files, not future model decisions.

| Agent | Persistent project rule | Project skill |
| --- | --- | --- |
| Codex | Managed block in `AGENTS.md` | `.agents/skills/knowledge-graph/SKILL.md` |
| OpenCode | The same block in `AGENTS.md` | The same portable skill |
| Cursor | `.cursor/rules/knowledge-graph.mdc`, `alwaysApply: true` | The same portable skill |
| Claude Code | Managed block in `CLAUDE.md` | `.claude/skills/knowledge-graph/SKILL.md` |

The portable skill includes Codex UI metadata in `agents/openai.yaml`, with implicit invocation enabled. Instructions are English and explain both reading languages.

For integration across projects on this device:

```powershell
knowledge-graph agents install --scope user --target auto
knowledge-graph agents doctor --scope user --target auto
```

User scope installs portable skills in `~/.agents/skills`, Claude skills in `~/.claude/skills`, and rules in Codex `~/.codex/AGENTS.md`, Claude `~/.claude/CLAUDE.md` and OpenCode `~/.config/opencode/AGENTS.md`. `CODEX_HOME` and `XDG_CONFIG_HOME` are respected. **Cursor user scope installs only the skill**; project integration supplies its persistent rule. No global `.cursor/rules` directory is invented. For collaborators/cloud checkouts, commit project integration and install the CLI in the execution environment; local user skills are not automatically deployed elsewhere.

`--target auto` detects executable/config directories and previous integrations. `--target all` installs all four; `--target codex,claude` selects specific agents. Project is the default scope. `--dir` applies only to project scope; top-level `--db` is not used for agent integration.

Preview or remove integration:

```powershell
knowledge-graph agents install --dir D:/Projects/MyProject --target all --dry-run
knowledge-graph agents uninstall --dir D:/Projects/MyProject --target all --dry-run
knowledge-graph agents uninstall --dir D:/Projects/MyProject --target all
knowledge-graph agents uninstall --scope user --target auto
```

Shared instruction files preserve text outside `KNOWLEDGE_GRAPH_START/END`. Dedicated generated skills and the Cursor rule are managed as whole files. Custom files without ownership markers are never overwritten. Malformed/duplicate markers produce `AGENT_CONFIG_CONFLICT`. Plans are checked before writing; write failures roll back completed writes. Symlink/junction customization paths are rejected. Repeated installation updates owned content without duplicates; uninstall retains artifacts still needed by another installed target. An ownership registry is stored in `.agents/knowledge-graph-integrations.json`; empty directories may remain after removal.

`doctor` returns JSON with targets, file paths/statuses, discovered database, CLI path, version and warnings. Exit 0 means ready; exit 1 reports missing/outdated/conflicting installation or caveats, including Cursor user scope and Codex `AGENTS.override.md` precedence; exit 2 means invalid usage. Re-run installation after upgrading to refresh generated instructions.

To upgrade an existing uv tool, first stop any GUI server on Windows:

```powershell
uv tool install --force git+https://github.com/AndreiUsoltsev/knowledge-graph.git
knowledge-graph --version
knowledge-graph agents install --dir D:/Projects/MyProject --target all
```

Integration follows official [Codex instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [skills](https://learn.chatgpt.com/docs/build-skills), [Cursor rules](https://cursor.com/docs/rules) and [skills](https://cursor.com/docs/skills), [Claude instructions](https://code.claude.com/docs/en/memory) and [skills](https://code.claude.com/docs/en/skills), and [OpenCode rules](https://opencode.ai/docs/rules/) and [skills](https://opencode.ai/docs/skills/).

## Browser viewer

`knowledge-graph gui` opens `http://127.0.0.1:8765/`. `serve` is an alias. Use `--port 8766` or `--no-browser` as needed. Stop the server with Ctrl+C. It binds only to loopback, accepts read-only HTTP requests, and exposes the packaged interface and validated graph. It does not expose arbitrary filesystem paths.

The viewer supports search, node and relationship filters, bounded neighborhoods, a full-graph mode, document navigation, browser history, zoom, pan and copy ID. Markdown is rendered as safe DOM elements; raw HTML stays text. Graph geometry stays bounded during resizing. The EN/RU switch defaults to English and remembers the choice in the browser; switching preserves the selected node and graph settings. `--lang ru gui` explicitly opens Russian. No automatic translation or external translation service is used.

Read-only HTTP endpoints: `/api/graph`, `/api/node?id=ID`, `/api/search?q=TEXT&limit=200`, `/api/walk?id=ID&depth=1&max_nodes=50`, `/api/validate`. Reading and search accept `lang=en` or `lang=ru`. Use the CLI for the full traversal API.

## Edit a database

Edit `.knowledge-graph/graph.json` and its Markdown documents in a text editor, then run `knowledge-graph validate`. Store the database in your project's version control if desired. Keep IDs stable, documents focused, and edge explanations useful for choosing a next step.

Version 1 requires `version`, nonempty `entry_points`, `nodes` and `edges`. Nodes have `id`, `title`, `type`, `summary`, `tags`, and a relative `.md` `content` path. Node types are `system`, `concept`, `workflow`, `tool`, `reference`. Edges have `source`, `target`, `type`, `label`. Relationship types are `contains`, `explains`, `requires`, `related`. Paths must remain inside the database, including resolved symlinks.

English lives in the existing fields. Optional `translations.ru` on a node contains `title`, `summary`, `tags`, `content`; on an edge it contains `label`. Translation documents are separate Markdown files. Validation checks both languages even when English is selected. Untranslated custom nodes and edges keep their original values. See `system.format` in the initialized database for a complete example.

## Development

```powershell
uv sync --locked
uv run python -m unittest discover -s tests -v
uv build
uv run python tests/check_distribution.py
```

The distribution check installs the wheel in an isolated uv environment and exercises initialization, CLI and browser resources outside the checkout. CI runs tests and distribution checks on Windows and Linux with Python 3.10 and 3.14. Assets are loaded through `importlib.resources` and included in wheel and sdist. License: MIT.

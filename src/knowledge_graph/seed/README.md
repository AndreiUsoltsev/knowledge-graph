# Project documentation graph

This database contains seven starting documents describing the documentation system itself. Add project knowledge separately.

Install the tool with `uv tool install git+https://github.com/AndreiUsoltsev/knowledge-graph.git`. From this project's root or any child directory, run:

```powershell
knowledge-graph entry
knowledge-graph search "topic"
knowledge-graph node system.overview
knowledge-graph neighbors system.overview
knowledge-graph gui
knowledge-graph validate
```

Elsewhere, pass `--db PATH` with the exact directory containing this README and graph.json. Use `--lang ru` for Russian reading and search. English is the default.

For an AI agent: find an entry point, read one node, inspect its neighbors, and follow the relevant explained relationship. Fetch full documents as needed. For a human: open the browser viewer, or edit graph.json and Markdown files with a text editor and validate the result. Changes can be versioned with the project's Git repository.

To connect the database to your agent instructions, manually add: "Use knowledge-graph entry or search to discover documentation, node ID to read a document and neighbors ID to choose a next step. Validate after editing the database and verify documentation against actual sources."

Initialization never modifies agent instructions automatically. The viewer is read-only. See system.format for the schema and system.human for authoring instructions. English source fields and optional translations.ru contain separate documents; missing translations fall back to the original fields. All paths are relative to this database.

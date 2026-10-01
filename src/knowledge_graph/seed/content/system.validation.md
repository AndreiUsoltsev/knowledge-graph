# Database validation

Run `knowledge-graph validate` after edits. Its JSON report contains `valid`, `database`, `errors` and `warnings`. Invalid databases return exit code 1; validation reports stay on stdout. Other commands reject invalid databases before reading or traversal.

Validation checks version, required fields, supported types, unique IDs, existing entry points and edge endpoints, duplicate edges, and safe relative Markdown paths. Every declared English and Russian document must exist, be UTF-8 and contain text. Invalid translations are errors even when English is selected.

Unreachable nodes are warnings. Reachability starts from all entry points and considers both directions, so a warning means a disconnected component. Cycles are valid; traversal tracks visited IDs.

`DATABASE_NOT_FOUND` suggests `install DIR` or an explicit `--db PATH`. `DATABASE_EXISTS` protects an existing database. `INVALID_DATABASE` includes detailed errors: fix the manifest or referenced documents, validate, then reload the viewer. `UNKNOWN_NODE` means an absent ID.

Development checks: `uv sync --locked`, `uv run python -m unittest discover -s tests -v`, `uv build`, `uv run python tests/check_distribution.py`. Tests cover traversal, validation, translations, initialization, discovery, CLI, HTTP safety and distribution resources. Browser checks cover localization, history and stable dimensions.

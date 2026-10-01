# Human workflow

Use `knowledge-graph gui` to read, search and follow graph connections. The viewer is read-only; author documents in a text editor.

1. Choose a stable unique ID and a focused topic.
2. Write UTF-8 Markdown under `content/`.
3. Add required node fields to `graph.json` with a relative content path.
4. Connect useful nodes with typed explained edges. Add an entry point only for a suitable starting document.
5. Optionally add complete `translations.ru` and a separate Russian document.
6. Run `knowledge-graph validate`; fix errors and review unreachable-node warnings.
7. Reload the viewer and review navigation. Version the database in your project's Git repository if desired.

Do not reuse an ID for another topic. Update edges and entry points when deleting a node. Prefer concise documents linked to related concepts over duplicated explanations. Read [format](kg:system.format) before editing and [validation](kg:system.validation) for diagnostics. Initialization changes only the new `.knowledge-graph` directory, not other files or Git settings.

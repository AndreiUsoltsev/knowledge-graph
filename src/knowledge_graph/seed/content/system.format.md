# Database format

`graph.json` uses version 1 and contains `version`, nonempty `entry_points`, `nodes`, and `edges`. Documents are UTF-8 Markdown inside the database. Keep node IDs stable when titles or translations change.

Nodes require `id`, `title`, `type`, `summary`, `tags`, `content`. IDs start with a lowercase ASCII letter or digit and contain lowercase ASCII letters, digits, dots, underscores or hyphens. Node types: `system`, `concept`, `workflow`, `tool`, `reference`. Titles, summaries and documents must be nonempty. Tags are a list of nonempty strings. Entry points must be unique existing IDs.

Edges require `source`, `target`, `type`, `label`. Endpoints must exist; duplicate source/target/type triples are invalid. Types: `contains`, `explains`, `requires`, `related`. See [relationship semantics](kg:system.links).

Content paths must be relative `.md` paths inside the database. Absolute paths, parent traversal and symlinks escaping the database are rejected. Every declared document is validated.

English source text lives in the regular fields. Optional node `translations.ru` requires `title`, `summary`, `tags`, `content`; edge `translations.ru` requires `label`. Russian documents use separate Markdown files. Missing translations fall back to original fields. IDs, types and JSON keys remain unchanged. Both languages are validated regardless of the selected reading language.

```json
{"id":"topic.overview","title":"Topic overview","type":"concept","summary":"An introduction.","tags":["topic"],"content":"content/topic.md","translations":{"ru":{"title":"Обзор темы","summary":"Введение.","tags":["тема"],"content":"content/ru/topic.md"}}}
```

---
name: knowledge-graph
description: Read and maintain a project's local documentation graph through the knowledge-graph CLI. Use when a repository has .knowledge-graph/graph.json and a task needs documented architecture, behavior, conventions or relationships between systems.
---

<!-- KNOWLEDGE_GRAPH_MANAGED_SKILL -->

# Project knowledge graph

Use focused documentation to orient an investigation. Do not load the whole database into context.

## Read and navigate

The `knowledge-graph` command is a separately installed Python tool. If it is unavailable, explain the missing tool and read the database README for the project's setup. Initialization is not a repair for a missing executable.

From the project or a child directory:

```text
knowledge-graph entry
knowledge-graph search "task vocabulary"
knowledge-graph node NODE_ID
knowledge-graph neighbors NODE_ID
```

Choose the next node by its summary, relationship type and explanation, then fetch that node's body separately. `contains` organizes topics; `requires` identifies prerequisites; `related` connects useful investigations; `explains` provides an explanation. Incoming relationships help locate consumers. IDs and JSON keys stay the same in both languages.

For a bounded map or a route:

```text
knowledge-graph walk NODE_ID --depth 2 --max-nodes 20
knowledge-graph path START_ID END_ID --direction out
knowledge-graph --lang ru node NODE_ID
knowledge-graph --db PATH_TO_DATABASE entry
```

`--db` names the directory containing graph.json. Without it, the CLI discovers the nearest `.knowledge-graph` by walking upwards. A malformed nearest database is reported rather than bypassed. Keep CLI errors visible and consult `--help` for filters/limits.

## Verify and maintain

Follow repository instructions and inspect current sources before making decisions. Use CodeGraph first for code discovery when the repository is indexed. A documentation claim or successful `validate` does not establish compilation or runtime correctness.

If the project has a source-audit helper, use the procedure in its database README to check changed sources and affected nodes. Do not refresh source hashes just to silence warnings.

When relevant behavior changes, update focused Markdown documents, metadata and explained relationships. Preserve stable node IDs. Canonical text is English; update existing Russian translations alongside it. Do not invent missing translations or present unverified behavior as tested.

```text
knowledge-graph validate
```

For the schema and authoring conventions, read `system.format`, `system.links` and `system.human`. Initialize a new database with `knowledge-graph install DIR` only when requested; an existing database must be preserved.

The browser viewer is optional for a person: `knowledge-graph gui`. It is not needed for agent reading. Stop a viewer you launch when finished, particularly before reinstalling the tool on Windows.

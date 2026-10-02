# AI agent workflow

Load relevant documentation incrementally. CLI responses are JSON; a full document is Markdown in `body`. Success returns `success` and `data`; errors include stable `code`, message and optional details.

1. Run `knowledge-graph entry` or `knowledge-graph search "question terms"`.
2. Read `knowledge-graph node ID` for the best candidate.
3. Inspect `knowledge-graph neighbors ID`; choose by type, direction and explanation.
4. Read the next full document only when useful.
5. Use `walk ID --depth 2 --max-nodes 20` for a bounded map, or `path START END` for a shortest route.

Search requires all query terms and prioritizes IDs and titles. English is the default. Use `knowledge-graph --lang ru search "навигация"` for Russian. Untranslated nodes use their original document. Use `--db PATH` outside the project tree. Missing databases suggest `install DIR`; damaged databases require `validate` and repair.

Verify knowledge against actual sources. Update focused documents and explained relationships when behavior changes. Database initialization does not write agent instructions. Use the separate `knowledge-graph agents install --target all` command to add persistent rules and the detailed skill, then `knowledge-graph agents doctor --target all` to inspect readiness. Restart the agent session after installation. Existing database content is preserved.

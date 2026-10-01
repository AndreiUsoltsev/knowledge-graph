# Documentation system

The knowledge graph organizes focused Markdown documents as nodes. Typed relationships with explanations help a human or AI agent choose the next useful document without loading the whole database.

The initial database describes this system only. Add project-specific knowledge separately. The tool works with any project and requires Python 3.10 or newer. Runtime dependencies are limited to the standard library.

Initialize a project with `knowledge-graph install DIR`. An existing `.knowledge-graph` is never overwritten. Without `--db`, commands find the nearest database above the working directory. Use `--db PATH` for an exact database directory.

Start with `entry`, `search "topic"`, `node ID`, and `neighbors ID`, or open `gui`. See [database format](kg:system.format), [relationship semantics](kg:system.links), [agent workflow](kg:system.agent), and [human workflow](kg:system.human). Validate after edits and verify claims against real project sources.

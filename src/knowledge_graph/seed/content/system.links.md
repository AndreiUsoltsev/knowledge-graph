# Relationship semantics

A relationship points from source to target. Its explanation says why and when to follow it. Directions stay meaningful even when the viewer displays both incoming and outgoing connections.

| Type | Meaning |
| --- | --- |
| contains | The source organizes or contains the target topic |
| explains | The source explains the target |
| requires | Understanding or using the source requires the target |
| related | The topics are useful together |

Write actionable labels such as "Read required fields before adding a document." Avoid repeating only a target title. `requires` means a prerequisite, not a chronological next step.

`neighbors ID --direction out` follows source to target; `--direction in` finds documents pointing here. The default `both` supports exploration. `walk` and `path` support direction and relationship filters and preserve declared edge direction. Cycles are valid; traversal tracks visited IDs.

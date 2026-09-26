---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0005
release_version: 0.9.0
kind: docs
summary:
  Documented API and CLI reference pages using Sphinx-compatible directives and tables
status: accepted
audience: null
scopes: []
source_refs:
  - git:654c2491e0fac5e589fb82543c79fc13b2a305bf
  - git:70356167906fde24fecd03fffa9997851a271b32
paths:
  - docs/api.md
  - docs/cli.md
  - docs/parser.md
issues: []
prs: []
sources: []
contributors:
  - "@holgern"
breaking: false
internal: false
order: 5
---

Converted API reference directives and exit-code table markup to forms supported by the
Sphinx/MyST documentation build, while aligning nearby examples with the documented SSMD
0.9 contract.

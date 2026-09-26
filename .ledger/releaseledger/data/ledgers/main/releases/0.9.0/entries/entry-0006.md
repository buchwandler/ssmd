---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0006
release_version: 0.9.0
kind: changed
summary:
  Changed parsing, formatting, and migration to preserve paragraph semantics across
  adjacent fenced voice scopes
status: accepted
audience: null
scopes: []
source_refs:
  - tl:task-0016
  - git:52b406a30be84844bf17687aa2766e4cd989efff
paths:
  - ssmd/parser.py
  - ssmd/formatter.py
  - ssmd/migration.py
  - tests/test_migration.py
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 6
---

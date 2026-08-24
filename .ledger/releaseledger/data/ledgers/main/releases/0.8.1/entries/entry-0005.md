---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0005
release_version: 0.8.1
kind: fixed
summary:
  Preserved whitespace before leading decimals during parsing and sentence rendering
status: accepted
audience: null
scopes: []
source_refs:
  - tl:task-0006
paths:
  - ssmd/parser.py
  - ssmd/sentence.py
  - tests/test_parser.py
  - tests/test_parse_spans.py
  - tests/test_formatter.py
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 5
---

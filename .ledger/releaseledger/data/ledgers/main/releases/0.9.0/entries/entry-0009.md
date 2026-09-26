---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0009
release_version: 0.9.0
kind: quality
summary:
  Improved test portability and protected canonical SSMD examples from generic
  formatting
status: accepted
audience: null
scopes: []
source_refs:
  - git:bc561876c172c497c1b7bd482e760a8b9eb1e0fe
  - git:83c06dcda34bff3dd46c742abde46f3d2daf4489
paths:
  - tests/test_cli.py
  - tests/test_migration.py
  - .pre-commit-config.yaml
  - examples/all_features.ssmd.md
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: true
order: 9
---

Tests avoid platform-specific file assertions, and generic Prettier no longer rewrites
canonical SSMD Markdown examples.

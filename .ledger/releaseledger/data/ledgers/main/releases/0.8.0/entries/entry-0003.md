---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0003
release_version: 0.8.0
kind: internal
summary:
  Improved parser tooling and pre-commit integration for consistent project checks
status: accepted
audience: null
scopes: []
source_refs:
  - git:0fa38173b9f5260be04313f23b379d31cc104944
paths:
  - .github/workflows/pre-commit.yml
  - .pre-commit-config.yaml
  - ssmd/cli.py
  - ssmd/ssml_parser.py
  - ssmd/utils.py
  - tests/test_parser_models.py
  - tests/test_roundtrip_ssml_maker.py
issues: []
prs: []
sources:
  - git:0fa38173b9f5260be04313f23b379d31cc104944
contributors: []
breaking: false
internal: true
order: 3
---

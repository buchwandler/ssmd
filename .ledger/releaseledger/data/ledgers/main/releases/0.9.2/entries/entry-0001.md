---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: 0.9.2
kind: added
summary:
  Added strict diagnostics and remediation hints for directive fences shorter than three
  colons
status: accepted
audience: null
scopes: []
source_refs:
  - git:b0e73b5fdb82dc93344ba83b24f265452bd7f00b
paths:
  - SPECIFICATION.md
  - docs/cli.md
  - docs/syntax.md
  - skills/ssmd/SKILL.md
  - spec/fixtures/invalid.json
  - ssmd/cli.py
  - ssmd/parser.py
  - ssmd/spans.py
  - ssmd/tokenizer.py
  - tests/test_cli.py
  - tests/test_cli_json_contract.py
  - tests/test_lint_diagnostics.py
  - tests/test_parse_structure.py
  - tests/test_spec_fixtures.py
issues: []
prs: []
sources:
  - git:b0e73b5fdb82dc93344ba83b24f265452bd7f00b
contributors:
  - "@holgern"
breaking: false
internal: false
order: 1
---

---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0010
release_version: 0.8.0
kind: added
summary:
  Added portable YAML front matter with voice bindings, pause defaults, and
  provider-aware authoring
status: accepted
audience: null
scopes: []
source_refs:
  - git:5f264b0cb737fcc130a3233c4119bd7fd8969b59
paths:
  - .ledger/ledger.toml
  - .ledger/taskledger/.ledger-project.toml
  - .ledger/taskledger/config.toml
  - README.md
  - SPECIFICATION.md
  - docs/api.md
  - docs/cli.md
  - docs/syntax.md
  - skills/ssmd/SKILL.md
  - ssmd/__init__.py
  - ssmd/cli.py
  - ssmd/cli_common.py
  - ssmd/command_inventory.py
  - ssmd/config.py
  - ssmd/document.py
  - ssmd/durations.py
  - ssmd/frontmatter.py
  - ssmd/parser.py
  - ssmd/utils.py
  - ssmd/voices.py
  - tests/test_command_inventory.py
  - tests/test_config.py
  - tests/test_config_cli.py
  - tests/test_frontmatter_schema.py
  - tests/test_header_materialization.py
  - tests/test_inspect_header_voices.py
  - tests/test_pause_defaults.py
  - tests/test_voice_inventory.py
issues: []
prs: []
sources:
  - git:5f264b0cb737fcc130a3233c4119bd7fd8969b59
contributors: []
breaking: false
internal: false
order: 10
---

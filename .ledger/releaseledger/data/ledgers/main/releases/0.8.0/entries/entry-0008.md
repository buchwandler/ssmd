---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0008
release_version: 0.8.0
kind: internal
summary: Changed package metadata, release state, and command-inventory checks
status: accepted
audience: null
scopes: []
source_refs:
  - git:919d65359e1af630e780032349c5c1a9f7501ac0
paths:
  - .ledger/ledger.toml
  - .ledger/releaseledger/.ledger-project.toml
  - .ledger/releaseledger/config.toml
  - .ledger/releaseledger/data/.ledger-project.toml
  - .ledger/releaseledger/data/ledgers/main/events/events.jsonl
  - .ledger/releaseledger/data/ledgers/main/releases/v0.8.0/release.md
  - .ledger/releaseledger/write.lock
  - docs/changelog.md
  - pyproject.toml
  - ssmd/cli.py
  - tests/test_command_inventory.py
  - tests/test_package_artifacts.py
  - tests/test_skill_contract.py
issues: []
prs: []
sources:
  - git:919d65359e1af630e780032349c5c1a9f7501ac0
contributors: []
breaking: false
internal: true
order: 8
---

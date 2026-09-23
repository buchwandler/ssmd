---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0004
release_version: 0.9.0
kind: changed
summary:
  "Changed CLI inference: plain .md needs ssmd_version or --from; .ssmd.md is the
  recommended complete-document name"
status: accepted
audience: null
scopes: []
source_refs:
  - git:c7ac987ec47d9d058a3fcbfe8bee7b078d5abe15
paths:
  - README.md
  - SPECIFICATION.md
  - docs/cli.md
  - docs/quickstart.md
  - skills/ssmd/SKILL.md
  - ssmd/cli.py
  - tests/test_cli.py
  - tests/test_cli_json_contract.py
issues: []
prs: []
sources:
  - git:c7ac987ec47d9d058a3fcbfe8bee7b078d5abe15
contributors:
  - "@holgern"
breaking: false
internal: false
order: 4
---

Use .ssmd.md for complete SSMD documents; .ssmd remains supported and plain .md remains
generic Markdown. The converter infers SSMD from a plain .md file only when its front
matter declares ssmd_version. Otherwise callers must select --from explicitly, avoiding
accidental treatment of ordinary Markdown as SSMD.

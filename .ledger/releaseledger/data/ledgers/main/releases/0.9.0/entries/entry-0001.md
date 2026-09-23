---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0001
release_version: 0.9.0
kind: changed
summary:
  Changed rate and pitch scales and added per-voice defaults with prosody transition
  diagnostics
status: accepted
audience: null
scopes: []
source_refs:
  - git:18243636d79c26156901a15f23ea5aaadb75b8cb
paths:
  - SPECIFICATION.md
  - docs/cli.md
  - docs/ssml_conversion.md
  - docs/syntax.md
  - ssmd/frontmatter.py
  - ssmd/parser.py
  - ssmd/segment.py
  - ssmd/ssml_conversions.py
  - ssmd/types.py
  - tests/test_natural_prosody.py
  - tests/test_prosody_transitions.py
  - tests/test_voice_defaults.py
issues: []
prs: []
sources:
  - git:18243636d79c26156901a15f23ea5aaadb75b8cb
contributors:
  - "@holgern"
breaking: true
internal: false
order: 1
---

SSMD now resolves voice_defaults per prosody field, supports configurable
prosody_transitions, and reports inconsistent or abrupt voice changes through lint and
inspection. Named rate and pitch values use descriptive scales mapped to percentages,
for example slow maps to 80% and fast to 125%. This changes rendered output for existing
named values; packed and short aliases remain compatibility forms rather than canonical
0.9 syntax.

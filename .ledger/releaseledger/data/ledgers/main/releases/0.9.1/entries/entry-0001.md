---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: 0.9.1
kind: added
summary:
  Added support for application-defined audio URIs and strict playback attribute
  validation
status: accepted
audience: null
scopes: []
source_refs:
  - git:17d0dc57eedabeaca622d4db9d655a5f206adfa5
paths:
  - docs/syntax.md
  - ssmd/parser.py
  - ssmd/segment.py
  - ssmd/types.py
  - ssmd/validation.py
  - tests/test_audio_sfx_uri.py
issues: []
prs: []
sources:
  - git:17d0dc57eedabeaca622d4db9d655a5f206adfa5
contributors:
  - "@holgern"
breaking: false
internal: false
order: 1
---

Audio source values may use application-specific URI schemes and pass through parsing,
canonical SSMD formatting, and generic SSML rendering without SSMD attempting to resolve
them. Audio playback attributes receive value-specific validation, and empty audio
annotations remain available as zero-width spans in parsed structures.

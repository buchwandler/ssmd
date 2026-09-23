---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0003
release_version: 0.9.0
kind: added
summary:
  Added generic, SSML 1.1, and provider targets with BCP-47 language preservation and
  explicit loss policies
status: accepted
audience: null
scopes: []
source_refs: []
paths:
  - docs/capabilities.md
  - docs/ssml_conversion.md
  - ssmd/rendering.py
  - ssmd/ssml_parser.py
  - tests/test_rendering_targets.py
  - tests/test_ssml_09_contract.py
issues: []
prs: []
sources:
  - git:3479a32cfa850d151f8eb7a8f6bd904ab0b810fd
contributors:
  - "@holgern"
breaking: false
internal: false
order: 3
---

Rendering distinguishes generic SSML, strict SSML 1.1, and provider-adapted output. SSML
1.1 requires an explicit root language; language tags are preserved without inferring a
region. Provider adaptations report unsupported semantics under explicit error, warn, or
drop policies. Reverse conversion rejects unknown element semantics by default and emits
a complete versioned 0.9 document unless fragment output is requested. Voice-language
selectors map to SSML languages, and audio description metadata is distinct from spoken
fallback content.

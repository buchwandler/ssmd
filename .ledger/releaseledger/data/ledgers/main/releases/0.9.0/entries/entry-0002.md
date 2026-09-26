---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 4
entry_id: entry-0002
release_version: 0.9.0
kind: changed
summary:
  Changed SSMD to strict 0.9 syntax with portable front matter, canonical formatting,
  migration, and trusted extensions
status: accepted
audience: null
scopes: []
source_refs:
  - git:3479a32cfa850d151f8eb7a8f6bd904ab0b810fd
  - git:81b49addbedeadcd22ca92b86d2ee0bf22928cda
paths:
  - README.md
  - SPECIFICATION.md
  - docs/api.md
  - docs/cli.md
  - docs/quickstart.md
  - docs/ssml_conversion.md
  - docs/syntax.md
  - spec/grammar.ebnf
  - ssmd/cli.py
  - ssmd/formatter.py
  - ssmd/frontmatter.py
  - ssmd/migration.py
  - ssmd/tokenizer.py
  - ssmd/validation.py
  - tests/test_formatter.py
  - tests/test_migration.py
  - tests/test_frontmatter_schema.py
issues: []
prs: []
sources:
  - git:3479a32cfa850d151f8eb7a8f6bd904ab0b810fd
contributors:
  - "@holgern"
breaking: true
internal: false
order: 2
---

Complete documents can declare ssmd_version: "0.9" and use strict canonical syntax:
recursively parsed annotations with quoted attributes, colon-fenced directives,
headings, marks, breaks, and canonical emphasis. Portable front matter validates BCP-47
language tags, voice bindings and defaults, pause settings, and extension requirements;
executable extension handlers must come from trusted configuration. Voice selectors use
voice-name and voice-languages. The canonical formatter formats 0.9 without migrating
unversioned or 0.8 documents. The explicit migrate --to 0.9 command verifies semantic
equivalence and writes atomically, returning manual actions when equivalence cannot be
established. CLI JSON responses expose a stable schema.

---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0004
release_version: 0.8.0
kind: added
summary:
  Added parser, document, capability, diagnostics, and security coverage for SSMD
  processing
status: accepted
audience: null
scopes: []
source_refs:
  - git:10a0586ed83a1d1b5cecbcc7bfc99b743a0167d0
paths:
  - .codecrate.toml
  - .pre-commit-config.yaml
  - .ruff.toml
  - .taskledger.toml
  - AGENTS.md
  - README.md
  - SPECIFICATION.md
  - docs/cli.rst
  - docs/conf.py
  - docs/installation.rst
  - docs/make.py
  - docs/requirements.txt
  - docs/spans.rst
  - examples/sentence_paragraph_detection_demo.py
  - examples/sentence_segment_demo.py
  - examples/tts_rich_parser_demo.py
  - pyproject.toml
  - requirements-test.txt
  - ssmd/__init__.py
  - ssmd/capabilities.py
  - ssmd/cli.py
  - ssmd/document.py
  - ssmd/formatter.py
  - ssmd/parser.py
  - ssmd/segment.py
  - ssmd/sentence.py
  - ssmd/spans.py
  - ssmd/ssml_parser.py
  - ssmd/utils.py
  - tests/test_basic.py
  - tests/test_capabilities.py
  - tests/test_cli.py
  - tests/test_formatter.py
  - tests/test_headings.py
  - tests/test_lint_diagnostics.py
  - tests/test_package_artifacts.py
  - tests/test_parse_spans.py
  - tests/test_parser.py
  - tests/test_parser_models.py
  - tests/test_roundtrip_ssml_maker.py
  - tests/test_security.py
  - tests/test_ssml_to_ssmd.py
  - tools/check_artifacts.py
  - tools/verify_reconstruction.py
issues: []
prs: []
sources:
  - git:10a0586ed83a1d1b5cecbcc7bfc99b743a0167d0
contributors: []
breaking: false
internal: false
order: 4
---

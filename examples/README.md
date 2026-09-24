# SSMD Examples

Run the Python examples from the repository root, for example:

```bash
python examples/parser_demo.py
python examples/story_reader_demo.py
python examples/tts_with_capabilities.py
```

## Canonical SSMD 0.9

These are the recommended examples for new SSMD documents. Complete documents declare
`ssmd_version: '0.9'`, use fenced `:::` block directives, and use canonical long-form
attributes. Complete source files use the `.ssmd.md` extension.

- [`all_features.ssmd.md`](all_features.ssmd.md) — comprehensive syntax and front
  matter.
- [`parser_demo.py`](parser_demo.py) — `parse_structure(..., dialect="0.9")`, clean
  text, annotations, structural events, and strict lint diagnostics.
- [`tts_rich_parser_demo.py`](tts_rich_parser_demo.py) — rich display of structural
  spans/events.
- [`story_reader_demo.py`](story_reader_demo.py) and
  [`tts_container_demo.py`](tts_container_demo.py) — render strict 0.9 documents through
  the `Document` API.
- [`tts_with_capabilities.py`](tts_with_capabilities.py) — compare capability-aware
  outputs from strict 0.9 source. The Polly extension is provider-specific.
- [`google_tts_styles.py`](google_tts_styles.py) — register style extensions and combine
  them with canonical fenced voice directives.

[`compare_examples.py`](compare_examples.py) is a conversion utility: it converts the
comprehensive 0.9 example and the SSML fixtures in both directions, writing generated
files beside the examples.

## Legacy 0.8 compatibility and migration material

These files are deliberately isolated from the current examples. Their older syntax and
sentence-oriented APIs remain useful for compatibility coverage and migration
demonstrations; new documents should follow the canonical examples above.

- [`legacy/cli_changes_podcast_08.ssmd`](legacy/cli_changes_podcast_08.ssmd) is a 0.8
  migration input containing legacy raw `<div>` voice scopes.
- [`legacy/legacy_08_sentence_segment_demo.py`](legacy/legacy_08_sentence_segment_demo.py)
  demonstrates compatibility-oriented sentence and segment APIs.
- [`legacy/legacy_08_sentence_paragraph_detection_demo.py`](legacy/legacy_08_sentence_paragraph_detection_demo.py)
  demonstrates legacy sentence and paragraph detection.

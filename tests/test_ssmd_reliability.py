"""Public API regressions for SSMD voice and round-trip semantics."""

import ssmd


def _roundtrip(source: str) -> tuple[ssmd.Document, ssmd.Document]:
    original = ssmd.Document(source, config={"sentence_use_spacy": False})
    restored = ssmd.Document.from_ssml(
        original.to_ssml(),
        config={"sentence_use_spacy": False},
    )
    return original, restored


def test_one_voice_block_roundtrips():
    original, restored = _roundtrip('<div voice="host">\nHello.\n</div>')
    assert restored.to_text() == original.to_text()
    assert "<div" not in restored.to_text()


def test_two_sibling_voice_blocks_roundtrip():
    source = '<div voice="host">\nHello.\n</div>\n\n<div voice="analyst">\nWorld.\n</div>'
    original, restored = _roundtrip(source)
    assert restored.to_text() == original.to_text()
    voices = [
        segment.voice.name
        for sentence in restored._parse_sentence_objects()
        for segment in sentence.segments
        if segment.voice is not None
    ]
    assert voices == ["host", "analyst"]


def test_heading_and_front_matter_roundtrip():
    source = """---
title: Summary
---

# Summary

<div voice="host">
Hello.
</div>
"""
    original, restored = _roundtrip(source)
    assert restored.to_text() == original.to_text()
    assert "<div" not in restored.to_text()


def test_voice_roundtrip_preserves_nested_emphasis_and_punctuation():
    source = '<div voice="host">\nHello, *world*!\n</div>\n\n<div voice="analyst">\nWorld: (again);\n</div>'
    original, restored = _roundtrip(source)
    assert restored.to_text() == original.to_text()


def test_five_sibling_voice_blocks_roundtrip():
    source = """---
title: Implementation Summary
---

# Implementation Summary

<div voice="host">
The project now has a structured configuration and template system.
</div>

<div voice="analyst">
Voice providers, voice IDs, and logical roles are configured centrally.
</div>

<div voice="host">
Generated text can be stored in the ingest directory and rendered automatically.
</div>

<div voice="analyst">
SSMD integration validates *role-driven* documents and enables multi-speaker narration.
</div>

<div voice="host">
The remaining work is to make that integration reliable.
</div>
"""
    original, restored = _roundtrip(source)
    assert restored.to_text() == original.to_text()
    assert "<div" not in restored.to_text()


def test_roundtrip_tolerates_blank_line_variation_between_siblings():
    compact = '<div voice="host">\nHello.\n</div>\n<div voice="analyst">\nWorld.\n</div>'
    spaced = '<div voice="host">\nHello.\n</div>\n\n\n<div voice="analyst">\nWorld.\n</div>'
    compact_original, compact_restored = _roundtrip(compact)
    spaced_original, spaced_restored = _roundtrip(spaced)
    assert compact_restored.to_text() == compact_original.to_text()
    assert spaced_restored.to_text() == spaced_original.to_text()
    assert compact_restored.to_text() == spaced_restored.to_text()

"""Tests for logical voice prosody defaults and effective rendering."""

import ssmd
from ssmd.parser import parse_sentences

HEADER = """---
voice_bindings:
  kokoro:
    guest: af_bella
voice_defaults:
  guest:
    pitch: high
---
"""


def test_voice_default_pitch_applies_to_div_without_materializing_source():
    source = HEADER + '<div voice="guest">\nHello.\n</div>\n'
    document = ssmd.Document(source)

    assert 'pitch="+12%"' in document.to_ssml()
    formatted = document.to_ssmd(include_header=True)
    assert '<div voice="guest">' in formatted
    assert 'pitch="high"' not in formatted
    assert document.voice_defaults["guest"].pitch == "high"


def test_explicit_div_override_wins_per_field():
    document = ssmd.Document(HEADER + '<div voice="guest" pitch="normal">\nHello.\n</div>\n')

    result = document.to_ssml()

    assert 'pitch="+0%"' in result
    assert 'pitch="+12%"' not in result


def test_rate_override_keeps_default_pitch():
    document = ssmd.Document(HEADER + '<div voice="guest" rate="slow">\nHello.\n</div>\n')

    result = document.to_ssml()

    assert 'rate="80%"' in result
    assert 'pitch="+12%"' in result


def test_inline_voice_annotation_uses_logical_voice_default():
    document = ssmd.Document(HEADER + '[Hello]{voice="guest"}')

    result = document.to_ssml()

    assert '<voice name="guest">' in result
    assert 'pitch="+12%"' in result


def test_declared_parser_prosody_is_not_mutated_by_resolution():
    sentences = parse_sentences('<div voice="guest">\nHello.\n</div>')

    assert sentences[0].prosody is None


def test_parse_structure_can_expose_declared_and_effective_annotations():
    result = ssmd.parse_structure(
        HEADER + '<div voice="guest">\nHello.\n</div>\n',
        resolve_defaults=True,
    )
    declared = next(annotation for annotation in result.annotations if annotation.kind == "div")
    effective = next(
        annotation for annotation in result.effective_annotations if annotation.kind == "div"
    )

    assert "pitch" not in declared.attrs
    assert effective.attrs["pitch"] == "high"

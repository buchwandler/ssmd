"""Tests for shared SSMD front matter behavior."""

import pytest

import ssmd
from ssmd.frontmatter import (
    FrontMatterError,
    merge_generated_header,
    parse_front_matter,
    serialize_front_matter,
    validate_front_matter,
)


def test_front_matter_delimiters_and_unknown_data():
    result = parse_front_matter("---\ntitle: Demo\n---\nHello\n")
    assert result.present is True
    assert result.data == {"title": "Demo"}
    assert result.body == "Hello\n"
    assert parse_front_matter("----\nHello").present is False


def test_front_matter_accepts_dots_and_rejects_non_mapping():
    assert parse_front_matter("---\ntitle: Demo\n...\nBody").body == "Body"
    with pytest.raises(FrontMatterError, match="root must be a mapping"):
        parse_front_matter("---\n- value\n---\nBody")


def test_front_matter_merge_preserves_explicit_values():
    merged = merge_generated_header(
        {"title": "Demo", "voice_bindings": {"kokoro": {"a": "one"}}},
        {"voice_bindings": {"kokoro": {"b": "two"}}, "pause_defaults": {"enabled": True}},
    )
    assert merged["voice_bindings"] == {"kokoro": {"a": "one", "b": "two"}}
    assert "pause_defaults:" in serialize_front_matter(merged, "Body")


def test_front_matter_empty_mapping_accepts_generated_defaults():
    merged = merge_generated_header(
        {"voice_bindings": {}},
        {"voice_bindings": {"kokoro": {"host": "af_sarah"}}},
    )
    assert merged["voice_bindings"] == {"kokoro": {"host": "af_sarah"}}


def test_front_matter_explicit_nested_binding_wins_over_generated_default():
    merged = merge_generated_header(
        {"voice_bindings": {"kokoro": {"host": "af_bella"}}},
        {"voice_bindings": {"kokoro": {"host": "af_sarah", "analyst": "am_michael"}}},
    )
    assert merged["voice_bindings"] == {"kokoro": {"host": "af_bella", "analyst": "am_michael"}}


def test_title_is_portable_string_metadata():
    assert validate_front_matter({"title": "Review podcast"}) == []
    assert validate_front_matter({"title": 42})[0].code == "header.title_invalid"

    serialized = serialize_front_matter({"title": "Review podcast"}, "Hello.")
    assert "title: Review podcast" in serialized


def test_voice_defaults_and_transitions_are_validated_and_ordered():
    data = {
        "prosody_transitions": {"rate": "450ms"},
        "voice_defaults": {"guest": {"pitch": "high"}},
    }
    assert validate_front_matter(data) == []
    serialized = serialize_front_matter(data, "Hello.")
    assert serialized.index("voice_defaults:") < serialized.index("prosody_transitions:")


def test_voice_defaults_reject_malformed_entries():
    issues = validate_front_matter(
        {
            "voice_defaults": {"guest": "high", "host": {"emotion": "sarcastic"}},
            "prosody_transitions": {"rate": "fast"},
        }
    )
    assert {issue.code for issue in issues} >= {
        "header.voice_default_invalid",
        "header.voice_default_unknown_key",
        "header.prosody_transition_duration_invalid",
    }


def test_document_exposes_transition_policy_and_keeps_it_out_of_ssml():
    source = """---
prosody_transitions:
  enabled: true
  same_voice_only: true
  rate: 450ms
  pitch: 300ms
---
Hello.
"""
    document = ssmd.Document(source)
    assert document.prosody_transitions is not None
    assert document.prosody_transitions.rate == "450ms"
    serialized = document.to_ssmd(include_header=True)
    assert "prosody_transitions:" in serialized
    assert "<transition" not in document.to_ssml()


def test_voice_default_invalid_prosody_value_is_diagnostic():
    issues = validate_front_matter({"voice_defaults": {"guest": {"pitch": "banana"}}})
    assert any(issue.code == "header.voice_default_prosody_invalid" for issue in issues)

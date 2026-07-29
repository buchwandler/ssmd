"""Tests for shared SSMD front matter behavior."""

import pytest

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
    assert merged["voice_bindings"] == {"kokoro": {"a": "one"}}
    assert "pause_defaults:" in serialize_front_matter(merged, "Body")


def test_title_is_portable_string_metadata():
    assert validate_front_matter({"title": "Review podcast"}) == []
    assert validate_front_matter({"title": 42})[0].code == "header.title_invalid"

    serialized = serialize_front_matter({"title": "Review podcast"}, "Hello.")
    assert "title: Review podcast" in serialized

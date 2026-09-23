"""Tests for document-level prosody transition metadata."""

import pytest

import ssmd
from ssmd.frontmatter import validate_front_matter


def test_transition_defaults_are_preserved_and_exposed():
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

    policy = document.prosody_transitions
    assert policy is not None
    assert policy.enabled is True
    assert policy.same_voice_only is True
    assert policy.rate == "450ms"
    assert policy.pitch == "300ms"
    assert "prosody_transitions:" in document.to_ssmd(include_header=True)


def test_transition_policy_is_not_emitted_as_ssml_markup():
    source = """---
prosody_transitions:
  rate: 450ms
---
Hello.
"""
    ssml = ssmd.Document(source).to_ssml()

    assert "transition" not in ssml
    assert "prosody" not in ssml


def test_transition_duration_must_use_duration_syntax():
    issues = validate_front_matter({"prosody_transitions": {"rate": "fast"}})

    assert any(issue.code == "header.prosody_transition_duration_invalid" for issue in issues)


@pytest.mark.parametrize("field", ["enabled", "same_voice_only"])
def test_transition_boolean_fields_are_validated(field):
    issues = validate_front_matter({"prosody_transitions": {field: "yes"}})

    assert any(issue.code == "header.prosody_transition_option_invalid" for issue in issues)

"""Regression tests for canonical lint syntax and diagnostic contracts."""

import pytest

import ssmd


@pytest.mark.parametrize(
    "source",
    [
        "*moderate*",
        "**strong**",
        "~~reduced~~",
        '[none]{emphasis="none"}',
        '[Bonjour]{lang="fr"}',
        '[tomato]{ipa="təˈmeɪtoʊ"}',
        '[123]{as="cardinal"}',
        '[H2O]{sub="water"}',
        '[loud]{v="5"}',
        "Hello ...500ms world",
    ],
)
def test_ssmd_core_canonical_syntax_has_no_lint_issues(source):
    assert ssmd.lint(source, profile="ssmd-core") == []


def test_strict_voice_directive_allows_selector_and_prosody_attributes_in_core_profile():
    source = """\
---
ssmd_version: "0.9"
---
:::{voice="guest" voice-languages="en-US" age="30" volume="loud" rate="fast" pitch="high"}
Hello.
:::
"""

    assert ssmd.lint(source, profile="ssmd-core", dialect="0.9") == []


def test_malformed_annotation_has_stable_error_diagnostic():
    result = ssmd.parse_spans('Hello [world]{lang="fr"')

    assert result.diagnostics[0].code == "syntax.unbalanced_braces"
    assert result.diagnostics[0].severity == "error"
    assert result.diagnostics[0].line == 1
    assert result.diagnostics[0].column is not None

    issue = ssmd.lint('Hello [world]{lang="fr"')[0]
    assert issue.code == "syntax.unbalanced_braces"
    assert issue.severity == "error"


def test_lint_warns_on_inconsistent_voice_pitch_without_default():
    source = '<div voice="guest" pitch="high">\nOne.\n</div>\n<div voice="guest">\nTwo.\n</div>'
    issues = ssmd.lint(source)
    assert any(issue.code == "voice.prosody_inconsistent" for issue in issues)


def test_lint_does_not_warn_when_voice_default_resolves_consistency():
    source = """---
voice_defaults:
  guest:
    pitch: high
---
<div voice="guest" pitch="high">
One.
</div>
<div voice="guest">
Two.
</div>"""
    assert not any(issue.code == "voice.prosody_inconsistent" for issue in ssmd.lint(source))

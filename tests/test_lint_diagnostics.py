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


def test_malformed_annotation_has_stable_error_diagnostic():
    result = ssmd.parse_spans('Hello [world]{lang="fr"')

    assert result.diagnostics[0].code == "syntax.unbalanced_braces"
    assert result.diagnostics[0].severity == "error"
    assert result.diagnostics[0].line == 1
    assert result.diagnostics[0].column is not None

    issue = ssmd.lint('Hello [world]{lang="fr"')[0]
    assert issue.code == "syntax.unbalanced_braces"
    assert issue.severity == "error"

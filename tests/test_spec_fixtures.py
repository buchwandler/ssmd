"""Integrity checks for the normative SSMD 0.9 grammar fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import ssmd

SPEC_ROOT = Path(__file__).parents[1] / "spec"
FIXTURES = SPEC_ROOT / "fixtures"


def _load_cases(filename: str) -> list[dict[str, Any]]:
    payload = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))

    assert payload["dialect"] == "0.9"
    assert isinstance(payload["cases"], list)
    assert payload["cases"]
    return payload["cases"]


def test_valid_fixtures_have_unique_ids_and_semantic_expectations() -> None:
    cases = _load_cases("valid.json")
    ids = [case["id"] for case in cases]

    assert len(ids) == len(set(ids))
    for case in cases:
        assert isinstance(case["input"], str)
        assert case["input"]
        assert isinstance(case["expected"], dict)
        assert case["expected"]


def test_invalid_fixtures_name_expected_diagnostics() -> None:
    cases = _load_cases("invalid.json")
    ids = [case["id"] for case in cases]

    assert len(ids) == len(set(ids))
    for case in cases:
        assert isinstance(case["input"], str)
        assert case["input"]
        assert case["expected_diagnostic"].startswith(("syntax.", "header."))


def test_semantic_valid_fixtures_parse_and_preserve_values() -> None:
    for case in _load_cases("semantic_valid.json"):
        result = ssmd.parse_structure(case["input"], dialect="0.9")
        expected = case["expected"]
        assert not [item for item in result.diagnostics if item.severity == "error"], case["id"]
        assert result.clean_text == expected["clean_text"], case["id"]
        attrs = expected["attrs"]
        assert any(
            all(span.attrs.get(key) == value for key, value in attrs.items())
            for span in result.annotations
        ), case["id"]


def test_semantic_invalid_fixtures_emit_source_ranged_diagnostics() -> None:
    cases = _load_cases("semantic_invalid.json")
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))

    specification = (SPEC_ROOT.parent / "SPECIFICATION.md").read_text(encoding="utf-8")
    assert "Phase 6 reconciles" not in specification
    for case in cases:
        assert case["expected_diagnostic"] in specification, case["id"]
        result = ssmd.parse_structure(case["input"], dialect="0.9")
        diagnostic = next(
            item for item in result.diagnostics if item.code == case["expected_diagnostic"]
        )
        expected = case["expected_range"]
        expected_start = (
            case["input"].index(f'"{expected}"') + 1
            if case["range_kind"] == "value"
            else case["input"].index(expected)
        )

        assert diagnostic.severity == "error", case["id"]
        assert diagnostic.source_start == expected_start, case["id"]
        assert diagnostic.source_end == expected_start + len(expected), case["id"]
        assert diagnostic.line is not None, case["id"]
        assert diagnostic.column is not None, case["id"]


def test_normative_grammar_covers_document_inline_and_fenced_constructs() -> None:
    grammar = (SPEC_ROOT / "grammar.ebnf").read_text(encoding="utf-8")

    for production in (
        "document          =",
        "paragraph         =",
        "heading           =",
        "directive-block   =",
        "closing-fence     =",
        "annotation        =",
        "attributes        =",
        "moderate-emphasis =",
        "strong-emphasis   =",
        "reduced-emphasis  =",
        "escaped-char      =",
        "break-marker      =",
        "mark              =",
    ):
        assert production in grammar


def test_valid_fixtures_parse_with_expected_structure() -> None:
    for case in _load_cases("valid.json"):
        result = ssmd.parse_structure(case["input"], dialect="0.9")
        expected = case["expected"]
        assert not [item for item in result.diagnostics if item.severity == "error"], case["id"]
        if "clean_text" in expected:
            assert result.clean_text == expected["clean_text"], case["id"]
        for annotation in expected.get("annotations", []):
            start = result.clean_text.index(annotation["text"])
            end = start + len(annotation["text"])
            assert any(
                span.char_start <= start
                and span.char_end >= end
                and all(span.attrs.get(key) == value for key, value in annotation["attrs"].items())
                for span in result.annotations
            ), case["id"]
        if "attrs" in expected:
            assert any(
                all(span.attrs.get(key) == value for key, value in expected["attrs"].items())
                for span in result.annotations
            ), case["id"]
        for fragment in expected.get("text_fragments", []):
            assert fragment in result.clean_text, case["id"]
        for scope in expected.get("scopes", []):
            start = result.clean_text.index(scope["text"])
            end = start + len(scope["text"])
            assert all(
                any(
                    span.char_start <= start
                    and span.char_end >= end
                    and span.attrs.get(key) == value
                    for span in result.annotations
                )
                for key, value in scope["attrs"].items()
            ), case["id"]
        for key, value in expected.get("header", {}).items():
            assert result.header[key] == value, case["id"]


def test_invalid_fixtures_emit_expected_diagnostics() -> None:
    for case in _load_cases("invalid.json"):
        result = ssmd.parse_structure(case["input"], dialect="0.9")
        diagnostic = next(
            item for item in result.diagnostics if item.code == case["expected_diagnostic"]
        )
        assert diagnostic.severity == "error"
        assert diagnostic.source_start is not None
        assert diagnostic.source_end is not None
        assert diagnostic.line is not None
        assert diagnostic.column is not None


def test_parse_spans_adapts_canonical_structure() -> None:
    source = '---\nssmd_version: "0.9"\n---\n[*Hello*]{lang="en-GB"}'
    structure = ssmd.parse_structure(source)
    spans = ssmd.parse_spans(source)

    assert spans.clean_text == structure.clean_text
    assert spans.annotations == structure.annotations
    assert spans.diagnostics == structure.diagnostics
    language_span = next(span for span in spans.annotations if span.attrs.get("lang") == "en-GB")
    assert language_span.source_start == source.index("[")
    assert language_span.source_end == source.rindex("}") + 1


def test_strict_structure_parser_does_not_detect_sentences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("sentence detection was invoked")

    monkeypatch.setattr(ssmd.parser, "_split_sentences", fail)
    result = ssmd.parse_structure('---\nssmd_version: "0.9"\n---\nOne. Two.')

    assert result.clean_text == "One. Two."

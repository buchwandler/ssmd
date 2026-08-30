"""Tests for the sentence-neutral structural SSMD parser."""

from __future__ import annotations

import pytest

import ssmd


def assert_offsets(result: ssmd.ParseStructureResult) -> None:
    for span in result.annotations:
        assert 0 <= span.char_start <= span.char_end <= len(result.clean_text)
    for event in result.events:
        assert 0 <= event.pos <= len(result.clean_text)


def test_plain_text_has_no_structure() -> None:
    result = ssmd.parse_structure("Hello world.")

    assert result.clean_text == "Hello world."
    assert result.annotations == []
    assert result.events == []
    assert_offsets(result)


def test_annotation_offsets_and_metadata() -> None:
    result = ssmd.parse_structure('Hello [world]{lang="fr"}!')

    assert result.clean_text == "Hello world!"
    span = result.annotations[0]
    assert result.clean_text[span.char_start : span.char_end] == "world"
    assert span.attrs["lang"] == "fr"
    assert_offsets(result)


def test_phoneme_and_substitution_annotations() -> None:
    phoneme = ssmd.parse_structure('Say [tomato]{ph="təˈmeɪtoʊ"} now.')
    assert phoneme.clean_text == "Say tomato now."
    assert phoneme.annotations[0].attrs["ph"] == "təˈmeɪtoʊ"

    substitution = ssmd.parse_structure('Say [Prof.]{sub="Professor"} now.')
    assert substitution.clean_text == "Say Professor now."
    span = substitution.annotations[0]
    assert substitution.clean_text[span.char_start : span.char_end] == "Professor"
    assert span.attrs["sub"] == "Professor"
    assert_offsets(phoneme)
    assert_offsets(substitution)


@pytest.mark.parametrize(
    ("source", "strength"),
    [
        ("...n", "none"),
        ("...w", "x-weak"),
        ("...c", "medium"),
        ("...s", "strong"),
        ("...p", "x-strong"),
    ],
)
def test_strength_breaks_preserve_semantics(source: str, strength: str) -> None:
    result = ssmd.parse_structure(f"Hello {source} world")

    assert result.clean_text == "Hello world"
    assert result.events == [ssmd.StructuralEvent(5, "break", "after", {"strength": strength})]
    assert_offsets(result)


def test_timed_break_leading_and_trailing_boundaries() -> None:
    leading = ssmd.parse_structure("...500ms Hello")
    trailing = ssmd.parse_structure("Hello ...500ms")

    assert leading.events[0] == ssmd.StructuralEvent(0, "break", "before", {"time": "500ms"})
    assert trailing.events[0] == ssmd.StructuralEvent(
        len(trailing.clean_text), "break", "after", {"time": "500ms"}
    )
    assert_offsets(leading)
    assert_offsets(trailing)


def test_marks_and_multiple_events_preserve_source_order() -> None:
    result = ssmd.parse_structure("Hello ...500ms @chapter world")

    assert result.clean_text == "Hello world"
    assert [(event.kind, event.attrs) for event in result.events] == [
        ("break", {"time": "500ms"}),
        ("mark", {"name": "chapter"}),
    ]
    assert all(event.pos == 5 and event.anchor == "after" for event in result.events)


def test_trailing_mark_is_not_lost() -> None:
    result = ssmd.parse_structure("Hello @end")

    assert result.clean_text == "Hello"
    assert result.events == [ssmd.StructuralEvent(5, "mark", "after", {"name": "end"})]


def test_events_without_text_are_preserved_without_markup() -> None:
    result = ssmd.parse_structure("...500ms @end")

    assert result.clean_text == ""
    assert [(event.kind, event.pos) for event in result.events] == [
        ("break", 0),
        ("mark", 0),
    ]


def test_paragraph_boundary_is_structural_and_sentence_neutral() -> None:
    result = ssmd.parse_structure("First.\n\nSecond.")

    assert result.clean_text == "First.\n\nSecond."
    assert result.events == [ssmd.StructuralEvent(6, "paragraph", "after", {})]


def test_front_matter_is_returned_separately() -> None:
    result = ssmd.parse_structure(
        "---\ntitle: Test\npause_defaults:\n  sentence: 250ms\ncustom: value\n---\nHello."
    )

    assert result.header == {
        "title": "Test",
        "pause_defaults": {"sentence": "250ms"},
        "custom": "value",
    }
    assert result.clean_text == "Hello."


def test_normalization_and_preserve_whitespace_keep_event_coordinates() -> None:
    normalized = ssmd.parse_structure("Hello   ...500ms   world")
    preserved = ssmd.parse_structure("Hello   ...500ms   world", normalize=False)

    assert normalized.clean_text == "Hello world"
    assert normalized.events[0].pos == 5
    assert preserved.clean_text == "Hello      world"
    assert preserved.events[0].pos == 8
    assert_offsets(normalized)
    assert_offsets(preserved)


def test_default_language_is_an_annotation() -> None:
    result = ssmd.parse_structure("Hello", default_lang="en")

    assert result.annotations[0].attrs == {"lang": "en"}
    assert (
        result.clean_text[result.annotations[0].char_start : result.annotations[0].char_end]
        == "Hello"
    )


def test_malformed_input_preserves_warnings_and_diagnostics() -> None:
    result = ssmd.parse_structure('[test]{lang="unterminated}')

    assert result.clean_text == "test"
    assert result.warnings
    assert result.diagnostics


def test_parse_structure_does_not_invoke_sentence_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("sentence detection was invoked")

    monkeypatch.setattr(ssmd.parser, "_split_sentences", fail)
    result = ssmd.parse_structure("Prof. Klein wartet 1 Min. Danach geht er.")

    assert result.clean_text == "Prof. Klein wartet 1 Min. Danach geht er."
    assert result.events == []

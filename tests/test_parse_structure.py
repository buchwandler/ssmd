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


@pytest.mark.parametrize(
    ("line_ending", "opening_indent"),
    [("\n", ""), ("\n", "  "), ("\r\n", ""), ("\r\n", "  ")],
)
def test_tight_sibling_directives_share_a_paragraph(line_ending: str, opening_indent: str) -> None:
    source = (
        f':::{{voice="a"}}{line_ending}One.{line_ending}:::{line_ending}'
        f'{opening_indent}:::{{voice="b"}}{line_ending}Two.{line_ending}:::'
    )
    result = ssmd.parse_structure(source, dialect="0.9")

    assert result.clean_text == "One. Two."
    assert not any(event.kind == "paragraph" for event in result.events)
    voice_spans = {
        span.attrs["voice"]: result.clean_text[span.char_start : span.char_end]
        for span in result.annotations
        if "voice" in span.attrs
    }
    assert voice_spans == {"a": "One.", "b": "Two."}
    assert [span.source_start for span in result.annotations] == [
        source.index(':::{voice="a"}'),
        source.index(':::{voice="b"}'),
    ]


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_loose_sibling_directives_create_a_paragraph_boundary(line_ending: str) -> None:
    source = (
        f':::{{voice="a"}}{line_ending}One.{line_ending}:::{line_ending}{line_ending}'
        f':::{{voice="b"}}{line_ending}Two.{line_ending}:::'
    )
    result = ssmd.parse_structure(source, dialect="0.9")
    blank_line_start = source.index(line_ending * 2) + len(line_ending)

    assert result.clean_text == "One.\n\nTwo."
    paragraph_events = [event for event in result.events if event.kind == "paragraph"]
    assert paragraph_events == [
        ssmd.StructuralEvent(
            4,
            "paragraph",
            "after",
            {},
            blank_line_start,
            blank_line_start + len(line_ending),
        )
    ]
    voice_spans = {
        span.attrs["voice"]: result.clean_text[span.char_start : span.char_end]
        for span in result.annotations
        if "voice" in span.attrs
    }
    assert voice_spans == {"a": "One.", "b": "Two."}
    assert_offsets(result)


def test_tight_directives_preserve_source_whitespace_without_normalization() -> None:
    source = ':::{voice="a"}\nOne.\n:::\n:::{voice="b"}\nTwo.\n:::'
    result = ssmd.parse_structure(source, dialect="0.9", normalize=False)

    assert result.clean_text == "One.\nTwo."
    assert not any(event.kind == "paragraph" for event in result.events)
    assert_offsets(result)


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


def test_structural_parser_validates_09_front_matter_with_source_ranges() -> None:
    source = '---\nssmd_version: "0.9"\nlanguage: not a language\n---\nHello.'
    result = ssmd.parse_structure(source)
    issue = next(item for item in result.diagnostics if item.code == "language.invalid_tag")

    assert issue.severity == "error"
    assert issue.source_start == source.index("language")
    assert issue.source_end == source.index("language") + len("language")
    assert issue.line == 3
    assert issue.column == 1


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


def test_short_directive_opener_reports_its_fence_and_consumes_recovery_close() -> None:
    source = '::{voice="host"}\nHello.\n:::'
    result = ssmd.parse_structure(source, dialect="0.9")

    assert [item.code for item in result.diagnostics] == ["syntax.directive_fence_too_short"]
    diagnostic = result.diagnostics[0]
    assert diagnostic.source_start == 0
    assert diagnostic.source_end == 2
    assert diagnostic.line == 1
    assert diagnostic.column == 1
    assert "at least 3 colons" in diagnostic.message
    assert diagnostic.hint is not None
    assert "three colons" in diagnostic.hint.lower()
    assert result.clean_text == "Hello."
    assert not any("voice" in annotation.attrs for annotation in result.annotations)


def test_short_directive_recovery_preserves_nested_valid_directives() -> None:
    source = '::{voice="invalid"}\nBefore.\n::::{voice="nested"}\nInside.\n::::\nAfter.\n:::'
    result = ssmd.parse_structure(source, dialect="0.9")

    assert [item.code for item in result.diagnostics] == ["syntax.directive_fence_too_short"]
    assert "Before." in result.clean_text
    assert "Inside." in result.clean_text
    assert "After." in result.clean_text
    nested = [item for item in result.annotations if item.attrs.get("voice") == "nested"]
    assert len(nested) == 1
    assert result.clean_text[nested[0].char_start : nested[0].char_end] == "Inside."
    assert not any(item.attrs.get("voice") == "invalid" for item in result.annotations)


def test_repeated_short_directive_openers_report_each_opener_without_close_cascades() -> None:
    blocks = [f'::{{voice="speaker-{index}"}}\nLine {index}.\n:::' for index in range(27)]
    source = "\n".join(blocks)
    result = ssmd.parse_structure(source, dialect="0.9")
    diagnostics = [
        item for item in result.diagnostics if item.code == "syntax.directive_fence_too_short"
    ]

    assert len(diagnostics) == 27
    assert [item.line for item in diagnostics] == [1 + index * 3 for index in range(27)]
    assert not any(item.code == "syntax.unexpected_directive_close" for item in result.diagnostics)


@pytest.mark.parametrize("fence", [":::", "::::"])
def test_valid_directive_fence_lengths_remain_valid(fence: str) -> None:
    source = f'{fence}{{voice="host"}}\nHello.\n{fence}'
    result = ssmd.parse_structure(source, dialect="0.9")

    assert not [item for item in result.diagnostics if item.severity == "error"]
    assert any(item.attrs.get("voice") == "host" for item in result.annotations)


def test_fence_mismatch_diagnostic_keeps_its_existing_meaning() -> None:
    result = ssmd.parse_structure('::::{voice="host"}\nHello.\n:::', dialect="0.9")

    assert [item.code for item in result.diagnostics] == ["syntax.directive_fence_mismatch"]


def test_short_opener_does_not_activate_in_08_mode() -> None:
    source = '::{voice="host"}\nHello.\n:::'
    result = ssmd.parse_structure(source, dialect="0.8")

    assert not any(item.code == "syntax.directive_fence_too_short" for item in result.diagnostics)


def test_short_directive_recovery_leaves_noncanonical_close_to_ancestor() -> None:
    source = '::::{voice="outer"}\n::{voice="invalid"}\nInside.\n::::'
    result = ssmd.parse_structure(source, dialect="0.9")

    assert [item.code for item in result.diagnostics] == [
        "syntax.directive_fence_too_short",
        "syntax.unclosed_directive",
    ]
    assert result.clean_text == "Inside."
    assert not any(
        item.code in ("syntax.directive_fence_mismatch", "syntax.unexpected_directive_close")
        for item in result.diagnostics
    )
    assert any(item.attrs.get("voice") == "outer" for item in result.annotations)
    assert not any(item.attrs.get("voice") == "invalid" for item in result.annotations)

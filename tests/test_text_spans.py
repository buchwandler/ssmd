from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import ssmd


def _mapped_slices(source: str, parsed: ssmd.ParseStructureResult) -> list[tuple[str, str]]:
    assert isinstance(parsed.text_spans, tuple)
    slices: list[tuple[str, str]] = []
    for span in parsed.text_spans:
        assert 0 <= span.char_start < span.char_end <= len(parsed.clean_text)
        assert 0 <= span.source_start < span.source_end <= len(source)
        slices.append(
            (
                source[span.source_start : span.source_end],
                parsed.clean_text[span.char_start : span.char_end],
            )
        )
    return slices


def test_text_spans_map_plain_paragraph_heading_and_nested_inline_markup() -> None:
    source = "# Heading\n\nOne *nested **bold** text*."
    parsed = ssmd.parse_structure(source, dialect="0.9", normalize=False)

    assert parsed.clean_text == "Heading\n\nOne nested bold text."
    assert _mapped_slices(source, parsed) == [
        ("Heading", "Heading"),
        ("One ", "One "),
        ("nested ", "nested "),
        ("bold", "bold"),
        (" text", " text"),
        (".", "."),
    ]


def test_text_spans_cover_sub_say_as_and_phoneme_annotation_text() -> None:
    source = '[AWS]{sub="Amazon Web Services"} [date]{as="date"} [tomato]{ph="təˈmeɪtoʊ"}'
    parsed = ssmd.parse_structure(source, dialect="0.9", normalize=False)

    assert parsed.clean_text == "AWS date tomato"
    assert _mapped_slices(source, parsed) == [
        ("AWS", "AWS"),
        (" ", " "),
        ("date", "date"),
        (" ", " "),
        ("tomato", "tomato"),
    ]


def test_text_spans_retain_escaped_source_range_without_claiming_one_to_one_offsets() -> None:
    source = r"Escaped \[syntax\] and \*stars\*"
    parsed = ssmd.parse_structure(source, dialect="0.9", normalize=False)

    assert parsed.clean_text == "Escaped [syntax] and *stars*"
    assert _mapped_slices(source, parsed) == [(source, parsed.clean_text)]


def test_text_spans_keep_repeated_text_occurrences_at_distinct_source_coordinates() -> None:
    source = "same *same* same"
    parsed = ssmd.parse_structure(source, dialect="0.9", normalize=False)

    assert parsed.clean_text == "same same same"
    assert [clean for _raw, clean in _mapped_slices(source, parsed)] == [
        "same ",
        "same",
        " same",
    ]
    assert [source[start : start + 4] for start in (0, 6, 12)] == ["same"] * 3
    assert [span.source_start for span in parsed.text_spans] == [0, 6, 11]


def test_text_spans_cover_unicode_and_newline_text() -> None:
    source = "café ☯\nsecond line"
    parsed = ssmd.parse_structure(source, dialect="0.9", normalize=False)

    assert parsed.clean_text == source
    assert _mapped_slices(source, parsed) == [(source, source)]


def test_text_spans_use_original_document_coordinates_after_front_matter() -> None:
    source = '---\nssmd_version: "0.9"\n---\nIntro.'
    parsed = ssmd.parse_structure(source)

    assert parsed.clean_text == "Intro."
    span = parsed.text_spans[0]
    assert span.source_start == source.index("Intro.")
    assert source[span.source_start : span.source_end] == "Intro."


def test_text_span_is_immutable() -> None:
    parsed = ssmd.parse_structure("Hello", dialect="0.9")
    span = parsed.text_spans[0]
    assert isinstance(span, ssmd.TextSpan)

    with pytest.raises(FrozenInstanceError):
        span.char_start = 1  # type: ignore[misc]

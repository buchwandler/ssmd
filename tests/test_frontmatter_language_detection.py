"""Tests for pronunciation language scope and portable routing hints."""

import pytest

import ssmd
from ssmd.frontmatter import language_detection_hint, serialize_front_matter, validate_front_matter

PRONUNCIATION_SCOPE = 'lang="en" scope="pronunciation"'


def test_language_scope_defaults_and_is_exposed_in_spans() -> None:
    semantic = ssmd.parse_spans('[Bonjour]{lang="fr"}')
    pronunciation = ssmd.parse_spans(f"[File]{{{PRONUNCIATION_SCOPE}}}")

    assert semantic.annotations[0].language_scope == "semantic"
    assert semantic.annotations[0].is_pronunciation_language is False
    assert pronunciation.annotations[0].attrs == {
        "lang": "en",
        "scope": "pronunciation",
        "tag": "lang",
    }
    assert pronunciation.annotations[0].is_pronunciation_language is True


def test_language_alias_is_preserved_in_span_attrs_and_canonicalized_on_segment_output() -> None:
    result = ssmd.parse_spans('[File]{language="en" scope="pronunciation"}')
    segment = ssmd.parse_segments('[File]{language="en" scope="pronunciation"}')[0]

    assert result.annotations[0].attrs["language"] == "en"
    assert result.annotations[0].attrs["tag"] == "lang"
    assert segment.to_ssmd() == '[File]{lang="en" scope="pronunciation"}'


def test_invalid_language_scope_diagnostics() -> None:
    invalid = ssmd.lint('[File]{lang="en" scope="model"}')
    missing_language = ssmd.lint('[File]{scope="pronunciation"}')

    assert invalid[0].code == "annotation.language_scope_invalid"
    assert missing_language[0].code == "annotation.language_scope_without_language"


def test_pronunciation_scope_round_trips_without_changing_ssml_mapping() -> None:
    segment = ssmd.Segment(text="File", language="en", language_scope="pronunciation")

    assert segment.to_ssmd() == '[File]{lang="en" scope="pronunciation"}'
    assert '<lang xml:lang="en-US">File</lang>' in segment.to_ssml()


def test_subtoken_adjacency_and_offsets_are_exact() -> None:
    cases = (
        ("[Manpower]{" + PRONUNCIATION_SCOPE + "}diskussion", "Manpowerdiskussion", "Manpower"),
        ("ge[cancel]{" + PRONUNCIATION_SCOPE + "}t", "gecancelt", "cancel"),
        ("[download]{" + PRONUNCIATION_SCOPE + "}en", "downloaden", "download"),
    )

    for source, expected, annotated_text in cases:
        result = ssmd.parse_spans(source)
        span = result.annotations[0]
        assert result.clean_text == expected
        assert result.clean_text[span.char_start : span.char_end] == annotated_text
        assert span.attrs["scope"] == "pronunciation"


def test_normalization_still_preserves_source_whitespace_boundaries() -> None:
    assert ssmd.parse_spans(f"foo [bar]{{{PRONUNCIATION_SCOPE}}} baz").clean_text == "foo bar baz"
    assert ssmd.parse_spans("Hello   world").clean_text == "Hello world"


def test_language_detection_header_is_typed_preserved_and_excluded_from_clean_text() -> None:
    header = {"language_detection": {"mode": "auto", "languages": ["de", "en"]}}
    source = serialize_front_matter(header, "Hallo.")
    document = ssmd.Document(source)
    structure = ssmd.parse_structure(source)

    assert document.header == header
    assert document.language_detection_hint == language_detection_hint(header)
    assert structure.header == header
    assert structure.clean_text == "Hallo."
    assert document.to_ssmd(include_header=True).startswith("---\nlanguage_detection:\n")


def test_language_detection_off_may_omit_languages() -> None:
    assert validate_front_matter({"language_detection": {"mode": "off"}}) == []
    assert language_detection_hint({"language_detection": {"mode": "off"}}).mode == "off"


@pytest.mark.parametrize(
    ("header", "code"),
    [
        ({"language_detection": "auto"}, "header.language_detection_invalid"),
        ({"language_detection": {"mode": "maybe"}}, "header.language_detection_mode_invalid"),
        ({"language_detection": {"mode": "auto"}}, "header.language_detection_languages_invalid"),
        (
            {"language_detection": {"mode": "auto", "languages": "de"}},
            "header.language_detection_languages_invalid",
        ),
        (
            {"language_detection": {"mode": "auto", "languages": []}},
            "header.language_detection_languages_invalid",
        ),
    ],
)
def test_invalid_language_detection_headers_have_stable_diagnostics(header, code) -> None:
    assert validate_front_matter(header)[0].code == code


def test_unrelated_header_keys_remain_preserved() -> None:
    header = {
        "author": "Jane",
        "language_detection": {"mode": "auto", "languages": ["de", "en"]},
    }
    serialized = serialize_front_matter(header, "Text")

    parsed = ssmd.parse_front_matter(serialized)
    assert parsed.data == header
    assert any(issue.code == "header.unknown_key" for issue in validate_front_matter(header))

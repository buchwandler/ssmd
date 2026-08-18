"""Tests for parse_spans span offsets."""

import pytest

import ssmd

LEADING_DECIMAL_SOURCES = (
    "It takes .2 seconds.",
    "Wait .02 seconds.",
    "Value .125.",
)


def test_basic_phoneme_span_offsets():
    text = "Say [tomato]{ph='a'} now."
    result = ssmd.parse_spans(text)

    assert result.clean_text == "Say tomato now."
    span = result.annotations[0]
    assert span.char_start == 4
    assert span.char_end == 10
    assert span.attrs.get("ph") == "a"
    assert span.attrs.get("tag") == "phoneme"


def test_repeated_words_offsets():
    text = "[word]{lang='en'} word"
    result = ssmd.parse_spans(text)

    assert result.clean_text == "word word"
    span = result.annotations[0]
    assert span.attrs.get("tag") == "lang"
    assert result.clean_text[span.char_start : span.char_end] == "word"


def test_punctuation_adjacency_offsets():
    text = "Hello, [world]{lang='en'}!"
    result = ssmd.parse_spans(text)

    assert result.clean_text == "Hello, world!"
    span = result.annotations[0]
    assert span.attrs.get("tag") == "lang"
    assert result.clean_text[span.char_start : span.char_end] == "world"


def test_adjacent_annotations():
    text = "[hello]{lang='en'}[world]{lang='en'}"
    result = ssmd.parse_spans(text, normalize=False)

    assert result.clean_text == "helloworld"
    assert len(result.annotations) == 2
    assert result.annotations[0].attrs.get("tag") == "lang"
    assert (
        result.clean_text[result.annotations[0].char_start : result.annotations[0].char_end]
        == "hello"
    )
    assert result.annotations[1].attrs.get("tag") == "lang"
    assert (
        result.clean_text[result.annotations[1].char_start : result.annotations[1].char_end]
        == "world"
    )


def test_div_block_offsets():
    text = "<div lang='fr'>\nBonjour\n</div>"
    result = ssmd.parse_spans(text)

    assert result.clean_text == "Bonjour"
    span = next(s for s in result.annotations if s.attrs.get("lang") == "fr")
    assert span.attrs.get("tag") == "div"
    assert result.clean_text[span.char_start : span.char_end] == "Bonjour"


def test_sentence_iteration_offsets_match_clean_text():
    text = "Hello *world*. Next sentence."
    spans = ssmd.iter_sentences_spans(text, use_spacy=False)
    clean_text = ssmd.parse_spans(text).clean_text

    for sentence, start, end in spans:
        assert clean_text[start:end] == sentence


def test_sentence_iteration_repeated_sentences():
    text = "Hello. Hello."
    spans = ssmd.iter_sentences_spans(text, use_spacy=False)
    clean_text = ssmd.parse_spans(text).clean_text

    assert len(spans) == 2
    assert spans[0][0] == "Hello."
    assert spans[0][1] == 0
    assert clean_text[spans[0][1] : spans[0][2]] == "Hello."
    assert spans[1][0] == "Hello."
    assert clean_text[spans[1][1] : spans[1][2]] == "Hello."


def test_sentence_iteration_normalization_alignment():
    text = "Hello   *world*. Hello   *world*."
    spans = ssmd.iter_sentences_spans(text, use_spacy=False)
    clean_text = ssmd.parse_spans(text).clean_text

    assert clean_text == "Hello world. Hello world."
    assert len(spans) == 2
    assert spans[0][0] == "Hello world."
    assert spans[1][0] == "Hello world."
    assert clean_text[spans[0][1] : spans[0][2]] == "Hello world."
    assert clean_text[spans[1][1] : spans[1][2]] == "Hello world."


@pytest.mark.parametrize("source", LEADING_DECIMAL_SOURCES)
def test_parse_spans_preserves_leading_decimal_spacing(source):
    result = ssmd.parse_spans(source)

    assert result.clean_text == source


def test_sentence_span_offsets_with_leading_decimal():
    source = "It takes .2 seconds."

    spans = ssmd.iter_sentences_spans(source, use_spacy=False)
    clean_text = ssmd.parse_spans(source).clean_text

    assert spans == [(source, 0, len(source))]
    assert clean_text == source
    assert clean_text[: len(source)] == source


# ═══════════════════════════════════════════════════════════
# GOLDEN TESTS (Phase 1)
# ═══════════════════════════════════════════════════════════


def test_plain_001_no_markup():
    """plain_001: no markup → clean_text equals input; spans empty"""
    text = "Plain text with no markup."
    result = ssmd.parse_spans(text)

    assert result.clean_text == "Plain text with no markup."
    assert len(result.annotations) == 0
    assert len(result.warnings) == 0


def test_ssmd_ph_001_phoneme():
    """ssmd_ph_001: Hello [world]{ph=\"wɝːld\"}."""
    text = 'Hello [world]{ph="wɝːld"}.'
    result = ssmd.parse_spans(text)

    assert result.clean_text == "Hello world."
    assert len(result.annotations) == 1
    span = result.annotations[0]
    assert span.char_start == 6
    assert span.char_end == 11
    assert result.clean_text[span.char_start : span.char_end] == "world"
    assert span.attrs.get("ph") == "wɝːld"
    assert span.attrs.get("tag") == "phoneme"


def test_ssmd_lang_single_quotes_001():
    """ssmd_lang_single_quotes_001: [Bonjour]{lang='fr'} le monde."""
    text = "[Bonjour]{lang='fr'} le monde."
    result = ssmd.parse_spans(text)

    assert result.clean_text == "Bonjour le monde."
    assert len(result.annotations) == 1
    span = result.annotations[0]
    assert result.clean_text[span.char_start : span.char_end] == "Bonjour"
    assert span.attrs.get("lang") == "fr"
    assert span.attrs.get("tag") == "lang"


def test_ssmd_multi_attrs_001():
    """ssmd_multi_attrs_001: multiple attrs mixed quotes"""
    text = '[this]{lang="en" ph=\'ðɪs\' rate="0.9"}'
    result = ssmd.parse_spans(text)

    assert result.clean_text == "this"
    assert len(result.annotations) == 1
    span = result.annotations[0]
    assert result.clean_text[span.char_start : span.char_end] == "this"
    assert span.attrs.get("lang") == "en"
    assert span.attrs.get("ph") == "ðɪs"
    assert span.attrs.get("rate") == "0.9"
    # Tag should be "phoneme" because ph takes precedence
    assert span.attrs.get("tag") == "phoneme"


def test_ssmd_duplicate_words_001():
    """ssmd_duplicate_words_001: no [no]{ph='nəʊ'} no
    (verify the second occurrence is spanned correctly)"""
    text = "no [no]{ph='nəʊ'} no"
    result = ssmd.parse_spans(text)

    # With normalize=True (default), spaces are added
    assert result.clean_text == "no no no"
    assert len(result.annotations) == 1
    span = result.annotations[0]
    # The middle "no" should be spanned
    assert result.clean_text[span.char_start : span.char_end] == "no"
    assert span.attrs.get("ph") == "nəʊ"
    # Verify it's the middle occurrence (not the first or last)
    assert span.char_start == 3  # After "no "


def test_ssmd_punctuation_adjacent_001():
    """ssmd_punctuation_adjacent_001: punctuation adjacency offsets"""
    text = "Wait,[what]{ph='wʌt'}?!"
    result = ssmd.parse_spans(text, normalize=False)

    assert result.clean_text == "Wait,what?!"
    assert len(result.annotations) == 1
    span = result.annotations[0]
    assert result.clean_text[span.char_start : span.char_end] == "what"
    assert span.attrs.get("ph") == "wʌt"


def test_ssmd_div_001():
    """ssmd_div_001: <div lang=fr>Bonjour le monde</div>"""
    text = "<div lang=fr>\nBonjour le monde\n</div>"
    result = ssmd.parse_spans(text)

    assert result.clean_text == "Bonjour le monde"
    assert len(result.annotations) == 1
    span = result.annotations[0]
    assert span.kind == "div"
    assert result.clean_text[span.char_start : span.char_end] == "Bonjour le monde"
    assert span.attrs.get("lang") == "fr"
    assert span.attrs.get("tag") == "div"


# ═══════════════════════════════════════════════════════════
# ROBUSTNESS TESTS (Phase 1 - P2)
# ═══════════════════════════════════════════════════════════


def test_robustness_random_whitespace_between_attrs():
    """Random whitespace between attributes should be handled"""
    text = '[test]{lang="en"     ph=\'test\'   rate="1.0"}'
    result = ssmd.parse_spans(text)

    assert result.clean_text == "test"
    span = result.annotations[0]
    assert span.attrs.get("lang") == "en"
    assert span.attrs.get("ph") == "test"
    assert span.attrs.get("rate") == "1.0"


def test_robustness_mixed_quote_styles():
    """Mixed quote styles should work consistently"""
    # All double quotes
    result1 = ssmd.parse_spans('[test]{lang="en" ph="test"}')
    # All single quotes
    result2 = ssmd.parse_spans("[test]{lang='en' ph='test'}")
    # Mixed
    result3 = ssmd.parse_spans("[test]{lang=\"en\" ph='test'}")

    for result in [result1, result2, result3]:
        assert result.clean_text == "test"
        assert result.annotations[0].attrs.get("lang") == "en"
        assert result.annotations[0].attrs.get("ph") == "test"


def test_robustness_malformed_attrs_emit_warnings():
    """Malformed attrs should emit warnings, not crash"""
    # Unterminated quote
    result = ssmd.parse_spans('[test]{lang="unterminated}')
    assert result.clean_text == "test"
    assert len(result.warnings) > 0
    assert any("Unterminated quote" in w for w in result.warnings)

    # Invalid characters in key
    result = ssmd.parse_spans("[test]{la@ng=fr}")
    assert result.clean_text == "test"
    assert len(result.warnings) > 0


def test_robustness_unbalanced_brackets():
    """Unbalanced brackets should emit warnings"""
    result = ssmd.parse_spans("[test{lang='en'}")
    assert len(result.warnings) > 0
    assert any("Unbalanced" in w for w in result.warnings)

    result = ssmd.parse_spans("test]{lang='en'}")
    # This is treated as plain text
    assert "test]" in result.clean_text or len(result.warnings) > 0


def test_robustness_unclosed_div():
    """Unclosed div should emit warning"""
    result = ssmd.parse_spans("<div lang=fr>\nBonjour")
    assert result.clean_text.strip() == "Bonjour"
    assert len(result.warnings) > 0
    assert any("Unclosed" in w or "div" in w.lower() for w in result.warnings)


def test_robustness_unexpected_div_close():
    """Unexpected </div> should emit warning"""
    result = ssmd.parse_spans("Hello\n</div>")
    assert len(result.warnings) > 0
    assert any("div" in w.lower() for w in result.warnings)


def test_robustness_empty_annotation():
    """Empty annotation brackets should be handled"""
    result = ssmd.parse_spans("[]{lang='en'}")
    assert result.clean_text == ""
    # Should still create a span for the empty text
    if result.annotations:
        assert result.annotations[0].attrs.get("lang") == "en"


def test_robustness_nested_divs():
    """Nested divs should work correctly"""
    text = """<div lang=en>
<div rate=fast>
Fast English text
</div>
</div>"""
    result = ssmd.parse_spans(text)
    assert "Fast English text" in result.clean_text
    # Should have annotations for both divs
    assert len(result.annotations) >= 1


def test_robustness_special_chars_in_values():
    """Special characters in attribute values should be preserved"""
    result = ssmd.parse_spans('[test]{ph="tɛst"}')
    assert result.annotations[0].attrs.get("ph") == "tɛst"

    # Unicode
    result = ssmd.parse_spans('[test]{text="你好"}')
    assert result.annotations[0].attrs.get("text") == "你好"


def test_robustness_very_long_value():
    """Very long attribute values should be handled"""
    long_value = "a" * 1000
    result = ssmd.parse_spans(f'[test]{{text="{long_value}"}}')
    assert result.annotations[0].attrs.get("text") == long_value

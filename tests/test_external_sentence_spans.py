"""Tests for externally supplied sentence boundaries."""

from dataclasses import dataclass

import ssmd


@dataclass(frozen=True)
class FakeSentenceSpan:
    char_start: int
    char_end: int


def test_external_spans_render_without_sentence_detection(monkeypatch):
    source = 'Hello *world*. Next [part]{lang="fr"}.'
    parsed = ssmd.parse_spans(source)
    spans = [FakeSentenceSpan(0, 12), FakeSentenceSpan(13, len(parsed.clean_text))]

    def fail_sentence_detection(*args: object, **kwargs: object) -> object:
        raise AssertionError("external sentence spans must not invoke sentence detection")

    monkeypatch.setattr(ssmd.parser, "_split_sentences", fail_sentence_detection)
    result = ssmd.to_ssml(source, sentence_spans=spans)

    assert result == (
        "<speak><p><s>Hello <emphasis>world</emphasis>.</s> "
        '<s>Next <lang xml:lang="fr-FR">part</lang>.</s></p></speak>'
    )


def test_document_external_spans_accept_iterable_tuples():
    source = "First. Second."
    result = ssmd.Document(source).to_ssml(sentence_spans=((0, 6), (7, len(source))))

    assert result == "<speak><p><s>First.</s> <s>Second.</s></p></speak>"


def test_parse_spans_reports_structure_without_normalization_or_language_inference():
    result = ssmd.parse_spans('German [Hello 2]{lang="en-US"} text')

    assert result.clean_text == "German Hello 2 text"
    assert len(result.annotations) == 1
    annotation = result.annotations[0]
    assert annotation.attrs["lang"] == "en-US"
    assert result.clean_text[annotation.char_start : annotation.char_end] == "Hello 2"


def test_phoneme_annotation_exposes_external_protection_range():
    result = ssmd.parse_spans('Say [XYZ]{ph="ɛks w aɪ z iː"} now.')

    annotation = result.annotations[0]
    assert annotation.attrs["tag"] == "phoneme"
    assert result.clean_text[annotation.char_start : annotation.char_end] == "XYZ"
    assert annotation.char_start == 4
    assert annotation.char_end == 7

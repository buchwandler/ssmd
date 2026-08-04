"""Tests for SSMD's phrasplit 0.3.4 model-selection boundary."""

import phrasplit
import pytest

from ssmd.document import Document
from ssmd.parser import parse_paragraphs, parse_sentences


def _fake_resolution(*, language: str, model: str | None, size: str | None):
    selected = model or "en_core_web_lg"
    return phrasplit.SpacyModelResolution(
        language=language,
        model=selected,
        model_size="lg",
        requested_model=model,
        requested_size=size,
        candidates=(selected,),
        attempts=(phrasplit.SpacyModelAttempt(selected, True),),
        available=True,
        loadable=True,
        diagnostics=("selected fake model",),
    )


def _patch_phrasplit(monkeypatch: pytest.MonkeyPatch):
    resolver_calls: list[dict[str, object]] = []
    splitter_calls: list[dict[str, object]] = []

    def resolve_spacy_model(**kwargs):
        resolver_calls.append(kwargs)
        return _fake_resolution(
            language=kwargs["language"],
            model=kwargs.get("model"),
            size=kwargs.get("size"),
        )

    def split_text(text: str, **kwargs):
        splitter_calls.append(kwargs)
        return [phrasplit.Segment(text=text, paragraph=0, sentence=0)]

    monkeypatch.setattr(phrasplit, "resolve_spacy_model", resolve_spacy_model)
    monkeypatch.setattr(phrasplit, "split_text", split_text)
    return resolver_calls, splitter_calls


def test_unset_model_and_size_delegate_language_and_automatic_selection(monkeypatch):
    resolver_calls, splitter_calls = _patch_phrasplit(monkeypatch)

    paragraphs = parse_paragraphs("Hallo.", language="de")

    assert resolver_calls[0] == {
        "language": "de",
        "model": None,
        "size": None,
        "require": False,
    }
    assert splitter_calls[0]["language"] == "de"
    assert splitter_calls[0]["language_model"] is None
    assert splitter_calls[0]["model_size"] is None
    assert paragraphs.diagnostics.selection_mode == "automatic"
    assert paragraphs.diagnostics.effective_language == "de"
    assert paragraphs.diagnostics.selected_model == "en_core_web_lg"


def test_exact_model_is_forwarded_unchanged_and_wins_over_size(monkeypatch):
    resolver_calls, splitter_calls = _patch_phrasplit(monkeypatch)

    with pytest.warns(UserWarning, match="model_size is ignored"):
        sentences = parse_sentences(
            "Hello.",
            language="en-US",
            spacy_model="custom_exact_model",
            model_size="sm",
        )

    assert resolver_calls[0]["model"] == "custom_exact_model"
    assert resolver_calls[0]["size"] is None
    assert splitter_calls[0]["language_model"] == "custom_exact_model"
    assert splitter_calls[0]["model_size"] == "sm"
    assert sentences.diagnostics.selection_mode == "explicit_model"
    assert sentences.diagnostics.selected_model == "custom_exact_model"


def test_exact_size_is_forwarded_without_local_package_construction(monkeypatch):
    resolver_calls, splitter_calls = _patch_phrasplit(monkeypatch)

    parse_sentences("Hello.", language="en", model_size="lg")

    assert resolver_calls[0]["model"] is None
    assert resolver_calls[0]["size"] == "lg"
    assert splitter_calls[0]["language_model"] is None
    assert splitter_calls[0]["model_size"] == "lg"


def test_regex_mode_skips_resolution_and_notes_ignored_model_fields(monkeypatch):
    _, splitter_calls = _patch_phrasplit(monkeypatch)

    def fail_resolution(**kwargs):
        raise AssertionError("regex mode must not resolve a spaCy model")

    monkeypatch.setattr(phrasplit, "resolve_spacy_model", fail_resolution)
    with pytest.warns(UserWarning, match="ignored when use_spacy=False"):
        result = parse_sentences(
            "Hello.",
            use_spacy=False,
            spacy_model="en_core_web_sm",
            model_size="sm",
        )

    assert splitter_calls[0]["use_spacy"] is False
    assert result.diagnostics.selection_mode == "regex"
    assert result.diagnostics.selected_model is None


def test_document_uses_one_exact_configuration_for_sentence_and_paragraph_paths(monkeypatch):
    _, splitter_calls = _patch_phrasplit(monkeypatch)
    document = Document(
        "Hello.",
        config={
            "sentence_spacy_model": "en_core_web_sm",
            "sentence_model_size": "lg",
            "sentence_use_spacy": None,
        },
    )

    config = document._sentence_detection_config()
    document._parse_sentence_objects()
    document._parse_paragraph_objects()

    assert config.spacy_model == "en_core_web_sm"
    assert config.model_size == "lg"
    assert all(call["language_model"] == "en_core_web_sm" for call in splitter_calls)
    assert all(call["model_size"] == "lg" for call in splitter_calls)
    assert document.sentence_detection_diagnostics.selected_model == "en_core_web_sm"

"""Tests for SSMD's phrasplit 0.3.5 detailed split boundary."""

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
    splitter_calls: list[dict[str, object]] = []

    def split_text_with_diagnostics(text: str, **kwargs):
        splitter_calls.append(kwargs)
        language = phrasplit.normalize_spacy_language(kwargs["language"])
        use_spacy = kwargs.get("use_spacy") is not False
        resolution = _fake_resolution(
            language=language,
            model=kwargs.get("language_model"),
            size=kwargs.get("model_size"),
        )
        diagnostics = phrasplit.SplitDiagnostics(
            backend="spacy" if use_spacy else "regex",
            language=language,
            resolution=resolution if use_spacy else None,
        )
        return phrasplit.SplitTextResult(
            segments=[phrasplit.Segment(text=text, paragraph=0, sentence=0)],
            diagnostics=diagnostics,
        )

    monkeypatch.setattr(phrasplit, "split_text_with_diagnostics", split_text_with_diagnostics)
    return splitter_calls


def test_unset_model_and_size_delegate_language_and_automatic_selection(monkeypatch):
    splitter_calls = _patch_phrasplit(monkeypatch)

    paragraphs = parse_paragraphs("Hallo.", language="de")

    assert splitter_calls[0]["language"] == "de"
    assert splitter_calls[0]["language_model"] is None
    assert splitter_calls[0]["model_size"] is None
    assert paragraphs.diagnostics.selection_mode == "automatic"
    assert paragraphs.diagnostics.effective_language == "de"
    assert paragraphs.diagnostics.selected_model == "en_core_web_lg"


def test_exact_model_is_forwarded_unchanged_and_wins_over_size(monkeypatch):
    splitter_calls = _patch_phrasplit(monkeypatch)

    with pytest.warns(UserWarning, match="model_size is ignored"):
        sentences = parse_sentences(
            "Hello.",
            language="en-US",
            spacy_model="custom_exact_model",
            model_size="sm",
        )

    assert splitter_calls[0]["language"] == "en-US"
    assert splitter_calls[0]["language_model"] == "custom_exact_model"
    assert splitter_calls[0]["model_size"] is None
    assert sentences.diagnostics.selection_mode == "explicit_model"
    assert sentences.diagnostics.selected_model == "custom_exact_model"


def test_exact_size_is_forwarded_without_local_package_construction(monkeypatch):
    splitter_calls = _patch_phrasplit(monkeypatch)

    parse_sentences("Hello.", language="en", model_size="lg")

    assert splitter_calls[0]["language_model"] is None
    assert splitter_calls[0]["model_size"] == "lg"


def test_ssmd_uses_one_phrasplit_detailed_split(monkeypatch):
    splitter_calls = _patch_phrasplit(monkeypatch)

    def fail_resolution(**kwargs):
        raise AssertionError("SSMD must not pre-resolve; phrasplit split result owns diagnostics")

    monkeypatch.setattr(phrasplit, "resolve_spacy_model", fail_resolution)
    result = parse_sentences("Hello.")

    assert len(splitter_calls) == 1
    assert result.diagnostics.selection_mode == "automatic"
    assert result.diagnostics.selected_model == "en_core_web_lg"


def test_regex_mode_skips_resolution_and_notes_ignored_model_fields(monkeypatch):
    splitter_calls = _patch_phrasplit(monkeypatch)

    def fail_resolution(**kwargs):
        raise AssertionError("regex mode must not resolve a spaCy model")

    monkeypatch.setattr(phrasplit, "resolve_spacy_model", fail_resolution)
    with pytest.warns(UserWarning, match="ignored when use_spacy=False") as caught:
        result = parse_sentences(
            "Hello.",
            use_spacy=False,
            spacy_model="en_core_web_sm",
            model_size="sm",
        )

    assert len(caught) == 1
    assert splitter_calls[0]["use_spacy"] is False
    assert result.diagnostics.selection_mode == "regex"
    assert result.diagnostics.selected_model is None


def test_document_uses_one_exact_configuration_for_sentence_and_paragraph_paths(monkeypatch):
    splitter_calls = _patch_phrasplit(monkeypatch)
    document = Document(
        "Hello.",
        config={
            "sentence_spacy_model": "en_core_web_sm",
            "sentence_model_size": "lg",
            "sentence_use_spacy": None,
        },
    )

    config = document._sentence_detection_config()
    with pytest.warns(
        UserWarning,
        match="model_size is ignored when an explicit model is supplied",
    ) as caught:
        document._parse_sentence_objects()
        document._parse_paragraph_objects()

    assert len(caught) == 2
    assert config.spacy_model == "en_core_web_sm"
    assert config.model_size == "lg"
    assert all(call["language_model"] == "en_core_web_sm" for call in splitter_calls)
    assert all(call["model_size"] is None for call in splitter_calls)
    assert document.sentence_detection_diagnostics.selected_model == "en_core_web_sm"


@pytest.mark.parametrize(
    ("spacy_model", "model_size"),
    [
        ("en_core_web_sm", None),
        (None, "sm"),
        ("en_core_web_sm", "sm"),
    ],
)
def test_regex_warning_matrix_emits_only_regex_warning(monkeypatch, spacy_model, model_size):
    _patch_phrasplit(monkeypatch)
    with pytest.warns(UserWarning, match="ignored when use_spacy=False") as caught:
        parse_sentences(
            "Hello.",
            use_spacy=False,
            spacy_model=spacy_model,
            model_size=model_size,
        )

    assert len(caught) == 1

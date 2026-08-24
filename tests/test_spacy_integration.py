"""Focused end-to-end tests for the optional real spaCy backend."""

import pytest

from ssmd.document import Document
from ssmd.parser import parse_sentences

pytestmark = pytest.mark.spacy


@pytest.fixture(scope="module")
def english_model() -> str:
    """Require the official English small model for integration tests."""
    spacy = pytest.importorskip("spacy")
    try:
        spacy.load("en_core_web_sm")
    except OSError as exc:
        pytest.skip(f"en_core_web_sm is not loadable: {exc}")
    return "en_core_web_sm"


def test_automatic_installed_english_model_selection(english_model):
    result = parse_sentences("Hello world.")

    assert result.diagnostics.selection_mode == "automatic"
    assert result.diagnostics.selected_model is not None
    assert result.diagnostics.selected_model.startswith("en_core_web_")


def test_forced_spacy_uses_installed_model(english_model):
    result = parse_sentences("Hello world. This is a test.", use_spacy=True)

    assert len(result) == 2
    assert result.diagnostics.selected_model is not None


def test_explicit_model_is_selected(english_model):
    result = parse_sentences("Hello world.", spacy_model=english_model)

    assert result.diagnostics.selection_mode == "explicit_model"
    assert result.diagnostics.selected_model == english_model


def test_selected_model_diagnostics_include_effective_size(english_model):
    result = parse_sentences("Hello world.", spacy_model=english_model)

    assert result.diagnostics.selected_model_size == "sm"
    assert result.diagnostics.effective_language == "en"


def test_spacy_handles_abbreviation_sentence_boundary(english_model):
    result = parse_sentences(
        "Dr. Smith met Mr. Johnson at the U.S. Embassy.",
        spacy_model=english_model,
    )

    assert len(result) == 1


def test_document_spacy_integration_path(english_model):
    document = Document(
        "Hello world. This is a test.",
        config={
            "sentence_spacy_model": english_model,
            "sentence_use_spacy": True,
        },
    )

    sentences = document._parse_sentence_objects()

    assert len(sentences) == 2
    assert document.sentence_detection_diagnostics.selected_model == english_model

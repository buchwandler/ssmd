"""Shared pytest fixtures for deterministic sentence-backend tests."""

from __future__ import annotations

import phrasplit
import pytest


def _no_model_resolution(**kwargs):
    """Return a deterministic no-model result for generic unit tests."""
    language = phrasplit.normalize_spacy_language(kwargs.get("language"))
    return phrasplit.SpacyModelResolution(
        language=language,
        model=None,
        model_size=None,
        requested_model=kwargs.get("model"),
        requested_size=kwargs.get("size"),
        candidates=(),
        attempts=(),
        available=False,
        loadable=False,
        diagnostics=("unit test forced regex backend",),
    )


@pytest.fixture(autouse=True)
def deterministic_sentence_backend(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    """Keep generic tests on phrasplit's real regex implementation."""
    if request.node.get_closest_marker("spacy") is not None:
        return

    monkeypatch.setattr(phrasplit, "resolve_spacy_model", _no_model_resolution)
    monkeypatch.setattr(phrasplit.splitter, "resolve_spacy_model", _no_model_resolution)

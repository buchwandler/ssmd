"""Characterization tests for the unversioned SSMD 0.8 compatibility syntax."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ssmd
from ssmd.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_08_div_voice_directive_remains_structural() -> None:
    source = '<div voice="moderator">\nFirst sentence. Second sentence.\n</div>'

    result = ssmd.parse_structure(source)

    assert result.clean_text == "First sentence. Second sentence."
    assert len(result.annotations) == 1
    assert result.annotations[0].attrs == {"voice": "moderator", "tag": "div"}


def test_08_underscore_and_symbolic_prosody_remain_supported() -> None:
    source = "_soft_ ++loud++ >>fast>> ^^high^^"

    result = ssmd.to_ssml(source)

    assert '<emphasis level="reduced">soft</emphasis>' in result
    assert '<prosody volume="x-loud">loud</prosody>' in result
    assert '<prosody rate="x-fast">fast</prosody>' in result
    assert '<prosody pitch="x-high">high</prosody>' in result


def test_08_comma_separator_recovers_with_warning() -> None:
    result = ssmd.parse_spans('[Hello]{voice="Joanna", v="4" r="3"}')

    assert result.annotations[0].attrs["voice"] == "Joanna"
    assert result.annotations[0].attrs["v"] == "4"
    assert result.annotations[0].attrs["r"] == "3"
    assert any("Unexpected character ','" in warning for warning in result.warnings)


def test_08_duplicate_attributes_use_last_value() -> None:
    result = ssmd.parse_structure('[Bonjour]{lang="en" lang="fr"}')

    assert result.annotations[0].attrs["lang"] == "fr"
    assert result.warnings == []


def test_08_language_without_region_expands_during_generic_rendering() -> None:
    assert '<lang xml:lang="fr-FR">Bonjour</lang>' in ssmd.to_ssml('[Bonjour]{lang="fr"}')


def test_08_named_voice_discards_other_voice_features() -> None:
    source = '[Hello]{voice="Joanna" voice-lang="en-US" gender="female" variant="2"}'

    result = ssmd.to_ssml(source)

    assert '<voice name="Joanna">Hello</voice>' in result
    assert 'language="' not in result
    assert 'gender="' not in result
    assert 'variant="' not in result


def test_08_fenced_directive_is_literal_in_unversioned_input() -> None:
    source = ':::{lang="en"}\nHello.\n:::'

    assert ":::" in ssmd.parse_spans(source).clean_text
    assert "<lang" not in ssmd.to_ssml(source)


@pytest.mark.xfail(
    strict=True,
    reason="SSML round-trip expands one multi-sentence voice directive into per-sentence annotations.",
)
def test_08_multisentence_voice_roundtrip_preserves_one_scope() -> None:
    source = '<div voice="moderator">\nSentence one. Sentence two. Sentence three.\n</div>'
    roundtripped = ssmd.from_ssml(ssmd.to_ssml(source))
    structure = ssmd.parse_structure(roundtripped)

    assert len(structure.annotations) == 1
    assert structure.annotations[0].char_start == 0
    assert structure.annotations[0].char_end == len(structure.clean_text)
    assert structure.annotations[0].attrs["voice"] == "moderator"


def test_08_cli_version_json_snapshot(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--json", "version"])

    assert code in (None, 0)
    actual = json.loads(capsys.readouterr().out)
    expected = json.loads((FIXTURES / "cli_version_08.json").read_text(encoding="utf-8"))

    assert actual["schema"] == "ssmd.cli.v1"
    assert actual["result"]["version"] == ssmd.__version__
    snapshot = {
        **actual,
        "result": {**actual["result"], "version": "<ssmd.__version__>"},
    }
    assert {key: value for key, value in snapshot.items() if key != "schema"} == expected

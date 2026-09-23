from __future__ import annotations

import json

import pytest

import ssmd
from ssmd import SSMLConversionError, SSMLParser, parse_structure
from ssmd.cli import main


def test_from_ssml_returns_a_versioned_document_and_preserves_voice_scope() -> None:
    ssml = '<speak><voice name="Narrator"><s>Hello.</s><s>Goodbye.</s></voice></speak>'

    source = ssmd.from_ssml(ssml)
    structure = parse_structure(source)
    rendered = ssmd.to_ssml(source)

    assert structure.header["ssmd_version"] == "0.9"
    assert not [item for item in structure.diagnostics if item.severity == "error"]
    assert 'voice name="Narrator"' in rendered
    assert "Hello." in rendered and "Goodbye." in rendered


def test_voice_selectors_and_audio_repeat_count_round_trip() -> None:
    ssml = (
        '<speak><voice name="Speaker" language="en-GB" gender="female" '
        'age="30" variant="2"><audio src="clip.wav" repeatCount="2">Clip</audio>'
        "</voice></speak>"
    )

    source = ssmd.from_ssml(ssml)
    structure = parse_structure(source)
    rendered = ssmd.to_ssml(source)

    assert 'repeat="2"' in source
    assert 'voice-name="Speaker"' in source
    assert not [item for item in structure.diagnostics if item.severity == "error"]
    assert (
        '<voice name="Speaker" languages="en-GB" gender="female" age="30" variant="2">' in rendered
    )
    assert '<audio src="clip.wav" repeatCount="2">Clip</audio>' in rendered


def test_reduced_emphasis_converts_to_canonical_09_and_round_trips() -> None:
    source = ssmd.from_ssml('<speak><emphasis level="reduced">quiet</emphasis></speak>')

    assert "~~quiet~~" in source
    assert "syntax.legacy_reduced_emphasis" not in {
        item.code for item in parse_structure(source).diagnostics
    }
    assert '<emphasis level="reduced">quiet</emphasis>' in ssmd.to_ssml(source)


def test_from_ssml_can_return_a_fragment_explicitly() -> None:
    source = ssmd.from_ssml("<speak>Hello.</speak>", complete_document=False)

    assert source == "Hello.\n"
    assert not source.startswith("---")


def test_unknown_ssml_semantics_error_by_default() -> None:
    source = (
        '<speak><v:express-as xmlns:v="https://example.test" style="happy">'
        "Hello</v:express-as></speak>"
    )

    with pytest.raises(SSMLConversionError) as error:
        ssmd.from_ssml(source)

    diagnostic = error.value.diagnostics[0]
    assert diagnostic.code == "conversion.unsupported_ssml_element"
    assert diagnostic.severity == "error"


def test_unknown_ssml_loss_policies_report_distinct_severities() -> None:
    source = (
        '<speak><v:express-as xmlns:v="https://example.test" style="happy">'
        "Hello</v:express-as></speak>"
    )

    for policy, severity in (("warn", "warning"), ("drop", "info")):
        parser = SSMLParser({"loss_policy": policy})
        assert parser.to_ssmd(source) == "Hello\n"
        assert [item.severity for item in parser.diagnostics] == [severity]


def test_from_ssml_cli_outputs_versioned_document_or_explicit_fragment(tmp_path, capsys) -> None:
    path = tmp_path / "source.ssml"
    path.write_text("<speak>Hello.</speak>", encoding="utf-8")

    assert main(["from-ssml", str(path)]) == 0
    complete = capsys.readouterr().out
    assert parse_structure(complete).header["ssmd_version"] == "0.9"

    assert main(["from-ssml", str(path), "--fragment"]) == 0
    fragment = capsys.readouterr().out
    assert fragment == "Hello.\n"


def test_from_ssml_cli_warns_on_loss_without_polluting_conversion_stdout(tmp_path, capsys) -> None:
    path = tmp_path / "source.ssml"
    path.write_text(
        '<speak><v:express-as xmlns:v="https://example.test" style="happy">'
        "Hello</v:express-as></speak>",
        encoding="utf-8",
    )

    assert main(["from-ssml", str(path), "--loss-policy", "warn"]) == 0
    captured = capsys.readouterr()

    assert "ssmd_version" in captured.out
    assert "Unsupported SSML element" in captured.err
    assert "warning:" in captured.err


def test_from_ssml_cli_json_includes_loss_diagnostic(tmp_path, capsys) -> None:
    path = tmp_path / "source.ssml"
    path.write_text(
        '<speak><v:express-as xmlns:v="https://example.test" style="happy">'
        "Hello</v:express-as></speak>",
        encoding="utf-8",
    )

    assert main(["--json", "from-ssml", str(path), "--loss-policy", "warn"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["result"]["diagnostics"][0]["severity"] == "warning"

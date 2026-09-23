"""Tests for inspect metadata output."""

import json

from ssmd.cli import main


def test_inspect_voices_and_header(tmp_path, capsys):
    path = tmp_path / "doc.ssmd"
    path.write_text(
        '---\nvoice_bindings:\n  kokoro:\n    moderator: af_sarah\n---\n<div voice="moderator">\nHello.\n</div>\n',
        encoding="utf-8",
    )
    assert main(["--json", "inspect", str(path), "--header", "--voices"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["result"]["data"]["header_present"] is True
    assert data["result"]["data"]["references"][0]["reference"] == "moderator"


def test_inspect_sentences_shows_declared_effective_prosody(tmp_path, capsys):
    path = tmp_path / "doc.ssmd"
    path.write_text(
        "---\nvoice_defaults:\n  guest:\n    pitch: high\n---\n"
        '<div voice="guest" rate="slow">\nHello.\n</div>\n',
        encoding="utf-8",
    )
    assert main(["--json", "inspect", str(path), "--sentences"]) == 0
    data = json.loads(capsys.readouterr().out)
    sentence = data["result"]["data"][0]
    assert sentence["declared_prosody"]["pitch"] is None
    assert sentence["effective_prosody"]["pitch"] == "high"
    assert sentence["sources"]["pitch"] == "voice_default"

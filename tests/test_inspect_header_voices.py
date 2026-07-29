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

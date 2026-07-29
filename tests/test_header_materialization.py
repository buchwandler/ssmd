"""Tests for create-time header materialization."""

import json

from ssmd.cli import main


def test_create_materializes_only_used_voice_binding(tmp_path, capsys):
    config = tmp_path / "config.yaml"
    source = tmp_path / "draft.ssmd"
    output = tmp_path / "review.ssmd"
    source.write_text('<div voice="moderator">\nHello.\n</div>\n', encoding="utf-8")
    assert main(["--config", str(config), "config", "init"]) == 0
    capsys.readouterr()
    assert main(["--config", str(config), "voices", "add", "kokoro", "af_sarah"]) == 0
    capsys.readouterr()
    assert main(["--config", str(config), "voices", "bind", "kokoro", "moderator", "af_sarah"]) == 0
    capsys.readouterr()
    assert (
        main(
            ["--config", str(config), "config", "set", "authoring.default_voice_provider", "kokoro"]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        main(
            [
                "--json",
                "--config",
                str(config),
                "create",
                str(source),
                "-o",
                str(output),
                "--no-roundtrip",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["result"]["header_materialized"] is True
    content = output.read_text(encoding="utf-8")
    assert "moderator: af_sarah" in content
    assert "Hello." in content

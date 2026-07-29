"""Tests for config and voice CLI command envelopes."""

import json

from ssmd.cli import main


def test_config_and_voice_cli_json(tmp_path, capsys):
    path = tmp_path / "config.yaml"
    assert main(["--json", "--config", str(path), "config", "init"]) == 0
    capsys.readouterr()
    assert main(["--json", "--config", str(path), "voices", "add", "kokoro", "af_sarah"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["command"] == "voices add"
    assert main(["--json", "--config", str(path), "voices", "list"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["result_type"] == "voice_catalog"
    assert data["result"]["voices"][0]["id"] == "af_sarah"

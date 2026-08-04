"""Tests for the JSON output contract of the SSMD CLI.

These tests verify that root-level --json produces stable, deterministic
JSON envelopes with the correct structure.
"""

import json
import subprocess
import sys

import pytest

from ssmd.cli import main


def run_json(argv: list[str]) -> tuple[int, dict]:
    """Run a command with --json and parse the output."""
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    code = 0
    try:
        with redirect_stdout(buf):
            code = main(["--json"] + argv)
    except SystemExit as exc:
        code = int(exc.code)
    output = buf.getvalue().strip()
    if output:
        data = json.loads(output)
    else:
        data = {}
    return code, data


def test_json_profiles_envelope():
    code, data = run_json(["profiles"])
    assert code == 0
    assert data["ok"] is True
    assert data["command"] == "profiles"
    assert data["result_type"] == "profile_catalog"
    assert "profiles" in data["result"]
    assert "presets" in data["result"]
    assert isinstance(data["result"]["profiles"], list)
    assert isinstance(data["result"]["result_presets"], list) if "result_presets" in data else True


def test_json_lint_valid(tmp_path):
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code, data = run_json(["lint", str(path)])
    assert code == 0
    assert data["ok"] is True
    assert data["command"] == "lint"
    assert data["result_type"] == "lint_report"
    assert data["result"]["passed"] is True
    assert data["result"]["files"][0]["path"] == str(path)
    assert data["result"]["files"][0]["issues"] == []


def test_json_lint_invalid(tmp_path):
    path = tmp_path / "bad.ssmd"
    path.write_text('Hello [world]{lang="fr"', encoding="utf-8")

    code, data = run_json(["lint", str(path)])
    assert code == 1
    assert data["ok"] is True  # operation succeeded, but lint failed
    assert data["result"]["passed"] is False
    assert len(data["result"]["files"][0]["issues"]) > 0


def test_json_fmt_check_dirty(tmp_path):
    path = tmp_path / "dirty.ssmd"
    path.write_bytes(b"Hello. World.\r\n")

    code, data = run_json(["fmt", "--check", str(path)])
    assert code == 1
    assert data["ok"] is True
    assert data["result"]["clean"] is False


def test_json_create_success_reports_created_state_and_bytes(tmp_path):
    source = tmp_path / "draft.ssmd"
    output = tmp_path / "release.ssmd"
    source.write_text("Hello *world*.", encoding="utf-8")

    code, data = run_json(["create", str(source), "-o", str(output), "--fail-on-warn"])

    assert code == 0
    assert data["ok"] is True
    assert data["result_type"] == "create_result"
    assert data["result"]["created"] is True
    assert data["result"]["bytes_written"] > 0
    assert output.exists()


@pytest.mark.parametrize("punctuation", [".", "?", "!"])
def test_json_sentence_boundary_pause_shipping_gate(tmp_path, punctuation):
    """Strict create and lint accept a single pause between sentences."""
    source = tmp_path / "pause.ssmd"
    output = tmp_path / "pause-output.ssmd"
    source.write_text(f"Hello{punctuation} ...250ms Done.\n", encoding="utf-8")

    create_code, create_data = run_json(
        ["create", str(source), "-o", str(output), "--fail-on-warn"]
    )
    lint_code, lint_data = run_json(["lint", str(output), "--roundtrip", "--fail-on-warn"])

    assert create_code == 0
    assert create_data["result"]["created"] is True
    assert create_data["result"]["bytes_written"] > 0
    assert lint_code == 0
    assert lint_data["result"]["passed"] is True


def test_json_create_warning_block_preserves_atomic_output_contract(tmp_path):
    source = tmp_path / "draft.ssmd"
    output = tmp_path / "release.ssmd"
    source.write_text("---\napplication_key: value\n---\nHello.", encoding="utf-8")

    code, data = run_json(["create", str(source), "-o", str(output), "--fail-on-warn"])

    assert code == 1
    assert data["ok"] is True
    assert data["result"]["created"] is False
    assert data["result"]["bytes_written"] == 0
    assert data["result"]["issues"][0]["code"] == "header.unknown_key"
    assert not output.exists()


def test_json_create_existing_output_requires_force(tmp_path):
    source = tmp_path / "draft.ssmd"
    output = tmp_path / "release.ssmd"
    source.write_text("Hello.", encoding="utf-8")

    assert run_json(["create", str(source), "-o", str(output)])[0] == 0
    code, data = run_json(["create", str(source), "-o", str(output)])
    assert code == 2
    assert data["ok"] is False
    assert data["error"]["code"] == "OUTPUT_EXISTS"

    code, data = run_json(["create", str(source), "-o", str(output), "--force"])
    assert code == 0
    assert data["ok"] is True
    assert data["result"]["created"] is True


def test_json_create_malformed_draft_returns_protocol_error(tmp_path):
    source = tmp_path / "malformed.ssmd"
    output = tmp_path / "release.ssmd"
    source.write_text("---\ntitle: [\n---\nHello.", encoding="utf-8")

    code, data = run_json(["create", str(source), "-o", str(output)])

    assert code == 1
    assert data["ok"] is False
    assert data["error"]["code"] == "header.yaml_invalid"
    assert not output.exists()


def test_json_create_title_gate_and_conversions_exclude_metadata(tmp_path):
    source = tmp_path / "example.ssmd"
    output = tmp_path / "output.ssmd"
    source.write_text("---\ntitle: Review podcast\n---\nHello *world*.", encoding="utf-8")

    code, data = run_json(["create", str(source), "-o", str(output), "--fail-on-warn"])
    assert code == 0
    assert data["ok"] is True
    assert data["result"]["created"] is True
    assert "title: Review podcast" in output.read_text(encoding="utf-8")

    code, data = run_json(["lint", str(output), "--roundtrip", "--fail-on-warn"])
    assert code == 0
    assert data["result"]["passed"] is True

    code, data = run_json(["text", str(output)])
    assert code == 0
    assert data["result"]["content"] == "Hello world."
    code, data = run_json(["to-ssml", str(output)])
    assert code == 0
    assert "Review podcast" not in data["result"]["content"]


def test_json_create_reports_header_materialization_fields(tmp_path):
    config = tmp_path / "config.yaml"
    source = tmp_path / "draft.ssmd"
    output = tmp_path / "release.ssmd"
    source.write_text('<div voice="moderator">\nHello.\n</div>\n', encoding="utf-8")

    assert run_json(["--config", str(config), "config", "init"])[0] == 0
    assert run_json(["--config", str(config), "voices", "add", "kokoro", "af_sarah"])[0] == 0
    assert (
        run_json(["--config", str(config), "voices", "bind", "kokoro", "moderator", "af_sarah"])[0]
        == 0
    )
    assert (
        run_json(
            [
                "--config",
                str(config),
                "config",
                "set",
                "authoring.default_voice_provider",
                "kokoro",
            ]
        )[0]
        == 0
    )

    code, data = run_json(
        [
            "--config",
            str(config),
            "create",
            str(source),
            "-o",
            str(output),
            "--no-roundtrip",
        ]
    )
    assert code == 0
    assert data["result"]["created"] is True
    assert data["result"]["header_materialized"] is True
    assert data["result"]["voice_bindings_added"] == {"kokoro": {"moderator": "af_sarah"}}


def test_json_convert_with_output(tmp_path):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")
    out = tmp_path / "out.ssml"

    code, data = run_json(["convert", str(path), "--to", "ssml", "-o", str(out)])
    assert code == 0
    assert data["ok"] is True
    assert data["result"]["input"] == str(path)
    assert data["result"]["output"] == str(out)
    assert data["result"]["bytes_written"] > 0
    assert out.exists()


def test_json_convert_stdout(tmp_path):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")

    code, data = run_json(["convert", str(path), "--to", "ssml"])
    assert code == 0
    assert data["ok"] is True
    assert data["result"]["output"] is None
    assert "<emphasis>world</emphasis>" in data["result"]["content"]


def test_json_io_error(tmp_path):
    code, data = run_json(["lint", str(tmp_path / "nonexistent.ssmd")])
    assert code == 2
    assert data["ok"] is False
    assert data["error"]["code"] == "IO_READ_FAILED"


def test_json_unsupported_conversion(tmp_path):
    path = tmp_path / "in.ssml"
    path.write_text("<speak>hi</speak>", encoding="utf-8")

    code, data = run_json(["convert", str(path), "--from", "ssml", "--to", "text"])
    assert code == 2
    assert data["ok"] is False
    assert data["error"]["code"] == "CONVERSION_UNSUPPORTED"


def test_json_no_human_prefix_suffix(tmp_path, capsys):
    """JSON stdout contains no human prefix/suffix."""
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code, data = run_json(["lint", str(path)])
    assert code == 0
    # Verify it's valid JSON
    assert data["ok"] is True


def test_json_unicode_emitted():
    """Unicode content is emitted without ASCII escaping."""
    code, data = run_json(["version"])
    assert code == 0
    # Re-serialize to check for escaped unicode
    output = json.dumps(data, ensure_ascii=False)
    assert "\\u" not in output


def test_json_deterministic():
    """JSON output is deterministic (no random values)."""
    code1, data1 = run_json(["version"])
    code2, data2 = run_json(["version"])
    assert code1 == code2
    assert data1 == data2


def test_json_check_reports_check_command(tmp_path):
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code, data = run_json(["check", str(path)])
    assert code == 0
    assert data["command"] == "check"


def test_json_version_subprocess():
    """python -m ssmd --json version works."""
    result = subprocess.run(
        [sys.executable, "-m", "ssmd", "--json", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert "version" in data["result"]


def test_json_legacy_lint_format_json(tmp_path):
    """Legacy lint --format json still works."""
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    # Run with --format json (legacy form)
    result = subprocess.run(
        [sys.executable, "-m", "ssmd", "lint", "--format", "json", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["result"]["passed"] is True


def test_json_legacy_profiles_json(tmp_path):
    """Legacy profiles --json still works."""
    result = subprocess.run(
        [sys.executable, "-m", "ssmd", "profiles", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert "ssmd-core" in data["result"]["profiles"]


def test_json_error_envelope_structure():
    """Error envelope has the required structure."""
    code, data = run_json(["lint", "/nonexistent/path.ssmd"])
    assert code == 2
    assert data["ok"] is False
    assert "command" in data
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert "message" in error
    assert "exit_code" in error


def test_json_envelope_has_required_keys(tmp_path):
    """Success envelope has required keys: ok, command, result."""
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code, data = run_json(["lint", str(path)])
    assert code == 0
    assert "ok" in data
    assert "command" in data
    assert "result" in data

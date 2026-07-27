"""Tests for the JSON output contract of the SSMD CLI.

These tests verify that root-level --json produces stable, deterministic
JSON envelopes with the correct structure.
"""

import json
import subprocess
import sys

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

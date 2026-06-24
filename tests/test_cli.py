"""Tests for the ssmd command-line interface."""

import json
import subprocess
import sys

from ssmd.cli import main


def run(argv: list[str]) -> int:
    return main(argv)


# ── version ──────────────────────────────────────────────────────────────


def test_version_subcommand(capsys):
    code = run(["version"])
    assert code == 0
    out = capsys.readouterr().out
    assert out.startswith("ssmd ")


def test_version_flag_exits_zero():
    import pytest

    with pytest.raises(SystemExit) as excinfo:
        run(["--version"])
    assert excinfo.value.code == 0


def test_python_m_ssmd_version():
    """`python -m ssmd --version` works via the __main__ entry."""
    result = subprocess.run(
        [sys.executable, "-m", "ssmd", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("ssmd ")


# ── lint / check ─────────────────────────────────────────────────────────


def test_lint_ok(tmp_path, capsys):
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code = run(["lint", str(path)])

    assert code == 0
    assert f"{path}: ok" in capsys.readouterr().out


def test_check_is_alias_for_lint(tmp_path, capsys):
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code = run(["check", str(path)])

    assert code == 0
    assert f"{path}: ok" in capsys.readouterr().out


def test_lint_quiet_prints_nothing_on_success(tmp_path, capsys):
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code = run(["lint", "--quiet", str(path)])

    assert code == 0
    assert capsys.readouterr().out == ""


def test_lint_warn_fail_on_warn(tmp_path, capsys):
    # Emphasis is unsupported by the ssmd-core profile -> warning.
    path = tmp_path / "warn.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")

    code = run(["lint", "--fail-on-warn", str(path)])

    assert code == 1
    assert "warn" in capsys.readouterr().out


def test_lint_warn_without_fail_on_warn_is_ok(tmp_path, capsys):
    path = tmp_path / "warn.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")

    code = run(["lint", str(path)])

    assert code == 0


def test_lint_json_valid(tmp_path, capsys):
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code = run(["lint", "--format", "json", str(path)])

    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert data["files"][0]["path"] == str(path)
    assert data["files"][0]["issues"] == []


def test_lint_json_nonzero(tmp_path, capsys):
    path = tmp_path / "warn.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")

    code = run(["lint", "--format", "json", "--fail-on-warn", str(path)])

    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False
    assert data["files"][0]["issues"][0]["severity"] == "warn"
    assert data["files"][0]["issues"][0]["coordinate_system"] == "clean_text"


def test_lint_unknown_profile(tmp_path, capsys):
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code = run(["lint", "--profile", "does-not-exist", str(path)])

    assert code == 2
    assert "error" in capsys.readouterr().err


def test_lint_missing_file(tmp_path, capsys):
    code = run(["lint", str(tmp_path / "nope.ssmd")])
    assert code == 2


def test_lint_multiple_files(tmp_path, capsys):
    ok = tmp_path / "ok.ssmd"
    ok.write_text("Hello world!", encoding="utf-8")
    warn = tmp_path / "warn.ssmd"
    warn.write_text("Hello *world*!", encoding="utf-8")

    code = run(["lint", str(ok), str(warn)])

    assert code == 0  # warnings are not errors
    out = capsys.readouterr().out
    assert f"{ok}: ok" in out
    assert "warn" in out


# ── convert / to-ssml / from-ssml / text ─────────────────────────────────


def test_to_ssml_stdout(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")

    code = run(["to-ssml", str(path)])

    assert code == 0
    assert "<emphasis>world</emphasis>" in capsys.readouterr().out


def test_to_ssml_output_file(tmp_path):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")
    out = tmp_path / "out.ssml"

    code = run(["to-ssml", str(path), "-o", str(out)])

    assert code == 0
    assert "<speak" in out.read_text(encoding="utf-8")


def test_convert_infer_format(tmp_path, capsys):
    path = tmp_path / "story.md"
    path.write_text("Hello *world*!", encoding="utf-8")

    code = run(["convert", str(path), "--to", "ssml"])

    assert code == 0
    assert "<emphasis>world</emphasis>" in capsys.readouterr().out


def test_from_ssml(tmp_path, capsys):
    path = tmp_path / "in.ssml"
    path.write_text("<speak><emphasis>Hello</emphasis></speak>", encoding="utf-8")

    code = run(["from-ssml", str(path)])

    assert code == 0
    assert "*Hello*" in capsys.readouterr().out


def test_convert_ssml_to_ssmd_explicit_from(tmp_path, capsys):
    path = tmp_path / "in.xml"
    path.write_text("<speak><emphasis>Hello</emphasis></speak>", encoding="utf-8")

    code = run(["convert", str(path), "--from", "ssml", "--to", "ssmd"])

    assert code == 0
    assert "*Hello*" in capsys.readouterr().out


def test_convert_to_text(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")

    code = run(["convert", str(path), "--to", "text"])

    assert code == 0
    out = capsys.readouterr().out
    assert "world" in out
    assert "*" not in out


def test_text_command_strips_markup(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")

    code = run(["text", str(path)])

    assert code == 0
    assert capsys.readouterr().out.strip() == "Hello world!"


def test_convert_same_format_is_passthrough(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code = run(["convert", str(path), "--from", "ssmd", "--to", "ssmd"])

    assert code == 0
    assert capsys.readouterr().out.strip() == "Hello world!"


def test_convert_stdin_requires_from(capsys):

    saved = sys.stdin
    sys.stdin = _FakeStdin("Hello *world*!")
    try:
        code = run(["convert", "-", "--to", "ssml"])
    finally:
        sys.stdin = saved
    assert code == 2
    assert "--from is required" in capsys.readouterr().err


def test_convert_stdin_with_from(capsys):
    saved = sys.stdin
    sys.stdin = _FakeStdin("Hello *world*!")
    try:
        code = run(["convert", "-", "--from", "ssmd", "--to", "ssml"])
    finally:
        sys.stdin = saved
    assert code == 0
    assert "<emphasis>world</emphasis>" in capsys.readouterr().out


def test_convert_unsupported_combo(tmp_path):
    path = tmp_path / "in.ssml"
    path.write_text("<speak>hi</speak>", encoding="utf-8")

    code = run(["convert", str(path), "--from", "ssml", "--to", "text"])

    assert code == 2


# ── fmt ──────────────────────────────────────────────────────────────────


def test_fmt_stdout(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code = run(["fmt", str(path)])

    assert code == 0
    assert capsys.readouterr().out.strip() == "Hello world!"


def test_fmt_check_clean(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code = run(["fmt", "--check", str(path)])

    assert code == 0


def test_fmt_check_dirty(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello. World.", encoding="utf-8")

    code = run(["fmt", "--check", str(path)])

    assert code == 1
    assert "would reformat" in capsys.readouterr().out


def test_fmt_write(tmp_path):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello. World.", encoding="utf-8")

    code = run(["fmt", "--write", str(path)])

    assert code == 0
    assert path.read_text(encoding="utf-8").splitlines() == ["Hello.", "World."]


def test_fmt_multiple_files_require_write_or_check(tmp_path):
    one = tmp_path / "a.ssmd"
    one.write_text("Hello world!", encoding="utf-8")
    two = tmp_path / "b.ssmd"
    two.write_text("Bye world!", encoding="utf-8")

    code = run(["fmt", str(one), str(two)])

    assert code == 2


# ── profiles / inspect ───────────────────────────────────────────────────


def test_profiles_text(tmp_path, capsys):
    code = run(["profiles"])

    assert code == 0
    out = capsys.readouterr().out
    assert "Lint profiles:" in out
    assert "ssmd-core" in out
    assert "Capability presets:" in out
    assert "pyttsx3" in out


def test_profiles_json(tmp_path, capsys):
    code = run(["profiles", "--json"])

    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert "ssmd-core" in data["profiles"]
    assert "pyttsx3" in data["presets"]


def test_inspect_spans(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")

    code = run(["inspect", "--spans", str(path)])

    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["clean_text"] == "Hello world!"
    assert any(a["attrs"].get("tag") == "emphasis" for a in data["annotations"])


def test_inspect_sentences(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello. World.", encoding="utf-8")

    code = run(["inspect", "--sentences", str(path)])

    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2


# ── helpers ──────────────────────────────────────────────────────────────


class _FakeStdin:
    def __init__(self, text: str):
        self._text = text

    def read(self) -> str:
        return self._text

"""Tests for the ssmd command-line interface."""

import json
import subprocess
import sys

from ssmd.cli import main
from ssmd.spans import LintIssue


def run(argv: list[str]) -> int:
    return main(argv)


# ── version ──────────────────────────────────────────────────────────────


def test_version_subcommand(capsys):
    code = run(["version"])
    assert code == 0
    out = capsys.readouterr().out
    assert "ssmd " in out


def test_version_flag_exits_zero(capsys):
    # --version with root callback returns normally (not SystemExit)
    code = run(["--version"])
    assert code == 0
    out = capsys.readouterr().out
    assert "ssmd " in out


def test_python_m_ssmd_version():
    """`python -m ssmd --version` works via the __main__ entry."""
    result = subprocess.run(
        [sys.executable, "-m", "ssmd", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "ssmd " in result.stdout


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
    out = capsys.readouterr().out
    assert out == ""


def test_lint_malformed_fails_by_default(tmp_path, capsys):
    path = tmp_path / "warn.ssmd"
    path.write_text('Hello [world]{lang="fr"', encoding="utf-8")

    code = run(["lint", str(path)])

    assert code == 1
    output = capsys.readouterr().out
    assert "error [syntax.unbalanced_braces]" in output
    assert "line 1, column" in output


def test_lint_advisory_warning_requires_fail_on_warn(tmp_path, capsys, monkeypatch):
    path = tmp_path / "warn.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")
    monkeypatch.setattr(
        "ssmd.cli.ssmd.lint",
        lambda text, profile: [LintIssue("warn", "advisory", code="capability.warning")],
    )

    code = run(["lint", str(path)])

    assert code == 0
    assert "warn [capability.warning]" in capsys.readouterr().out

    code = run(["lint", "--fail-on-warn", str(path)])
    assert code == 1


def test_lint_json_valid(tmp_path, capsys):
    path = tmp_path / "ok.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    code = run(["lint", "--format", "json", str(path)])

    assert code == 0
    data = json.loads(capsys.readouterr().out)
    # Legacy format json returns envelope
    assert data["ok"] is True
    assert data["result"]["passed"] is True
    assert data["result"]["files"][0]["path"] == str(path)
    assert data["result"]["files"][0]["issues"] == []


def test_lint_json_nonzero(tmp_path, capsys):
    path = tmp_path / "warn.ssmd"
    path.write_text('Hello [world]{lang="fr"', encoding="utf-8")

    code = run(["lint", "--format", "json", str(path)])

    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True  # operation succeeded, but lint failed
    assert data["result"]["passed"] is False
    issue = data["result"]["files"][0]["issues"][0]
    assert issue["severity"] == "error"
    assert issue["code"] == "syntax.unbalanced_braces"
    assert issue["line"] == 1
    assert issue["column"] is not None


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
    warn.write_text('Hello [world]{lang="fr"', encoding="utf-8")

    code = run(["lint", str(ok), str(warn)])

    assert code == 1
    out = capsys.readouterr().out
    assert f"{ok}: ok" in out
    assert "error [syntax.unbalanced_braces]" in out


def test_lint_roundtrip_detects_semantic_loss(tmp_path, capsys, monkeypatch):
    path = tmp_path / "lossy.ssmd"
    path.write_text("Hello world!", encoding="utf-8")
    monkeypatch.setattr("ssmd.cli.ssmd.from_ssml", lambda text, capabilities=None: "Goodbye")

    code = run(["lint", "--roundtrip", str(path)])

    assert code == 1
    assert "error [roundtrip.semantic_loss]" in capsys.readouterr().out


def test_lint_roundtrip_capability_loss_is_explicit_warning(tmp_path, capsys, monkeypatch):
    path = tmp_path / "lossy.ssmd"
    path.write_text("Hello world!", encoding="utf-8")
    monkeypatch.setattr("ssmd.cli.ssmd.from_ssml", lambda text, capabilities=None: "Goodbye")

    code = run(["lint", "--roundtrip", "--capabilities", "minimal", str(path)])

    assert code == 0
    assert "warn [roundtrip.lossy_capability]" in capsys.readouterr().out


def test_lint_roundtrip_accepts_equivalent_voice_directives(tmp_path, capsys):
    path = tmp_path / "voices.ssmd"
    path.write_text(
        """<div voice="moderator">
Welcome. This remains one voice block.
</div>
""",
        encoding="utf-8",
    )

    code = run(["lint", "--roundtrip", str(path)])

    assert code == 0
    assert f"{path}: ok" in capsys.readouterr().out


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
    path.write_bytes(b"Hello. World.\r\n")

    code = run(["fmt", "--check", str(path)])

    assert code == 1
    assert "would reformat" in capsys.readouterr().out


def test_fmt_write(tmp_path):
    path = tmp_path / "in.ssmd"
    path.write_bytes(b"Hello. World.\r\n")

    code = run(["fmt", "--write", str(path)])

    assert code == 0
    assert path.read_bytes() == b"Hello. World.\n"


def test_fmt_write_preserves_permissions(tmp_path):
    path = tmp_path / "in.ssmd"
    path.write_bytes(b"Hello\r\n")
    path.chmod(0o640)
    expected_mode = path.stat().st_mode & 0o777

    code = run(["fmt", "--write", str(path)])

    assert code == 0
    assert path.stat().st_mode & 0o777 == expected_mode


def test_fmt_preserves_heading_and_front_matter(tmp_path):
    path = tmp_path / "in.ssmd"
    source = "---\ntitle: Example\n---\n\n# Heading\n\nBody."
    path.write_text(source, encoding="utf-8")

    code = run(["fmt", "--write", str(path)])

    assert code == 0
    assert path.read_text(encoding="utf-8") == source


def test_fmt_rejects_stdin_with_write(capsys):
    code = run(["fmt", "-", "--write"])

    assert code == 2
    assert "stdin cannot be used with --write" in capsys.readouterr().err


def test_fmt_refuses_malformed_input(tmp_path, capsys):
    path = tmp_path / "bad.ssmd"
    path.write_text('Hello [world]{lang="fr"', encoding="utf-8")

    code = run(["fmt", "--check", str(path)])

    assert code == 1
    assert "syntax.unbalanced_braces" in capsys.readouterr().out


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
    # Legacy format returns envelope
    assert "ssmd-core" in data["result"]["profiles"]
    assert "pyttsx3" in data["result"]["presets"]


def test_inspect_spans(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello *world*!", encoding="utf-8")

    # In human mode, inspect outputs formatted JSON text
    code = run(["inspect", "--spans", str(path)])
    assert code == 0
    out = capsys.readouterr().out
    # Human mode outputs formatted text
    assert "Hello world!" in out


def test_inspect_sentences(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello world!\n\nSecond paragraph.", encoding="utf-8")

    # In human mode, inspect outputs formatted text
    code = run(["inspect", "--sentences", str(path)])
    assert code == 0
    out = capsys.readouterr().out
    # Human mode outputs formatted text
    assert "Hello world!" in out


def test_inspect_paragraphs(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello world!\n\nSecond paragraph.", encoding="utf-8")

    # In human mode, inspect outputs formatted text
    code = run(["inspect", "--paragraphs", str(path)])
    assert code == 0
    out = capsys.readouterr().out
    # Human mode outputs formatted text
    assert "Hello world!" in out


def test_inspect_default_is_paragraphs(tmp_path, capsys):
    path = tmp_path / "in.ssmd"
    path.write_text("Hello world!", encoding="utf-8")

    # In human mode, inspect outputs formatted text
    code = run(["inspect", str(path)])
    assert code == 0
    out = capsys.readouterr().out
    # Human mode outputs formatted text
    assert "Hello world!" in out


# ── create ───────────────────────────────────────────────────────────────


def test_create_basic(tmp_path, capsys):
    src = tmp_path / "draft.ssmd"
    src.write_text("# Example\n\nHello *world*!", encoding="utf-8")
    out = tmp_path / "episode.ssmd"

    code = run(["create", str(src), "-o", str(out)])

    assert code == 0
    assert out.exists()
    assert "Hello *world*!" in out.read_text(encoding="utf-8")
    assert "created" in capsys.readouterr().out


def test_create_refuses_existing_output(tmp_path, capsys):
    src = tmp_path / "draft.ssmd"
    src.write_text("Hello!", encoding="utf-8")
    out = tmp_path / "episode.ssmd"
    out.write_text("existing", encoding="utf-8")

    code = run(["create", str(src), "-o", str(out)])

    assert code == 2
    assert "already exists" in capsys.readouterr().err


def test_create_force_replaces_existing(tmp_path, capsys):
    src = tmp_path / "draft.ssmd"
    src.write_text("Hello!", encoding="utf-8")
    out = tmp_path / "episode.ssmd"
    out.write_text("old", encoding="utf-8")

    code = run(["create", str(src), "-o", str(out), "--force"])

    assert code == 0
    assert "Hello!" in out.read_text(encoding="utf-8")


def test_create_validation_failure_no_write(tmp_path, capsys):
    src = tmp_path / "draft.ssmd"
    src.write_text('Hello [world]{lang="fr"', encoding="utf-8")
    out = tmp_path / "episode.ssmd"

    code = run(["create", str(src), "-o", str(out)])

    assert code == 1
    assert not out.exists()
    captured = capsys.readouterr()
    assert "error" in captured.err or "Validation failed" in captured.err


def test_create_fail_on_warn(tmp_path, capsys, monkeypatch):
    src = tmp_path / "draft.ssmd"
    src.write_text("Hello *world*!", encoding="utf-8")
    out = tmp_path / "episode.ssmd"
    monkeypatch.setattr(
        "ssmd.cli.ssmd.lint",
        lambda text, profile: [LintIssue("warn", "advisory", code="capability.warning")],
    )

    code = run(["create", str(src), "-o", str(out), "--fail-on-warn"])

    assert code == 1
    assert not out.exists()


def test_create_stdin(tmp_path, capsys):
    out = tmp_path / "episode.ssmd"
    saved = sys.stdin
    sys.stdin = _FakeStdin("# Example\n\nHello *world*!")
    try:
        code = run(["create", "-", "-o", str(out)])
    finally:
        sys.stdin = saved

    assert code == 0
    assert out.exists()


# ── helpers ──────────────────────────────────────────────────────────────


class _FakeStdin:
    """Minimal stdin replacement for tests that need to supply input."""

    def __init__(self, text: str) -> None:
        self._text = text

    def read(self) -> str:
        return self._text

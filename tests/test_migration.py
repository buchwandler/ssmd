"""Tests for verified legacy SSMD migration."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

import ssmd.migration as migration_module
from ssmd.migration import migrate_file, migrate_ssmd
from ssmd.parser import parse_structure


def test_migrate_legacy_div_to_fenced_directive_with_equivalence() -> None:
    source = '<div voice="moderator">\nHello *world*.\n</div>'

    result = migrate_ssmd(source)

    assert result.success
    assert result.content is not None
    assert "ssmd_version: '0.9'" in result.content
    assert ':::{voice="moderator"}' in result.content
    assert "Hello *world*." in result.content
    before = parse_structure(source, dialect="0.8")
    after = parse_structure(result.content, dialect="0.9")
    assert after.clean_text == before.clean_text
    voice_spans = [span for span in after.annotations if span.attrs.get("voice")]
    assert [(span.attrs["voice"], span.char_start, span.char_end) for span in voice_spans] == [
        ("moderator", 0, 12)
    ]
    assert [(event.pos, event.kind, event.attrs) for event in after.events] == [
        (event.pos, event.kind, event.attrs) for event in before.events
    ]


def test_migrate_canonicalizes_inline_aliases() -> None:
    result = migrate_ssmd('[Bonjour]{voice-lang="fr-FR" gender="female"}')

    assert result.success
    assert result.content is not None
    assert 'voice-languages="fr-FR"' in result.content
    assert "voice-lang=" not in result.content
    assert 'gender="female"' in result.content


def test_migrate_preserves_breaks_marks_and_heading_semantics() -> None:
    source = "# Heading\n\nHello ...s world @mark"

    result = migrate_ssmd(source)

    assert result.success
    assert result.content is not None
    before = parse_structure(source, dialect="0.8")
    after = parse_structure(result.content, dialect="0.9")
    assert after.clean_text == before.clean_text
    assert [(event.pos, event.kind, event.attrs) for event in after.events] == [
        (event.pos, event.kind, event.attrs) for event in before.events
    ]


def test_migrate_refuses_ambiguous_audio_alt_text() -> None:
    source = 'Audio [fallback]{src="clip.wav" alt="description"}'

    result = migrate_ssmd(source)

    assert not result.success
    assert result.content is None
    assert result.manual_actions
    assert result.diagnostics[0].code == "migration.manual_action_required"


def test_migrate_refuses_portable_extension_handlers() -> None:
    source = "---\nextensions:\n  custom: '<x>{text}</x>'\n---\nHello."

    result = migrate_ssmd(source)

    assert not result.success
    assert result.content is None
    assert "trusted configuration" in result.manual_actions[0]


def test_migrate_existing_09_is_idempotent() -> None:
    initial = migrate_ssmd("Hello world!")
    assert initial.content is not None

    repeated = migrate_ssmd(initial.content)

    assert repeated.success
    assert repeated.content == initial.content


def test_migrate_file_atomically_preserves_mode(tmp_path: Path) -> None:
    path = tmp_path / "legacy.ssmd"
    path.write_text('<div voice="guide">\nHello.\n</div>', encoding="utf-8")
    path.chmod(0o640)

    result = migrate_file(path)

    assert result.success
    assert result.written
    assert path.stat().st_mode & 0o777 == 0o640
    assert "ssmd_version: '0.9'" in path.read_text(encoding="utf-8")
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_migrate_file_does_not_write_when_manual_action_is_required(tmp_path: Path) -> None:
    path = tmp_path / "unsafe.ssmd"
    original = "---\nextensions: {}\n---\nHello."
    path.write_text(original, encoding="utf-8")

    result = migrate_file(path)

    assert not result.success
    assert not result.written
    assert path.read_text(encoding="utf-8") == original


def test_migrate_file_write_failure_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "legacy.ssmd"
    original = '<div voice="guide">\nHello.\n</div>'
    path.write_text(original, encoding="utf-8")

    def fail_replace(_source: str, _destination: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(migration_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        migrate_file(path)

    assert path.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob(".legacy.ssmd.*")) == []


def test_migrate_file_refuses_existing_output_without_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "legacy.ssmd"
    output = tmp_path / "out.ssmd"
    source.write_text("Hello.", encoding="utf-8")
    output.write_text("Keep this.", encoding="utf-8")

    result = migrate_file(source, output)

    assert not result.success
    assert result.diagnostics[0].code == "migration.output_exists"
    assert output.read_text(encoding="utf-8") == "Keep this."

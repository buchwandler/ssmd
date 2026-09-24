"""Tests for verified legacy SSMD migration."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

import ssmd.migration as migration_module
from ssmd.formatter import FormatError
from ssmd.migration import migrate_file, migrate_ssmd
from ssmd.parser import parse_structure
from ssmd.spans import Diagnostic


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
    expected_mode = stat.S_IMODE(path.stat().st_mode)

    result = migrate_file(path)

    assert result.success
    assert result.written
    assert stat.S_IMODE(path.stat().st_mode) == expected_mode
    assert "ssmd_version: '0.9'" in path.read_text(encoding="utf-8")


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


def _assert_migration_preserves_structure(source: str):
    result = migrate_ssmd(source)
    assert result.success, result.diagnostics
    assert result.content is not None
    assert "ssmd_version: '0.9'" in result.content
    assert "<div" not in result.content

    before = parse_structure(source, dialect="0.8")
    after = parse_structure(result.content, dialect="0.9")
    assert not [item for item in after.diagnostics if item.severity == "error"]
    assert after.clean_text == before.clean_text
    assert [(event.pos, event.kind, event.attrs) for event in after.events] == [
        (event.pos, event.kind, event.attrs) for event in before.events
    ]

    for event in after.events:
        if event.kind != "paragraph":
            continue
        separator_end = event.pos
        while separator_end < len(after.clean_text) and after.clean_text[separator_end] == "\n":
            separator_end += 1
        for annotation in after.annotations:
            if annotation.kind == "directive":
                continue
            assert annotation.char_end <= event.pos or annotation.char_start >= separator_end

    repeated = migrate_ssmd(result.content)
    assert repeated.success
    assert repeated.content == result.content
    return before, after


def test_printer_story_migrates_to_fenced_blocks_golden() -> None:
    fixtures = Path(__file__).parent / "fixtures" / "migration"
    legacy = (fixtures / "printer_08.ssmd").read_text(encoding="utf-8")
    expected = (fixtures / "printer_09_expected.ssmd.md").read_text(encoding="utf-8")
    result = migrate_ssmd(legacy)

    assert result.success
    assert result.content is not None
    assert result.content == expected
    assert "<div" not in result.content
    assert ":::{voice=" in result.content
    assert "\n:::\n:::" in result.content
    assert "\n\nThe printer immediately woke up." in result.content
    before = parse_structure(legacy, dialect="0.8")
    after = parse_structure(result.content, dialect="0.9")

    assert before.clean_text == after.clean_text
    assert [(event.pos, event.kind, event.attrs) for event in before.events] == [
        (event.pos, event.kind, event.attrs) for event in after.events
    ]
    assert sum(event.kind == "paragraph" for event in after.events) == 1
    assert migration_module._semantic_signature(legacy, "0.8") == (
        migration_module._semantic_signature(result.content, "0.9")
    )
    assert [event.attrs["time"] for event in after.events if event.kind == "break"] == [
        "700ms",
        "600ms",
        "650ms",
    ]
    assert before.header["pause_defaults"] == after.header["pause_defaults"]
    assert migration_module.format_canonical(result.content) == result.content
    repeated = migrate_ssmd(result.content)
    assert repeated.success
    assert repeated.content == result.content


@pytest.mark.parametrize(
    ("source", "expected_voice_text"),
    [
        (
            """\
<div voice="a">
One.
</div>

<div voice="b">
Two.

Three.
</div>
""",
            {"a": ["One."], "b": ["Two.\n\nThree."]},
        ),
        (
            """\
<div voice="a">
One.

Two.
</div>

<div voice="b">
Three.
</div>
""",
            {"a": ["One.\n\nTwo."], "b": ["Three."]},
        ),
    ],
)
def test_migrate_sibling_divs_crossing_paragraph_boundaries(
    source: str, expected_voice_text: dict[str, list[str]]
) -> None:
    _, after = _assert_migration_preserves_structure(source)
    voice_text: dict[str, list[str]] = {}
    for annotation in after.annotations:
        voice = annotation.attrs.get("voice")
        if voice is not None:
            voice_text.setdefault(voice, []).append(
                after.clean_text[annotation.char_start : annotation.char_end].strip()
            )
    assert voice_text == expected_voice_text
    assert sum(event.kind == "paragraph" for event in after.events) == 1


def test_migrate_block_aligned_sibling_divs_to_tight_directives() -> None:
    source = '<div voice="a">\nOne.\n</div>\n\n<div voice="b">\nTwo.\n</div>'
    result = migrate_ssmd(source)

    assert result.success
    assert result.content is not None
    assert ':::{voice="a"}\nOne.\n:::\n:::{voice="b"}\nTwo.\n:::' in result.content
    assert "[One.]" not in result.content
    assert "<div" not in result.content


def test_migrate_mixed_unscoped_flow_keeps_inline_voice_fallback() -> None:
    source = 'Intro text\n<div voice="guest">\nquoted voice\n</div>\noutro text'
    result = migrate_ssmd(source)

    assert result.success
    assert result.content is not None
    assert 'voice="guest"' in result.content
    assert 'Intro text [quoted voice]{voice="guest"} outro text' in result.content
    assert "[" in result.content
    assert ':::{voice="guest"}' not in result.content


def test_migrate_paragraph_crossing_voice_preserves_nested_emphasis() -> None:
    source = """\
<div voice="narrator">
One **important** thing.

Second paragraph.
</div>

<div voice="guest">
Final.
</div>
"""
    _, after = _assert_migration_preserves_structure(source)

    narrator_text = [
        after.clean_text[annotation.char_start : annotation.char_end].strip()
        for annotation in after.annotations
        if annotation.attrs.get("voice") == "narrator"
    ]
    emphasis_text = [
        after.clean_text[annotation.char_start : annotation.char_end].strip()
        for annotation in after.annotations
        if annotation.attrs.get("tag") == "emphasis"
    ]
    assert narrator_text == ["One important thing.\n\nSecond paragraph."]
    assert emphasis_text == ["important"]


def test_migrate_nested_annotations_at_paragraph_boundary() -> None:
    source = """\
<div voice="narrator">
Before [ending]{lang="en"}

[starting]{lang="fr"} after.
</div>

<div voice="other">
Done.
</div>
"""
    _, after = _assert_migration_preserves_structure(source)

    language_text = [
        (
            annotation.attrs["lang"],
            after.clean_text[annotation.char_start : annotation.char_end].strip(),
        )
        for annotation in after.annotations
        if "lang" in annotation.attrs
    ]
    assert language_text == [("en", "ending"), ("fr", "starting")]


def test_migrate_paragraph_scopes_preserves_pause_defaults() -> None:
    source = """\
---
pause_defaults:
  enabled: true
  paragraph: 450ms
  voice_change: 200ms
---
<div voice="a">
One.

Two.
</div>

<div voice="b">
Three.
</div>
"""
    before, after = _assert_migration_preserves_structure(source)

    assert before.header["pause_defaults"] == {
        "enabled": True,
        "paragraph": "450ms",
        "voice_change": "200ms",
    }
    assert after.header["pause_defaults"] == before.header["pause_defaults"]
    assert sum(event.kind == "paragraph" for event in after.events) == 1


def test_migrate_narrator_excerpt_preserves_timed_break_and_paragraph() -> None:
    source = """\
<div voice="speaker">
Earlier.
</div>

<div voice="narrator">
Daniel stared at it.
Then at the parcel.
Then back at the printer. ...650ms
He picked up a pen and wrote the address by hand.

The printer immediately woke up.
</div>
"""
    before, after = _assert_migration_preserves_structure(source)

    assert [event.attrs["time"] for event in before.events if event.kind == "break"] == ["650ms"]
    assert [event.attrs["time"] for event in after.events if event.kind == "break"] == ["650ms"]
    assert sum(event.kind == "paragraph" for event in before.events) == 1
    assert sum(event.kind == "paragraph" for event in after.events) == 1


def test_migrate_reports_invalid_legacy_source_separately() -> None:
    result = migrate_ssmd('<div voice="a">\nUnclosed.')

    assert not result.success
    assert result.diagnostics[0].code == "migration.source_invalid"
    assert result.diagnostics[0].source_start is not None
    assert result.manual_actions


def test_migrate_reports_generated_candidate_error_without_source_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_format(_text: str) -> str:
        raise FormatError(
            (
                Diagnostic(
                    code="syntax.unclosed_annotation",
                    severity="error",
                    message="Generated annotation is unclosed.",
                    source_start=15,
                ),
            )
        )

    monkeypatch.setattr(migration_module, "format_canonical", fail_format)
    result = migrate_ssmd("One.")

    assert not result.success
    assert result.diagnostics[0].code == "migration.generated_invalid"
    assert result.diagnostics[0].source_start is None
    assert "generated" in result.diagnostics[0].message.lower()
    assert not result.manual_actions


def test_migrate_preserves_break_at_adjacent_voice_boundary() -> None:
    source = """\
<div voice="a">
Hello ...600ms
</div>

<div voice="b">
World.
</div>
"""
    before, after = _assert_migration_preserves_structure(source)
    result = migrate_ssmd(source)
    assert result.content is not None
    assert ':::{voice="a"}\nHello ...600ms\n:::\n:::{voice="b"}' in result.content

    assert [(event.pos, event.attrs) for event in before.events if event.kind == "break"] == [
        (5, {"time": "600ms"})
    ]
    assert [(event.pos, event.attrs) for event in after.events if event.kind == "break"] == [
        (5, {"time": "600ms"})
    ]

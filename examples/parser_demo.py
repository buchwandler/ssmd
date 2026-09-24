#!/usr/bin/env python3
"""Inspect a strict SSMD 0.9 document with the sentence-neutral parser."""

from __future__ import annotations

from pathlib import Path

from ssmd.parser import lint, parse_structure


def main() -> int:
    """Parse and display structure from the comprehensive 0.9 example."""
    source_path = Path(__file__).with_name("all_features.ssmd.md")
    source = source_path.read_text(encoding="utf-8")
    structure = parse_structure(source, dialect="0.9")

    print(f"Source: {source_path.name}")
    print(f"Front matter: {structure.header}")
    print(f"Clean text:\n{structure.clean_text}\n")

    print("Annotations:")
    for annotation in structure.annotations:
        text = structure.clean_text[annotation.char_start : annotation.char_end]
        print(f"  {annotation.char_start}:{annotation.char_end} {text!r} {annotation.attrs}")

    print("\nStructural events:")
    for event in structure.events:
        print(f"  {event.pos} {event.anchor} {event.kind} {event.attrs}")

    issues = lint(source, dialect="0.9")
    print("\nLint:")
    if not issues:
        print("  No issues.")
    for issue in issues:
        print(f"  {issue.severity}: {issue.code}: {issue.message}")

    diagnostics = [item for item in structure.diagnostics if item.severity == "error"]
    return 1 if diagnostics or any(issue.severity == "error" for issue in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())

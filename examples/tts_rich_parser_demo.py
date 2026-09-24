#!/usr/bin/env python3
"""Display SSMD 0.9 structural spans and events with Rich."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ssmd.parser import lint, parse_structure


def main() -> int:
    """Render structural parse results for the canonical feature example."""
    source_path = Path(__file__).with_name("all_features.ssmd.md")
    source = source_path.read_text(encoding="utf-8")
    structure = parse_structure(source, dialect="0.9")
    console = Console()

    console.print(Panel.fit("SSMD 0.9 Structural Parser", border_style="blue"))
    console.print(f"Source: {source_path.name}")
    console.print(Panel(structure.clean_text, title="Clean text", border_style="green"))

    annotations = Table(title="Annotations", show_header=True)
    annotations.add_column("Range", style="cyan")
    annotations.add_column("Text", style="white")
    annotations.add_column("Attributes", style="dim")
    for annotation in structure.annotations:
        text = structure.clean_text[annotation.char_start : annotation.char_end]
        annotations.add_row(
            f"{annotation.char_start}:{annotation.char_end}",
            text,
            str(annotation.attrs),
        )
    console.print(annotations)

    events = Table(title="Structural events", show_header=True)
    events.add_column("Position", style="cyan", justify="right")
    events.add_column("Anchor")
    events.add_column("Kind", style="green")
    events.add_column("Attributes", style="dim")
    for event in structure.events:
        events.add_row(str(event.pos), event.anchor, event.kind, str(event.attrs))
    console.print(events)

    issues = lint(source, dialect="0.9")
    for issue in issues:
        console.print(f"{issue.severity}: {issue.code}: {issue.message}")
    errors = any(item.severity == "error" for item in structure.diagnostics) or any(
        issue.severity == "error" for issue in issues
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

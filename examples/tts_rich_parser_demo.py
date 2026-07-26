#!/usr/bin/env python3
"""Parse example_ssmd.md and simulate TTS with Rich output."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from ssmd import parse_sentences


def build_sentence_text(sentence) -> str:
    parts: list[str] = []
    for segment in sentence.segments:
        if segment.substitution:
            parts.append(segment.substitution)
        else:
            parts.append(segment.text)

    if not parts:
        return ""

    result = parts[0]
    for part in parts[1:]:
        if part and part[0] in ".!?,;:'\")}]>":
            result += part
        elif result and result[-1] in "([{<\"'":
            result += part
        else:
            result += " " + part

    return result.strip()


def sentence_metadata(sentence) -> list[str]:
    details: list[str] = []
    if sentence.voice:
        if sentence.voice.name:
            details.append(f"voice={sentence.voice.name}")
        if sentence.voice.language:
            details.append(f"voice-lang={sentence.voice.language}")
        if sentence.voice.gender:
            details.append(f"gender={sentence.voice.gender}")
    if sentence.language:
        details.append(f"lang={sentence.language}")
    if sentence.prosody:
        if sentence.prosody.volume:
            details.append(f"volume={sentence.prosody.volume}")
        if sentence.prosody.rate:
            details.append(f"rate={sentence.prosody.rate}")
        if sentence.prosody.pitch:
            details.append(f"pitch={sentence.prosody.pitch}")
    return details


def sentence_events(sentence) -> list[str]:
    events: list[str] = []
    for segment in sentence.segments:
        for mark in segment.marks_before:
            events.append(f"mark:{mark}")
        for brk in segment.breaks_before:
            if brk.time:
                events.append(f"break:{brk.time}")
            elif brk.strength:
                events.append(f"break:{brk.strength}")
        if segment.emphasis:
            events.append("emphasis")
        for brk in segment.breaks_after:
            if brk.time:
                events.append(f"break:{brk.time}")
            elif brk.strength:
                events.append(f"break:{brk.strength}")
        for mark in segment.marks_after:
            events.append(f"mark:{mark}")
    if sentence.is_paragraph_end:
        events.append("paragraph-end")
    return events


def main() -> int:  # noqa: C901
    console = Console()
    examples_dir = Path(__file__).parent
    ssmd_file = examples_dir / "example_ssmd.md"
    if not ssmd_file.exists():
        console.print(f"Missing file: {ssmd_file}")
        return 1

    ssmd_text = ssmd_file.read_text(encoding="utf-8")
    sentences = parse_sentences(ssmd_text)

    console.print(Panel.fit("SSMD Parser -> Rich TTS Simulation", border_style="blue"))
    console.print(f"Sentences parsed: {len(sentences)}\n")

    progress = Progress(
        SpinnerColumn(),
        TextColumn("Speaking {task.completed}/{task.total}"),
        BarColumn(bar_width=40),
        TextColumn("{task.percentage:>3.0f}%"),
        console=console,
    )

    with progress:
        task_id = progress.add_task("tts", total=len(sentences))
        for index, sentence in enumerate(sentences, start=1):
            text = build_sentence_text(sentence)
            meta = sentence_metadata(sentence)
            events = sentence_events(sentence)

            header = Text(f"Sentence {index}", style="bold")
            console.print(Panel(Text(text), title=header, border_style="green"))

            table = Table(show_header=False, box=None)
            table.add_row("Meta", ", ".join(meta) if meta else "-")
            table.add_row("Events", ", ".join(events) if events else "-")
            console.print(table)

            segment_table = Table(title="Segments", show_header=True)
            segment_table.add_column("#", style="cyan", width=4)
            segment_table.add_column("Text", style="white")
            segment_table.add_column("Attrs", style="dim")

            for seg_index, segment in enumerate(sentence.segments, start=1):
                attrs: list[str] = []
                if segment.emphasis:
                    attrs.append(f"emphasis={segment.emphasis}")
                if segment.language:
                    attrs.append(f"lang={segment.language}")
                if segment.voice:
                    if segment.voice.name:
                        attrs.append(f"voice={segment.voice.name}")
                    if segment.voice.language:
                        attrs.append(f"voice-lang={segment.voice.language}")
                    if segment.voice.gender:
                        attrs.append(f"gender={segment.voice.gender}")
                    if segment.voice.variant is not None:
                        attrs.append(f"variant={segment.voice.variant}")
                if segment.say_as:
                    attrs.append(f"say-as={segment.say_as.interpret_as}")
                if segment.substitution:
                    attrs.append(f"sub={segment.substitution}")
                if segment.phoneme:
                    attrs.append(f"phoneme={segment.phoneme.ph}")
                if segment.extension:
                    attrs.append(f"ext={segment.extension}")
                if segment.prosody:
                    if segment.prosody.volume:
                        attrs.append(f"volume={segment.prosody.volume}")
                    if segment.prosody.rate:
                        attrs.append(f"rate={segment.prosody.rate}")
                    if segment.prosody.pitch:
                        attrs.append(f"pitch={segment.prosody.pitch}")
                if segment.breaks_before:
                    attrs.append("breaks-before")
                if segment.breaks_after:
                    attrs.append("breaks-after")
                if segment.marks_before:
                    attrs.append("marks-before")
                if segment.marks_after:
                    attrs.append("marks-after")

                segment_table.add_row(str(seg_index), segment.text, ", ".join(attrs) or "-")

            console.print(segment_table)
            console.print()

            progress.advance(task_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

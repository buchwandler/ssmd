"""Semantic migration from legacy SSMD to canonical 0.9."""

from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from ssmd.formatter import FormatError, format_canonical
from ssmd.frontmatter import FrontMatterError, parse_front_matter, serialize_front_matter
from ssmd.parser import parse_structure
from ssmd.spans import AnnotationSpan, Diagnostic, StructuralEvent


@dataclass(frozen=True)
class MigrationResult:
    """Result of a semantic migration attempt."""

    content: str | None
    diagnostics: tuple[Diagnostic, ...] = ()
    manual_actions: tuple[str, ...] = ()
    written: bool = False

    @property
    def success(self) -> bool:
        return self.content is not None and not any(
            item.severity == "error" for item in self.diagnostics
        )


@dataclass
class _SpanNode:
    start: int
    end: int
    attrs: dict[str, str]
    children: list[_SpanNode]


class _ManualActionRequired(ValueError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _diagnostic(code: str, message: str) -> Diagnostic:
    return Diagnostic(code=code, severity="error", message=message)


def _escape_text(text: str) -> str:
    escaped = text.replace("\\", "\\\\")
    for character in '*[]{}~@"':
        escaped = escaped.replace(character, "\\" + character)
    return escaped


def _quote_attribute(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ('"', "[", "]", "{", "}"):
        escaped = escaped.replace(character, "\\" + character)
    return f'"{escaped}"'


def _format_attrs(attrs: dict[str, str]) -> str:
    return " ".join(f"{key}={_quote_attribute(value)}" for key, value in sorted(attrs.items()))


def _canonical_attrs(attrs: dict[str, str]) -> dict[str, str]:
    from ssmd.parser import _parse_prosody_params

    tag = attrs.get("tag")
    if "alt" in attrs:
        raise _ManualActionRequired(
            "Legacy audio alt text is ambiguous in SSMD 0.9. Choose spoken fallback content or description metadata manually."
        )

    values = {key: value for key, value in attrs.items() if key != "tag"}
    aliases = {"voice-lang": "voice-languages", "voice_lang": "voice-languages", "language": "lang"}
    for alias, canonical in aliases.items():
        if alias in values:
            if canonical in values:
                raise _ManualActionRequired(
                    f"Both {alias!r} and {canonical!r} are present. Resolve the duplicate manually."
                )
            values[canonical] = values.pop(alias)

    if any(key in values for key in ("volume", "rate", "pitch", "v", "r", "p", "vrp")):
        prosody = _parse_prosody_params(values)
        if prosody is None:
            if "vrp" in values:
                raise _ManualActionRequired(
                    f"Invalid legacy vrp value {values['vrp']!r}; correct it manually."
                )
        else:
            for key in ("volume", "rate", "pitch", "v", "r", "p", "vrp"):
                values.pop(key, None)
            for key in ("volume", "rate", "pitch"):
                value = getattr(prosody, key)
                if value is not None:
                    values[key] = value

    if tag == "emphasis" and values.get("emphasis") not in {"moderate", "strong", "reduced"}:
        raise _ManualActionRequired("The legacy emphasis level cannot be represented safely.")
    return values


def _span_forest(spans: list[AnnotationSpan]) -> list[_SpanNode]:
    ordered = sorted(spans, key=lambda span: (span.char_start, -span.char_end))
    roots: list[_SpanNode] = []
    stack: list[_SpanNode] = []
    for span in ordered:
        node = _SpanNode(span.char_start, span.char_end, dict(span.attrs), [])
        while stack and span.char_start >= stack[-1].end:
            stack.pop()
        if stack:
            parent = stack[-1]
            if span.char_end > parent.end:
                raise _ManualActionRequired(
                    "Overlapping legacy annotations cannot be nested without changing their meaning."
                )
            if span.char_start == parent.start and span.char_end == parent.end:
                raise _ManualActionRequired(
                    "Coextensive legacy annotations have ambiguous nesting."
                )
            parent.children.append(node)
        else:
            roots.append(node)
        stack.append(node)
    return roots


def _event_text(event: StructuralEvent, text: str) -> str:
    if event.kind == "mark":
        separator = " " if event.pos > 0 and not text[event.pos - 1].isspace() else ""
        return f"{separator}@{event.attrs['name']}"
    if event.kind != "break":
        return ""
    if "time" in event.attrs:
        marker = f"...{event.attrs['time']}"
    else:
        strength_markers = {
            "none": "...n",
            "x-weak": "...w",
            "weak": "...w",
            "medium": "...m",
            "strong": "...s",
            "x-strong": "...p",
        }
        marker = strength_markers.get(event.attrs.get("strength", "strong"), "...s")
    if (
        event.anchor == "before"
        and event.pos < len(text)
        and not text[event.pos].isspace()
        and text[event.pos] not in ".!?;:,"
    ):
        marker += " "
    return marker


def _render_range(
    text: str,
    start: int,
    end: int,
    children: list[_SpanNode],
    events: list[StructuralEvent],
) -> str:
    output: list[str] = []
    cursor = start
    positions: dict[int, list[StructuralEvent]] = {}
    for event in events:
        if event.kind in {"break", "mark"} and start <= event.pos <= end:
            positions.setdefault(event.pos, []).append(event)

    def append_text(until: int) -> None:
        nonlocal cursor
        for position in sorted(pos for pos in positions if cursor < pos < until):
            output.append(_escape_text(text[cursor:position]))
            output.extend(_event_text(event, text) for event in positions.pop(position))
            cursor = position
        output.append(_escape_text(text[cursor:until]))
        cursor = until

    output.extend(_event_text(event, text) for event in positions.pop(start, []))

    for child in children:
        append_text(child.start)
        output.extend(_event_text(event, text) for event in positions.pop(child.start, []))
        attrs = _canonical_attrs(child.attrs)
        inner_events = [event for event in events if child.start < event.pos < child.end]
        content = _render_range(text, child.start, child.end, child.children, inner_events)
        tag = child.attrs.get("tag")
        if tag == "emphasis":
            marker = {"moderate": "*", "strong": "**", "reduced": "~~"}[attrs["emphasis"]]
            output.append(f"{marker}{content}{marker}")
        elif tag == "div" and not attrs:
            output.append(content)
        else:
            if not attrs:
                raise _ManualActionRequired(
                    "A legacy annotation has no canonical attributes and cannot be represented safely."
                )
            output.append(f"[{content}]{{{_format_attrs(attrs)}}}")
        cursor = child.end
        for position in [pos for pos in positions if child.start < pos < child.end]:
            positions.pop(position)
        output.extend(_event_text(event, text) for event in positions.pop(child.end, []))

    append_text(end)
    for position in sorted(positions):
        output.extend(_event_text(event, text) for event in positions[position])
    return "".join(output)


def _semantic_signature(text: str, dialect: Literal["0.8", "0.9"]) -> tuple[Any, ...]:
    from ssmd.parser import _parse_prosody_params

    structure = parse_structure(text, dialect=dialect)
    if any(item.severity == "error" for item in structure.diagnostics):
        raise _ManualActionRequired("The source or migrated document has parser errors.")

    def normalize_attrs(attrs: dict[str, str]) -> tuple[tuple[str, str], ...]:
        values = {key: value for key, value in attrs.items() if key != "tag"}
        for alias, canonical in (
            ("voice-lang", "voice-languages"),
            ("voice_lang", "voice-languages"),
            ("language", "lang"),
        ):
            if alias in values:
                values[canonical] = values.pop(alias)
        if any(key in values for key in ("volume", "rate", "pitch", "v", "r", "p", "vrp")):
            prosody = _parse_prosody_params(values)
            if prosody is not None:
                for key in ("volume", "rate", "pitch", "v", "r", "p", "vrp"):
                    values.pop(key, None)
                for key in ("volume", "rate", "pitch"):
                    value = getattr(prosody, key)
                    if value is not None:
                        values[key] = value
        return tuple(sorted(values.items()))

    def annotation_signature(item: AnnotationSpan) -> tuple[Any, ...]:
        start = item.char_start
        end = item.char_end
        while start < end and structure.clean_text[start].isspace():
            start += 1
        while end > start and structure.clean_text[end - 1].isspace():
            end -= 1
        return start, end, normalize_attrs(item.attrs)

    annotations = tuple(sorted(annotation_signature(item) for item in structure.annotations))
    events = tuple(
        (item.pos, item.kind, tuple(sorted(item.attrs.items()))) for item in structure.events
    )
    header = dict(structure.header)
    header.pop("ssmd_version", None)
    return structure.clean_text, annotations, events, header


def migrate_ssmd(text: str) -> MigrationResult:
    """Convert a legacy SSMD document to canonical 0.9 when equivalence is provable."""
    try:
        front_matter = parse_front_matter(text)
    except FrontMatterError as exc:
        return MigrationResult(
            None,
            (_diagnostic(exc.code, str(exc)),),
            ("Repair the YAML front matter, then rerun migration.",),
        )

    version = front_matter.data.get("ssmd_version")
    if version not in (None, "0.8", 0.8, "0.9", 0.9):
        return MigrationResult(
            None,
            (
                _diagnostic(
                    "migration.unsupported_version", f"Cannot migrate SSMD version {version!r}."
                ),
            ),
            ("Convert the document from its declared version manually.",),
        )

    if version in {"0.9", 0.9}:
        try:
            content = format_canonical(text)
        except FormatError as exc:
            return MigrationResult(None, exc.diagnostics, ("Repair the reported SSMD 0.9 issues.",))
        return MigrationResult(content, ())

    if "extensions" in front_matter.data:
        return MigrationResult(
            None,
            (
                _diagnostic(
                    "migration.manual_action_required",
                    "Portable front matter cannot define executable extension handlers.",
                ),
            ),
            ("Move extension handlers to trusted configuration and verify each extension use.",),
        )

    try:
        before = _semantic_signature(text, "0.8")
        if len(before) < 4:
            raise _ManualActionRequired("The legacy semantic model is incomplete.")
        structure = parse_structure(text, dialect="0.8")
        if any(item.severity == "error" for item in structure.diagnostics):
            raise _ManualActionRequired("The legacy source contains parser errors.")
        forest = _span_forest(structure.annotations)
        full_document_directives = [
            node
            for node in forest
            if node.attrs.get("tag") == "div"
            and node.start == 0
            and node.end == len(structure.clean_text)
        ]
        if len(full_document_directives) > 1:
            raise _ManualActionRequired("The document has ambiguous full-document directives.")

        if full_document_directives:
            directive = full_document_directives[0]
            forest.remove(directive)
            attrs = _canonical_attrs(directive.attrs)
            body = _render_range(
                structure.clean_text,
                directive.start,
                directive.end,
                directive.children,
                structure.events,
            )
            if attrs:
                fence_length = max(
                    [
                        3,
                        *(
                            len(line) + 1
                            for line in body.splitlines()
                            if line and set(line) == {":"}
                        ),
                    ]
                )
                fence = ":" * fence_length
                migrated_body = f"{fence}{{{_format_attrs(attrs)}}}\n{body}\n{fence}"
            else:
                migrated_body = body
        else:
            migrated_body = _render_range(
                structure.clean_text,
                0,
                len(structure.clean_text),
                forest,
                structure.events,
            )

        header = dict(front_matter.data)
        header["ssmd_version"] = "0.9"
        candidate = serialize_front_matter(header, migrated_body)
        canonical = format_canonical(candidate)
        after = _semantic_signature(canonical, "0.9")
        if before != after:
            raise _ManualActionRequired(
                "The migrated document is not semantically equivalent to its legacy source."
            )
        return MigrationResult(canonical, ())
    except _ManualActionRequired as exc:
        return MigrationResult(
            None,
            (_diagnostic("migration.manual_action_required", exc.message),),
            (exc.message,),
        )
    except FormatError as exc:
        return MigrationResult(
            None,
            exc.diagnostics,
            ("Resolve the reported syntax issue manually before migration.",),
        )


def _atomic_write_text(path: Path, text: str) -> None:
    if path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
    else:
        current_umask = os.umask(0)
        os.umask(current_umask)
        mode = 0o666 & ~current_umask
    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
        temporary_path = None
        os.chmod(path, mode)
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def migrate_file(
    source: str | Path,
    output: str | Path | None = None,
    *,
    overwrite: bool = False,
) -> MigrationResult:
    """Migrate a file and atomically install the result only after verification."""
    source_path = Path(source)
    destination = Path(output) if output is not None else source_path
    content = source_path.read_text(encoding="utf-8")
    result = migrate_ssmd(content)
    if not result.success or result.content is None:
        return result
    same_path = source_path.resolve() == destination.resolve()
    if destination.exists() and not same_path and not overwrite:
        return MigrationResult(
            None,
            (_diagnostic("migration.output_exists", f"Output file already exists: {destination}"),),
            ("Choose a new output path or explicitly allow overwriting.",),
        )
    _atomic_write_text(destination, result.content)
    return replace(result, written=True)

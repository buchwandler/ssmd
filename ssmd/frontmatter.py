"""YAML front matter parsing and serialization for SSMD documents."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import yaml

FRONT_MATTER_KEYS = frozenset(
    {"title", "voice_bindings", "pause_defaults", "heading", "extensions"}
)


@dataclass(frozen=True)
class FrontMatterIssue:
    """A stable front matter diagnostic."""

    code: str
    severity: str
    message: str
    line: int | None = None
    column: int | None = None


class FrontMatterError(ValueError):
    """Raised when a present front matter block cannot be parsed safely."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "header.yaml_invalid",
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.line = line
        self.column = column


@dataclass(frozen=True)
class FrontMatter:
    """Parsed SSMD front matter and the body that follows it."""

    data: dict[str, Any]
    body: str
    present: bool
    source_end: int | None = None
    raw: str | None = None


def _line_error(mark: Any) -> tuple[int | None, int | None]:
    """Return the line and column from a PyYAML mark-like object."""
    if mark is None:
        return None, None
    return getattr(mark, "line", 0) + 1, getattr(mark, "column", 0) + 1


def parse_front_matter(text: str) -> FrontMatter:
    """Parse an SSMD front matter block from *text*.

    Only a line containing exactly ``---`` can open a block.  The matching
    closing delimiter may be ``---`` or ``...``.  Text without a front matter
    block is returned unchanged and never parsed as YAML.
    """
    if not text:
        return FrontMatter({}, text, False)

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return FrontMatter({}, text, False)

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") in {"---", "..."}:
            closing_index = index
            break

    if closing_index is None:
        raise FrontMatterError(
            "YAML front matter is missing a closing delimiter",
            code="header.yaml_invalid",
            line=1,
            column=1,
        )

    raw = "".join(lines[1:closing_index])
    body = "".join(lines[closing_index + 1 :]).lstrip("\r\n")
    source_end = sum(len(line) for line in lines[: closing_index + 1])

    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        error_line, error_column = _line_error(getattr(exc, "problem_mark", None))
        detail = getattr(exc, "problem", None) or str(exc)
        raise FrontMatterError(
            f"Invalid YAML front matter: {detail}",
            code="header.yaml_invalid",
            line=error_line,
            column=error_column,
        ) from exc

    if loaded is None:
        data: dict[str, Any] = {}
    elif not isinstance(loaded, dict):
        raise FrontMatterError(
            "YAML front matter root must be a mapping",
            code="header.root_not_mapping",
            line=1,
            column=1,
        )
    else:
        data = dict(loaded)

    return FrontMatter(data, body, True, source_end=source_end, raw=raw)


def validate_front_matter(data: Mapping[str, Any]) -> list[FrontMatterIssue]:
    """Validate the structural fields owned by the portable header contract."""
    issues: list[FrontMatterIssue] = []
    for key in data:
        if key not in FRONT_MATTER_KEYS:
            issues.append(
                FrontMatterIssue(
                    "header.unknown_key",
                    "warn",
                    f"Unknown front matter key: {key}",
                )
            )

    if "title" in data and not isinstance(data["title"], str):
        issues.append(
            FrontMatterIssue(
                "header.title_invalid",
                "error",
                "title must be a string",
            )
        )

    if "voice_bindings" in data and not isinstance(data["voice_bindings"], Mapping):
        issues.append(
            FrontMatterIssue(
                "header.voice_bindings_invalid",
                "error",
                "voice_bindings must be a mapping",
            )
        )
    if "pause_defaults" in data and not isinstance(data["pause_defaults"], Mapping):
        issues.append(
            FrontMatterIssue(
                "header.pause_defaults_invalid",
                "error",
                "pause_defaults must be a mapping",
            )
        )
    return issues


def _ordered_header(data: Mapping[str, Any]) -> dict[str, Any]:
    """Order recognized generated keys after existing metadata."""
    recognized = ("title", "voice_bindings", "pause_defaults", "heading", "extensions")
    result: dict[str, Any] = {key: value for key, value in data.items() if key not in recognized}
    for key in recognized:
        if key in data:
            result[key] = data[key]
    return result


def serialize_front_matter(data: Mapping[str, Any], body: str) -> str:
    """Serialize a mapping and body with deterministic SSMD delimiters."""
    if not isinstance(data, Mapping):
        raise ValueError("front matter data must be a mapping")
    header = yaml.safe_dump(
        _ordered_header(data),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).rstrip("\n")
    clean_body = body.lstrip("\r\n")
    return f"---\n{header}\n---\n{clean_body}" if header else f"---\n---\n{clean_body}"


def _merge_defaults(explicit: Any, generated: Any) -> Any:
    """Merge explicit values over generated defaults recursively."""
    if isinstance(explicit, Mapping) and isinstance(generated, Mapping):
        merged = dict(generated)
        for key, value in explicit.items():
            merged[key] = _merge_defaults(value, merged[key]) if key in merged else value
        return merged
    return explicit


def merge_generated_header(
    existing: Mapping[str, Any],
    generated: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge generated defaults without replacing explicit document values."""
    merged = _merge_defaults(existing, generated)
    return _ordered_header(merged)


__all__ = [
    "FRONT_MATTER_KEYS",
    "FrontMatter",
    "FrontMatterError",
    "FrontMatterIssue",
    "merge_generated_header",
    "parse_front_matter",
    "serialize_front_matter",
    "validate_front_matter",
]

"""Span data types and structured diagnostics for SSMD parsing and linting."""

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class LintIssue:
    severity: str
    message: str
    char_start: int | None = None
    char_end: int | None = None
    code: str = "diagnostic"
    source_start: int | None = None
    source_end: int | None = None
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True)
class Diagnostic:
    """A stable parser diagnostic with source coordinates."""

    code: str
    severity: str
    message: str
    source_start: int | None = None
    source_end: int | None = None
    line: int | None = None
    column: int | None = None


@dataclass
class AnnotationSpan:
    char_start: int
    char_end: int
    attrs: dict[str, str]
    kind: str | None = None
    node_id: str | None = None


@dataclass
class ParseSpansResult:
    clean_text: str
    annotations: list[AnnotationSpan] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


@dataclass(frozen=True)
class StructuralEvent:
    """A zero-width structural event in clean-text coordinates."""

    pos: int
    kind: Literal["break", "mark", "paragraph"]
    anchor: Literal["before", "after"]
    attrs: dict[str, str] = field(default_factory=dict)


@dataclass
class ParseStructureResult:
    """Sentence-neutral structural parse for downstream pipelines."""

    clean_text: str
    annotations: list[AnnotationSpan] = field(default_factory=list)
    events: list[StructuralEvent] = field(default_factory=list)
    header: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


_DIAGNOSTIC_RULES = (
    ("Unbalanced annotation brackets", "syntax.unbalanced_brackets", "["),
    ("Unbalanced annotation braces", "syntax.unbalanced_braces", "{"),
    ("Unterminated quote", "syntax.unterminated_quote", "{"),
    ("Unexpected character", "syntax.invalid_attribute_key", ""),
    ("Unexpected </div>", "syntax.unexpected_directive_close", "</div>"),
    ("Unclosed <div>", "syntax.unclosed_directive", "<div"),
    ("Invalid vrp value", "prosody.invalid_vrp", ""),
)


def diagnostics_from_warnings(text: str, warnings: list[str]) -> list[Diagnostic]:
    """Convert legacy parser warning strings into stable diagnostics."""
    diagnostics: list[Diagnostic] = []
    for warning in warnings:
        code = "syntax.parse_warning"
        token = ""
        for prefix, candidate_code, candidate_token in _DIAGNOSTIC_RULES:
            if warning.startswith(prefix):
                code = candidate_code
                token = candidate_token
                break

        source_start = text.find(token) if token else None
        if source_start is not None and source_start < 0:
            source_start = None
        source_end = source_start + len(token) if source_start is not None and token else None
        line = column = None
        if source_start is not None:
            line = text.count("\n", 0, source_start) + 1
            line_start = text.rfind("\n", 0, source_start) + 1
            column = source_start - line_start + 1

        diagnostics.append(
            Diagnostic(
                code=code,
                severity="warn" if code == "prosody.invalid_vrp" else "error",
                message=warning,
                source_start=source_start,
                source_end=source_end,
                line=line,
                column=column,
            )
        )
    return diagnostics


__all__ = [
    "AnnotationSpan",
    "Diagnostic",
    "StructuralEvent",
    "ParseStructureResult",
    "ParseSpansResult",
    "LintIssue",
    "diagnostics_from_warnings",
]

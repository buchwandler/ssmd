"""Source-aware lexical scanning for the SSMD 0.9 grammar."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from ssmd.spans import Diagnostic

TokenKind = Literal[
    "text",
    "emphasis",
    "annotation",
    "break",
    "mark",
    "paragraph",
    "heading",
    "directive",
]


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    source_start: int
    source_end: int
    value: str = ""
    attrs: dict[str, str] = field(default_factory=dict)
    children: tuple[Token, ...] = ()
    level: int = 0

    attribute_ranges: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class _Line:
    content: str
    start: int
    content_end: int
    end: int


_OPEN_FENCE = re.compile(r"^(?P<fence>:{3,})\{(?P<attrs>.*)\}$")
_CLOSE_FENCE = re.compile(r"^:{3,}$")
_HEADING = re.compile(r"^\s*(?P<marker>#{1,6})(?:\s+|$)(?P<content>.*)$")
_BREAK = re.compile(r"\.\.\.(?P<value>\d+(?:\.\d+)?(?:ms|s)|[nwcsp])")
_MARK = re.compile(r"@(?P<name>[A-Za-z0-9_][A-Za-z0-9_.:-]*)")
_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_:-]*")
_LEGACY_ATTRIBUTES = frozenset(
    {"v", "r", "p", "vrp", "voice-lang", "voice_lang", "language", "alt"}
)
_STRENGTHS = {"n": "none", "w": "x-weak", "c": "medium", "s": "strong", "p": "x-strong"}
_LEGACY_INLINE_FORMS = (
    ("_", "syntax.legacy_reduced_emphasis", "Use `~~...~~` for reduced emphasis in SSMD 0.9."),
    ("++", "syntax.legacy_volume_alias", "Use a `volume` attribute instead of `++...++`."),
    (">>", "syntax.legacy_rate_alias", "Use a `rate` attribute instead of `>>...>>`."),
    ("^^", "syntax.legacy_pitch_alias", "Use a `pitch` attribute instead of `^^...^^`."),
)


def _diagnostic(
    code: str,
    message: str,
    position: int,
    end: int,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity="error",
        message=message,
        source_start=position,
        source_end=end,
    )


def _find_unescaped(source: str, marker: str, start: int, end: int) -> int:
    position = start
    while position <= end - len(marker):
        if source[position] == "\\":
            position += 2
        elif source.startswith(marker, position):
            return position
        else:
            position += 1
    return -1


def _find_annotation_close(source: str, start: int, end: int) -> int:
    depth = 1
    position = start + 1
    while position < end:
        char = source[position]
        if char == "\\":
            position += 2
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return position
        position += 1
    return -1


def _find_attribute_close(source: str, start: int, end: int) -> int:
    quote = False
    escaped = False
    position = start
    while position < end:
        char = source[position]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            quote = not quote
        elif char == "}" and not quote:
            return position
        position += 1
    return -1


def _read_quoted_value(
    source: str,
    position: int,
    end: int,
    source_offset: int,
    diagnostics: list[Diagnostic],
) -> tuple[str | None, int]:
    if position >= end or source[position] != '"':
        diagnostics.append(
            _diagnostic(
                "syntax.invalid_attribute_value",
                "SSMD 0.9 attribute values must use double quotes.",
                source_offset + position,
                source_offset + min(position + 1, end),
            )
        )
        while position < end and not source[position].isspace() and source[position] != ",":
            position += 1
        return None, position

    position += 1
    value: list[str] = []
    while position < end:
        char = source[position]
        if char == '"':
            return "".join(value), position + 1
        if char == "\\":
            escape_start = position
            position += 1
            if position >= end or source[position] not in (chr(92), chr(34), "]", "}", "[", "{"):
                diagnostics.append(
                    _diagnostic(
                        "syntax.invalid_escape",
                        "Invalid escape in quoted attribute value.",
                        source_offset + escape_start,
                        source_offset + min(position + 1, end),
                    )
                )
                if position < end:
                    value.append(source[position])
                    position += 1
                continue
            value.append(source[position])
            position += 1
            continue
        value.append(char)
        position += 1

    diagnostics.append(
        _diagnostic(
            "syntax.unclosed_attribute_value",
            "Quoted attribute value is not closed.",
            source_offset + position,
            source_offset + position,
        )
    )
    return "".join(value), position


def _parse_attributes(
    source: str,
    start: int,
    end: int,
    source_offset: int,
    diagnostics: list[Diagnostic],
    *,
    strict: bool,
) -> tuple[dict[str, str], dict[str, tuple[int, int]]]:
    attrs: dict[str, str] = {}
    attribute_ranges: dict[str, tuple[int, int]] = {}
    position = start

    while position < end:
        if source[position].isspace():
            position += 1
            continue
        if source[position] == ",":
            diagnostics.append(
                _diagnostic(
                    "syntax.comma_separator_legacy",
                    "Commas are not permitted between SSMD 0.9 attributes.",
                    source_offset + position,
                    source_offset + position + 1,
                )
            )
            position += 1
            continue

        key_start = position
        match = _KEY.match(source, position, end)
        if match is None:
            diagnostics.append(
                _diagnostic(
                    "syntax.invalid_attribute_key",
                    "Invalid character in attribute key.",
                    source_offset + position,
                    source_offset + position + 1,
                )
            )
            position += 1
            continue
        key = match.group().lower()
        position = match.end()
        if position >= end or source[position] != "=":
            diagnostics.append(
                _diagnostic(
                    "syntax.invalid_attribute_key",
                    f"Attribute {key!r} must be followed by '='.",
                    source_offset + key_start,
                    source_offset + position,
                )
            )
            while position < end and not source[position].isspace() and source[position] != ",":
                position += 1
            continue

        quote_position = position + 1
        value_start = quote_position + 1
        value, position = _read_quoted_value(
            source,
            quote_position,
            end,
            source_offset,
            diagnostics,
        )
        if value is None:
            continue
        if strict and position < end and not source[position].isspace() and source[position] != ",":
            diagnostics.append(
                _diagnostic(
                    "syntax.invalid_attribute_separator",
                    "SSMD 0.9 attributes must be separated by whitespace.",
                    source_offset + position,
                    source_offset + position + 1,
                )
            )
        if key in attrs:
            diagnostics.append(
                _diagnostic(
                    "syntax.duplicate_attribute",
                    f"Duplicate attribute {key!r}.",
                    source_offset + key_start,
                    source_offset + match.end(),
                )
            )
            continue
        if strict and key in _LEGACY_ATTRIBUTES:
            diagnostics.append(
                _diagnostic(
                    "syntax.legacy_attribute_alias",
                    f"Attribute alias {key!r} is not canonical SSMD 0.9 syntax.",
                    source_offset + key_start,
                    source_offset + match.end(),
                )
            )
        closed = position > quote_position and source[position - 1] == '"'
        value_end = position - 1 if closed else position
        attrs[key] = value
        attribute_ranges[key] = (source_offset + value_start, source_offset + value_end)

    return attrs, attribute_ranges


def _tokenize_inline(
    source: str,
    start: int,
    end: int,
    source_offset: int,
    strict: bool,
    diagnostics: list[Diagnostic],
) -> tuple[Token, ...]:
    tokens: list[Token] = []
    text_start = start
    text_value: list[str] = []

    def flush_text(position: int) -> None:
        nonlocal text_start, text_value
        if text_value:
            tokens.append(
                Token(
                    "text",
                    source_offset + text_start,
                    source_offset + position,
                    "".join(text_value),
                )
            )
        text_start = position
        text_value = []

    position = start
    while position < end:
        if source[position] == "\\" and position + 1 < end:
            escaped = source[position + 1]
            if escaped in '\\*[]{}~@"':
                text_value.append(escaped)
                position += 2
                continue

        if source[position] == "[":
            close = _find_annotation_close(source, position, end)
            attr_close: int | None = None
            if close >= 0 and close + 1 < end and source[close + 1] == "{":
                attr_close = _find_attribute_close(source, close + 2, end)
                if attr_close >= 0:
                    flush_text(position)
                    attrs, attribute_ranges = _parse_attributes(
                        source,
                        close + 2,
                        attr_close,
                        source_offset,
                        diagnostics,
                        strict=strict,
                    )
                    children = _tokenize_inline(
                        source,
                        position + 1,
                        close,
                        source_offset,
                        strict,
                        diagnostics,
                    )
                    tokens.append(
                        Token(
                            "annotation",
                            source_offset + position,
                            source_offset + attr_close + 1,
                            attrs=attrs,
                            children=children,
                            attribute_ranges=attribute_ranges,
                        )
                    )
                    position = attr_close + 1
                    text_start = position
                    continue
            if strict and (
                close < 0
                or close + 1 >= end
                or source[close + 1] != "{"
                or attr_close is None
                or attr_close < 0
            ):
                diagnostics.append(
                    _diagnostic(
                        "syntax.unclosed_annotation",
                        "Annotation must have a matching ']' and a closed attribute block.",
                        source_offset + position,
                        source_offset + min(position + 1, end),
                    )
                )

        if strict:
            for legacy_marker, code, message in _LEGACY_INLINE_FORMS:
                if not source.startswith(legacy_marker, position):
                    continue
                close = _find_unescaped(source, legacy_marker, position + len(legacy_marker), end)
                if close <= position + len(legacy_marker):
                    continue
                if legacy_marker == "_":
                    before = source[position - 1] if position > start else ""
                    after_position = close + len(legacy_marker)
                    after = source[after_position] if after_position < end else ""
                    if (before and (before.isalnum() or before == "_")) or (
                        after and (after.isalnum() or after == "_")
                    ):
                        continue
                diagnostics.append(
                    _diagnostic(
                        code,
                        message,
                        source_offset + position,
                        source_offset + close + len(legacy_marker),
                    )
                )
                break
        marker = next(
            (value for value in ("**", "~~", "*") if source.startswith(value, position)),
            None,
        )
        if marker is not None:
            close = _find_unescaped(source, marker, position + len(marker), end)
            if close >= 0 and close > position + len(marker):
                flush_text(position)
                level = {"*": "moderate", "**": "strong", "~~": "reduced"}[marker]
                children = _tokenize_inline(
                    source,
                    position + len(marker),
                    close,
                    source_offset,
                    strict,
                    diagnostics,
                )
                tokens.append(
                    Token(
                        "emphasis",
                        source_offset + position,
                        source_offset + close + len(marker),
                        value=level,
                        children=children,
                    )
                )
                position = close + len(marker)
                text_start = position
                continue

        break_match = _BREAK.match(source, position, end)
        if break_match and (
            break_match.end() == end
            or source[break_match.end()].isspace()
            or source[break_match.end()] in ".!?;:,"
        ):
            flush_text(position)
            value = break_match.group("value")
            attrs = {"time": value} if value[0].isdigit() else {"strength": _STRENGTHS[value]}
            tokens.append(
                Token(
                    "break",
                    source_offset + position,
                    source_offset + break_match.end(),
                    attrs=attrs,
                )
            )
            position = break_match.end()
            text_start = position
            continue

        mark_match = _MARK.match(source, position, end)
        if (
            mark_match
            and (position == start or source[position - 1].isspace())
            and (mark_match.end() == end or source[mark_match.end()].isspace())
        ):
            flush_text(position)
            tokens.append(
                Token(
                    "mark",
                    source_offset + position,
                    source_offset + mark_match.end(),
                    value=mark_match.group("name"),
                )
            )
            position = mark_match.end()
            text_start = position
            continue

        text_value.append(source[position])
        position += 1

    flush_text(end)
    return tuple(tokens)


def tokenize_inline(
    source: str,
    *,
    source_offset: int = 0,
    dialect: Literal["0.8", "0.9"] = "0.9",
) -> tuple[tuple[Token, ...], list[Diagnostic]]:
    """Tokenize inline SSMD while retaining original source ranges."""
    diagnostics: list[Diagnostic] = []
    tokens = _tokenize_inline(
        source,
        0,
        len(source),
        source_offset,
        dialect == "0.9",
        diagnostics,
    )
    return tokens, diagnostics


def _lines(source: str) -> list[_Line]:
    result: list[_Line] = []
    position = 0
    for raw_line in source.splitlines(keepends=True):
        content = raw_line.rstrip("\r\n")
        content_end = position + len(content)
        result.append(_Line(content, position, content_end, position + len(raw_line)))
        position += len(raw_line)
    if source and not result:
        result.append(_Line(source, 0, len(source), len(source)))
    return result


def tokenize_blocks(
    source: str,
    *,
    source_offset: int = 0,
    dialect: Literal["0.8", "0.9"] = "0.9",
) -> tuple[tuple[Token, ...], list[Diagnostic]]:
    """Tokenize paragraphs, headings, and nested colon-fenced directives."""
    diagnostics: list[Diagnostic] = []
    lines = _lines(source)
    strict = dialect == "0.9"

    def parse_level(
        start_line: int,
        expected_fence: int | None = None,
        opening_offset: int | None = None,
    ) -> tuple[list[Token], int, bool]:
        blocks: list[Token] = []
        paragraph_start: int | None = None
        paragraph_end: int | None = None

        def flush_paragraph() -> None:
            nonlocal paragraph_start, paragraph_end
            if paragraph_start is None or paragraph_end is None:
                return
            inline = _tokenize_inline(
                source,
                paragraph_start,
                paragraph_end,
                source_offset,
                strict,
                diagnostics,
            )
            blocks.append(
                Token(
                    "paragraph",
                    source_offset + paragraph_start,
                    source_offset + paragraph_end,
                    children=inline,
                )
            )
            paragraph_start = paragraph_end = None

        index = start_line
        while index < len(lines):
            line = lines[index]
            stripped = line.content.strip()
            close_match = _CLOSE_FENCE.fullmatch(stripped)
            open_match = _OPEN_FENCE.fullmatch(stripped)

            if close_match:
                flush_paragraph()
                if expected_fence is None:
                    if strict:
                        close_start = line.start + line.content.find(stripped)
                        diagnostics.append(
                            _diagnostic(
                                "syntax.unexpected_directive_close",
                                "Unexpected closing directive fence.",
                                source_offset + close_start,
                                source_offset + close_start + len(stripped),
                            )
                        )
                        paragraph_start = line.start
                        paragraph_end = line.content_end
                        flush_paragraph()
                        index += 1
                        continue
                    paragraph_start = line.start if paragraph_start is None else paragraph_start
                    paragraph_end = line.content_end
                    index += 1
                    continue

                close_length = len(stripped)
                if close_length != expected_fence:
                    close_start = line.start + line.content.find(stripped)
                    diagnostics.append(
                        _diagnostic(
                            "syntax.directive_fence_mismatch",
                            "Closing directive fence length does not match its opening fence.",
                            source_offset + close_start,
                            source_offset + close_start + close_length,
                        )
                    )
                return blocks, index + 1, True

            if open_match:
                flush_paragraph()
                fence = open_match.group("fence")
                attr_text = open_match.group("attrs")
                open_start = line.start + line.content.find(stripped)
                attr_start = open_start + len(fence) + 1
                attrs, attribute_ranges = _parse_attributes(
                    source,
                    attr_start,
                    attr_start + len(attr_text),
                    source_offset,
                    diagnostics,
                    strict=strict,
                )
                children, next_line, closed = parse_level(
                    index + 1,
                    len(fence),
                    open_start,
                )
                if not closed:
                    diagnostics.append(
                        _diagnostic(
                            "syntax.unclosed_directive",
                            "Directive block is missing its matching closing fence.",
                            source_offset + open_start,
                            source_offset + open_start + len(fence),
                        )
                    )
                token_end = lines[next_line - 1].end if next_line > index + 1 else line.content_end
                blocks.append(
                    Token(
                        "directive",
                        source_offset + open_start,
                        source_offset + token_end,
                        attrs=attrs,
                        attribute_ranges=attribute_ranges,
                        children=tuple(children),
                        level=len(fence),
                    )
                )
                index = next_line
                continue

            heading_match = _HEADING.fullmatch(line.content)
            if heading_match:
                flush_paragraph()
                content_start = line.start + heading_match.start("content")
                inline = _tokenize_inline(
                    source,
                    content_start,
                    line.content_end,
                    source_offset,
                    strict,
                    diagnostics,
                )
                blocks.append(
                    Token(
                        "heading",
                        source_offset + line.start,
                        source_offset + line.content_end,
                        children=inline,
                        level=len(heading_match.group("marker")),
                    )
                )
                index += 1
                continue

            if strict and (stripped.startswith("<div") or stripped.lower() == "</div>"):
                flush_paragraph()
                div_start = line.start + line.content.find(stripped)
                diagnostics.append(
                    _diagnostic(
                        "syntax.legacy_div_directive",
                        "Raw <div> directives are compatibility-only; use colon fences.",
                        source_offset + div_start,
                        source_offset + div_start + len(stripped),
                    )
                )

            if not stripped:
                flush_paragraph()
                index += 1
                continue

            if paragraph_start is None:
                paragraph_start = line.start
            paragraph_end = line.content_end
            index += 1

        flush_paragraph()
        if expected_fence is not None:
            return blocks, index, False
        return blocks, index, True

    tokens, _, _ = parse_level(0)
    return tuple(tokens), diagnostics

"""SSMD formatting utilities for properly formatted output.

This module provides utilities to format parsed SSMD sentences with proper
line breaks, paragraph spacing, and structural elements according to SSMD
formatting conventions.
"""

from collections.abc import Mapping
from dataclasses import replace

from ssmd.ast import (
    AnnotationNode,
    BreakNode,
    DirectiveNode,
    EmphasisNode,
    HeadingNode,
    MarkNode,
    Node,
    ParagraphNode,
    TextNode,
    _is_tight_directive_transition,
    ast_from_tokens,
)
from ssmd.frontmatter import (
    FrontMatter,
    FrontMatterError,
    parse_front_matter,
    serialize_front_matter,
    validate_front_matter,
)
from ssmd.segment import Segment
from ssmd.sentence import Sentence
from ssmd.spans import Diagnostic
from ssmd.ssml_conversions import SSMD_BREAK_STRENGTH_MAP
from ssmd.tokenizer import tokenize_blocks
from ssmd.types import BreakAttrs, ProsodyAttrs, VoiceAttrs

# Backward compatibility aliases
SSMDSentence = Sentence
SSMDSegment = Segment


class FormatError(ValueError):
    """Raised when canonical formatting would be invalid or lossy."""

    def __init__(self, diagnostics: tuple[Diagnostic, ...]):
        self.diagnostics = diagnostics
        message = diagnostics[0].message if diagnostics else "SSMD formatting failed"
        super().__init__(message)


def _format_diagnostic(
    code: str,
    message: str,
    *,
    source_start: int | None = None,
    source_end: int | None = None,
    line: int | None = None,
    column: int | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity="error",
        message=message,
        source_start=source_start,
        source_end=source_end,
        line=line,
        column=column,
    )


def _quote_attribute(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ('"', "[", "]", "{", "}"):
        escaped = escaped.replace(character, "\\" + character)
    return f'"{escaped}"'


def _format_attributes(attrs: Mapping[str, str]) -> str:
    return " ".join(
        f"{key.lower()}={_quote_attribute(value)}"
        for key, value in sorted(attrs.items(), key=lambda item: item[0].lower())
    )


def _render_directive(attrs: Mapping[str, str], body: str, *, nested_fence_length: int = 0) -> str:
    fence_length = max(
        3,
        nested_fence_length + 1,
        max(
            (len(line) + 1 for line in body.splitlines() if line and set(line) == {":"}),
            default=3,
        ),
    )
    fence = ":" * fence_length
    return f"{fence}{{{_format_attributes(attrs)}}}\n{body}\n{fence}"


def _nested_fence_length(node: Node) -> int:
    if not isinstance(node, DirectiveNode):
        return 0
    return max([node.fence_length, *(_nested_fence_length(child) for child in node.children)])


def _render_inline_node(node: Node, source: str) -> str:
    if isinstance(node, TextNode):
        return source[node.source_start : node.source_end]
    if isinstance(node, EmphasisNode):
        marker = {"moderate": "*", "strong": "**", "reduced": "~~"}[node.level]
        content = "".join(_render_inline_node(child, source) for child in node.children)
        return f"{marker}{content}{marker}"
    if isinstance(node, AnnotationNode):
        content = "".join(_render_inline_node(child, source) for child in node.children)
        return f"[{content}]{{{_format_attributes(node.attrs)}}}"
    if isinstance(node, BreakNode):
        if "time" in node.attrs:
            return f"...{node.attrs['time']}"
        strength = node.attrs.get("strength", "strong")
        marker = SSMD_BREAK_STRENGTH_MAP.get(strength, "...s")
        return marker
    if isinstance(node, MarkNode):
        return f"@{node.name}"
    raise FormatError(
        (_format_diagnostic("format.node_unsupported", f"Cannot format {type(node).__name__}."),)
    )


def _canonical_block_separator(previous: Node, current: Node, source: str) -> str:
    gap = source[previous.source_end : current.source_start]
    if _is_tight_directive_transition(previous, current, gap):
        return "\n"
    return "\n\n"


def _render_block_sequence(nodes: tuple[Node, ...], source: str) -> str:
    output: list[str] = []
    previous: Node | None = None
    for node in nodes:
        if previous is not None:
            output.append(_canonical_block_separator(previous, node, source))
        output.append(_render_block_node(node, source))
        previous = node
    return "".join(output)


def _render_block_node(node: Node, source: str) -> str:
    if isinstance(node, ParagraphNode):
        return "".join(_render_inline_node(child, source) for child in node.children)
    if isinstance(node, HeadingNode):
        content = "".join(_render_inline_node(child, source) for child in node.children)
        return f"{'#' * node.level} {content}"
    if isinstance(node, DirectiveNode):
        nested = max((_nested_fence_length(child) for child in node.children), default=0)
        body = _render_block_sequence(node.children, source)
        return _render_directive(node.attrs, body, nested_fence_length=nested)
    return _render_inline_node(node, source)


def _semantic_signature(text: str, *, parse_yaml_header: bool = True) -> tuple[object, ...]:
    from ssmd.parser import parse_structure

    structure = parse_structure(text, dialect="0.9", parse_yaml_header=parse_yaml_header)
    if any(item.severity == "error" for item in structure.diagnostics):
        raise FormatError(tuple(structure.diagnostics))
    annotations = tuple(
        sorted(
            (
                item.char_start,
                item.char_end,
                tuple(sorted(item.attrs.items())),
            )
            for item in structure.annotations
        )
    )
    events = tuple(
        (item.pos, item.kind, item.anchor, tuple(sorted(item.attrs.items())))
        for item in structure.events
    )
    header = dict(structure.header)
    header.pop("ssmd_version", None)
    return structure.clean_text, annotations, events, header


def format_canonical(
    text: str, *, add_version: bool = False, parse_yaml_header: bool = True
) -> str:
    """Format strict SSMD 0.9 syntax without performing a legacy migration."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if parse_yaml_header:
        try:
            front_matter = parse_front_matter(normalized)
        except FrontMatterError as exc:
            raise FormatError(
                (_format_diagnostic(exc.code, str(exc), line=exc.line, column=exc.column),)
            ) from exc
    else:
        if add_version:
            raise ValueError("add_version requires YAML front matter parsing")
        front_matter = FrontMatter({}, normalized, False)
    header = dict(front_matter.data)
    if header.get("ssmd_version", "0.9") != "0.9":
        raise FormatError(
            (
                _format_diagnostic(
                    "format.unsupported_version",
                    "Canonical formatting supports only SSMD 0.9 documents.",
                ),
            )
        )
    if add_version:
        header["ssmd_version"] = "0.9"
    header_issues = validate_front_matter(header, dialect="0.9")
    header_errors = tuple(
        _format_diagnostic(
            issue.code,
            issue.message,
            line=issue.line,
            column=issue.column,
        )
        for issue in header_issues
        if issue.severity == "error"
    )
    if header_errors:
        raise FormatError(header_errors)

    body = front_matter.body
    tokens, diagnostics = tokenize_blocks(body, dialect="0.9")
    if diagnostics:
        raise FormatError(tuple(diagnostics))
    syntax_tree = ast_from_tokens(tokens, source_start=0, source_end=len(body))
    formatted_body = _render_block_sequence(syntax_tree.children, body).rstrip("\n")
    if formatted_body:
        formatted_body += "\n"
    if front_matter.present or add_version:
        formatted = serialize_front_matter(header, formatted_body)
        if formatted and not formatted.endswith("\n"):
            formatted += "\n"
    else:
        formatted = formatted_body
    if _semantic_signature(normalized, parse_yaml_header=parse_yaml_header) != _semantic_signature(
        formatted, parse_yaml_header=parse_yaml_header
    ):
        raise FormatError(
            (
                _format_diagnostic(
                    "format.semantic_mismatch",
                    "Canonical formatting changed declared SSMD semantics.",
                ),
            )
        )
    return formatted


def normalize_line_endings(text: str) -> str:
    """Normalize CRLF and CR line endings to LF without formatting SSMD syntax."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def format_source(text: str) -> str:
    """Preserve SSMD syntax and dialect while normalizing line endings."""
    return normalize_line_endings(text)


def format_ssmd(sentences: list[Sentence]) -> str:
    """Format parsed SSMD sentences with proper line breaks.

    This function takes a list of parsed Sentence objects and formats them
    according to SSMD formatting conventions:

    - Each sentence on a new line (after . ? !)
    - Break markers at sentence boundaries: end of previous line
    - Break markers mid-sentence: stay inline between segments
    - Paragraph breaks: double newline
    - Directive blocks: separate line with blank line after
    - Headings: blank lines before and after

    Args:
        sentences: List of parsed Sentence objects

    Returns:
        Properly formatted SSMD string

    Example:
        >>> from ssmd.parser import parse_sentences
        >>> sentences = parse_sentences("Hello. How are you?")
        >>> formatted = format_ssmd(sentences)
        >>> print(formatted, end="")
        Hello.
        How are you?
    """
    if not sentences:
        return ""

    output_lines: list[str] = []
    previous_directive: tuple[VoiceAttrs | None, str | None, ProsodyAttrs | None] = (
        None,
        None,
        None,
    )

    for i, sentence in enumerate(sentences):
        directive_key = (sentence.voice, sentence.language, sentence.prosody)
        if directive_key != previous_directive:
            if previous_directive != (None, None, None):
                output_lines.append("</div>")
                output_lines.append("")

            if any(directive_key):
                directive = _format_div_directive(sentence)
                if directive:
                    if output_lines and output_lines[-1] != "":
                        output_lines.append("")
                    output_lines.append(directive)
            previous_directive = directive_key

        # Check if sentence has breaks_before (from previous sentence boundary)
        # These should be appended to the previous line, then suppressed while
        # rendering the current sentence so they are emitted exactly once.
        leading_breaks_moved = False
        if i > 0 and sentence.segments and sentence.segments[0].breaks_before:
            if output_lines:
                break_marker = _format_breaks(sentence.segments[0].breaks_before)
                output_lines[-1] += " " + break_marker
                leading_breaks_moved = True

        # Format the sentence using to_ssmd()
        sentence_text = _format_sentence_content(
            sentence, suppress_leading_breaks=leading_breaks_moved
        )

        if sentence_text:
            output_lines.append(sentence_text)

            # Add paragraph break if needed
            if sentence.is_paragraph_end:
                output_lines.append("")  # Extra blank line for paragraph

    if previous_directive != (None, None, None):
        if output_lines and output_lines[-1] != "":
            output_lines.append("")
        output_lines.append("</div>")
        output_lines.append("")

    # Join lines and ensure trailing newline
    result = "\n".join(output_lines)

    # Clean up multiple consecutive blank lines (max 1 blank line)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    return result.rstrip() + "\n" if result else ""


def _format_sentence_content(sentence: Sentence, *, suppress_leading_breaks: bool = False) -> str:
    """Format a single sentence's content (segments only).

    Args:
        sentence: Sentence object to format

    Returns:
        Formatted sentence text with inline and trailing breaks
    """
    if not sentence.segments:
        return ""

    # Build segments using their to_ssmd() method
    result_parts: list[str] = []

    for segment_index, segment in enumerate(sentence.segments):
        # A sentence-boundary break may already have been moved to the previous
        # output line. Render a copy without that leading break to avoid duplication.
        render_segment = segment
        if suppress_leading_breaks and segment_index == 0 and segment.breaks_before:
            render_segment = replace(segment, breaks_before=[])

        # Format the segment using its to_ssmd() method
        segment_text = render_segment.to_ssmd()

        # Preserve the trailing space if segment has breaks_after
        if segment.breaks_after:
            segment_text = segment_text.rstrip() + " "
        else:
            segment_text = segment_text.strip()

        if not segment_text.strip():
            continue

        # Add this segment
        result_parts.append(segment_text)

    # Join segments intelligently
    sentence_text = ""
    for i, part in enumerate(result_parts):
        if i == 0:
            sentence_text = part
        elif part.startswith("..."):
            # This is a break marker - append without extra space
            sentence_text += part
        elif i > 0 and _ends_with_break_marker(result_parts[i - 1]):
            # Previous part ends with break marker, already has space
            sentence_text += part
        elif i > 0 and result_parts[i - 1].endswith((" ", "\n")):
            # Previous part ends with whitespace
            sentence_text += part
        else:
            # Normal text segment - add space
            sentence_text += " " + part

    # Add sentence-level breaks at end of line
    if sentence.breaks_after:
        break_marker = _format_breaks(sentence.breaks_after)
        sentence_text += " " + break_marker

    return sentence_text.strip()


def _ends_with_break_marker(text: str) -> bool:
    """Check if text ends with a break marker like ...s, ...500ms, etc."""
    import re

    # Break marker pattern: ... followed by strength letter or time
    return bool(re.search(r"\.\.\.[swcpn]$|\.\.\.\d+(ms|s)$", text.rstrip()))


def _format_breaks(breaks: list[BreakAttrs]) -> str:
    """Convert break attributes to SSMD break markers.

    Args:
        breaks: List of BreakAttrs objects

    Returns:
        SSMD break marker string (e.g., "...s", "...500ms")
    """
    if not breaks:
        return ""

    # Format each break
    break_markers = []
    for brk in breaks:
        if brk.time:
            # Time-based break: ...500ms or ...2s
            break_markers.append(f"...{brk.time}")
        elif brk.strength:
            # Strength-based break
            marker = SSMD_BREAK_STRENGTH_MAP.get(brk.strength, "...s")
            break_markers.append(marker)
        else:
            # Default to strong break
            break_markers.append("...s")

    return " ".join(break_markers)


def _format_div_directive(sentence: Sentence) -> str:
    """Format a <div> directive for voice/lang/prosody."""
    from ssmd.segment import _escape_xml_attr

    parts: list[str] = []

    if sentence.voice:
        if sentence.voice.name:
            parts.append(f'voice="{_escape_xml_attr(sentence.voice.name)}"')
        if sentence.voice.language:
            parts.append(f'voice-lang="{_escape_xml_attr(sentence.voice.language)}"')
        if sentence.voice.gender:
            parts.append(f'gender="{_escape_xml_attr(sentence.voice.gender)}"')
        if sentence.voice.variant is not None:
            parts.append(f'variant="{sentence.voice.variant}"')

    if sentence.language:
        parts.append(f'lang="{_escape_xml_attr(sentence.language)}"')

    if sentence.prosody:
        if sentence.prosody.volume:
            parts.append(f'volume="{_escape_xml_attr(sentence.prosody.volume)}"')
        if sentence.prosody.rate:
            parts.append(f'rate="{_escape_xml_attr(sentence.prosody.rate)}"')
        if sentence.prosody.pitch:
            parts.append(f'pitch="{_escape_xml_attr(sentence.prosody.pitch)}"')

    if not parts:
        return ""

    return f"<div {' '.join(parts)}>"

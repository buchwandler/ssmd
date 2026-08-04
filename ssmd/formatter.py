"""SSMD formatting utilities for properly formatted output.

This module provides utilities to format parsed SSMD sentences with proper
line breaks, paragraph spacing, and structural elements according to SSMD
formatting conventions.
"""

from dataclasses import replace

from ssmd.segment import Segment
from ssmd.sentence import Sentence
from ssmd.ssml_conversions import SSMD_BREAK_STRENGTH_MAP
from ssmd.types import BreakAttrs, ProsodyAttrs, VoiceAttrs

# Backward compatibility aliases
SSMDSentence = Sentence
SSMDSegment = Segment


def format_source(text: str) -> str:
    """Apply the safe, source-preserving formatter contract.

    ``fmt`` deliberately does not serialize the semantic document model. It
    preserves headings, front matter, directives, annotations, escapes, and
    literal text, while normalizing only CRLF/CR line endings to LF. The final
    newline state is preserved, so the operation is deterministic and
    idempotent without silently changing the document's structure.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


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

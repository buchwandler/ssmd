"""SSMD parser - Parse SSMD text into structured Sentence/Segment objects.

This module provides functions to parse SSMD markdown into structured data
that can be used for TTS processing or conversion to SSML.
"""

import math
import re
import warnings
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, cast

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
    ast_from_tokens,
)
from ssmd.paragraph import Paragraph
from ssmd.segment import Segment
from ssmd.sentence import Sentence
from ssmd.spans import (
    AnnotationSpan,
    Diagnostic,
    LintIssue,
    ParseSpansResult,
    ParseStructureResult,
    StructuralEvent,
    diagnostics_from_warnings,
)
from ssmd.ssml_conversions import (
    PROSODY_PITCH_MAP,
    PROSODY_RATE_MAP,
    PROSODY_VOLUME_MAP,
    SSMD_BREAK_MARKER_TO_STRENGTH,
    normalize_pitch_value,
    normalize_rate_value,
)
from ssmd.tokenizer import tokenize_blocks
from ssmd.types import (
    DEFAULT_HEADING_LEVELS,
    AudioAttrs,
    BreakAttrs,
    DirectiveAttrs,
    ParsedResult,
    PhonemeAttrs,
    ProsodyAttrs,
    SayAsAttrs,
    SentenceDetectionConfig,
    SentenceDetectionDiagnostics,
    SpacyModelSize,
    VoiceAttrs,
    VoiceDefaults,
    VoiceProsodyDefaults,
)
from ssmd.utils import unescape_ssmd_syntax
from ssmd.validation import validate_token_semantics

if TYPE_CHECKING:
    from ssmd.capabilities import TTSCapabilities


# ═══════════════════════════════════════════════════════════════════════════════
# REGEX PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# Directive blocks: <div key="value"> ... </div>
DIV_DIRECTIVE_INLINE = re.compile(r"^\s*<div\s+([^>]+)>(.*?)</div>\s*$", re.IGNORECASE)
DIV_DIRECTIVE_START = re.compile(r"^\s*<div\s+([^>]+)>\s*$", re.IGNORECASE)
DIV_DIRECTIVE_END = re.compile(r"^\s*</div>\s*$", re.IGNORECASE)

# Emphasis patterns
STRONG_EMPHASIS_PATTERN = re.compile(r"\*\*([^\*]+)\*\*")
MODERATE_EMPHASIS_PATTERN = re.compile(r"\*([^\*]+)\*")
REDUCED_EMPHASIS_PATTERN = re.compile(r"(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)")
TILDE_REDUCED_EMPHASIS_PATTERN = re.compile(r"~~([^~]+)~~")

# Symbolic prosody patterns
X_LOUD_PROSODY_PATTERN = re.compile(r"(?<!\+)\+\+([^+\n]+?)\+\+(?!\+)")
X_FAST_PROSODY_PATTERN = re.compile(r"(?<!>)>>([^>\n]+?)>>(?!>)")
X_HIGH_PROSODY_PATTERN = re.compile(r"(?<!\^)\^\^([^\^\n]+?)\^\^(?!\^)")
SILENT_VOLUME_PATTERN = re.compile(r"(?<!~)~([^~\n]+?)~(?!~)")
X_SOFT_VOLUME_PATTERN = re.compile(r"(?<!-)--([^-\n]+?)--(?!-)")
SOFT_VOLUME_PATTERN = re.compile(r"(?<![\w-])-([^-\n]+?)-(?![\w-])")
LOUD_VOLUME_PATTERN = re.compile(r"(?<!\+)\+([^+\n]+?)\+(?!\+)")
X_SLOW_RATE_PATTERN = re.compile(r"(?<!<)<<([^<\n]+?)<<(?!<)")
SLOW_RATE_PATTERN = re.compile(r"(?<!<)<([^<\n]+?)<(?!<)")
FAST_RATE_PATTERN = re.compile(r"(?<!>)>([^>\n]+?)>(?!>)")
X_LOW_PITCH_PATTERN = re.compile(r"(?<!_)__([^_\n]+?)__(?!_)")
HIGH_PITCH_PATTERN = re.compile(r"(?<!\^)\^([^\^\n]+?)\^(?!\^)")

SYMBOLIC_PROSODY_RULES = (
    (X_LOUD_PROSODY_PATTERN, "volume", "x-loud"),
    (X_FAST_PROSODY_PATTERN, "rate", "x-fast"),
    (X_HIGH_PROSODY_PATTERN, "pitch", "x-high"),
    (SILENT_VOLUME_PATTERN, "volume", "silent"),
    (X_SOFT_VOLUME_PATTERN, "volume", "x-soft"),
    (SOFT_VOLUME_PATTERN, "volume", "soft"),
    (LOUD_VOLUME_PATTERN, "volume", "loud"),
    (X_SLOW_RATE_PATTERN, "rate", "x-slow"),
    (SLOW_RATE_PATTERN, "rate", "slow"),
    (FAST_RATE_PATTERN, "rate", "fast"),
    (X_LOW_PITCH_PATTERN, "pitch", "x-low"),
    (HIGH_PITCH_PATTERN, "pitch", "high"),
)
SYMBOLIC_PROSODY_PATTERNS = tuple(rule[0] for rule in SYMBOLIC_PROSODY_RULES)

# Protect complete inline markup spans while phrasplit decides sentence
# boundaries. Sentence punctuation inside a span must not be mistaken for a
# boundary before the closing delimiter is restored.
INLINE_SENTENCE_MARKUP_PATTERNS = (
    STRONG_EMPHASIS_PATTERN,
    MODERATE_EMPHASIS_PATTERN,
    TILDE_REDUCED_EMPHASIS_PATTERN,
    REDUCED_EMPHASIS_PATTERN,
    *SYMBOLIC_PROSODY_PATTERNS,
)
# Annotation pattern: [text]{key="value"}
ANNOTATION_PATTERN = re.compile(r"\[([^\]]*)\]\{((?:\\.|[^}])*)\}")

# Break pattern: ...500ms, ...2s, ...n, ...w, ...c, ...s, ...p
BREAK_PATTERN = re.compile(r"\.\.\.(\d+(?:\.\d+)?(?:s|ms)|[nwcsp])(?=\s|$|[.!?,;:])")

# Mark pattern: @name
MARK_PATTERN = re.compile(r"(?<!\S)@(\w+)(?=\s|$)")

INLINE_MARKUP_TOKEN_PATTERN = re.compile(
    "|".join(
        f"(?:{pattern.pattern})"
        for pattern in (
            STRONG_EMPHASIS_PATTERN,
            MODERATE_EMPHASIS_PATTERN,
            TILDE_REDUCED_EMPHASIS_PATTERN,
            REDUCED_EMPHASIS_PATTERN,
            *SYMBOLIC_PROSODY_PATTERNS,
            ANNOTATION_PATTERN,
            BREAK_PATTERN,
            MARK_PATTERN,
        )
    )
)
# Heading pattern: # ## ###
HEADING_PATTERN = re.compile(r"^\s*(#{1,6})\s*(.+)$", re.MULTILINE)

# Paragraph break: two or more newlines
PARAGRAPH_PATTERN = re.compile(r"\n\n+")

# Space before punctuation (to normalize). Preserve leading decimals like ".2".
SPACE_BEFORE_PUNCT = re.compile(r"\s+([!?,:;]|\.(?!\d))")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PARSING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def _normalize_text(text: str) -> str:
    """Normalize text by removing extra whitespace and fixing spacing.

    - Removes space before punctuation
    - Collapses multiple spaces
    """
    text = SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_paragraphs(
    text: str,
    *,
    capabilities: "TTSCapabilities | str | None" = None,
    heading_levels: dict | None = None,
    extensions: dict | None = None,
    sentence_detection: bool = True,
    language: str | None = None,
    use_spacy: bool | None = None,
    spacy_model: str | None = None,
    model_size: SpacyModelSize | None = None,
    parse_yaml_header: bool = True,
    strict_parse: bool = False,
) -> ParsedResult[Paragraph]:
    """Parse SSMD text into a list of Paragraphs.

    This is the main parsing function. It handles:
    - Directive blocks (<div ...> ... </div>)
    - Paragraph and sentence splitting
    - All SSMD markup (emphasis, annotations, breaks, etc.)

    Args:
        text: SSMD markdown text
        capabilities: TTS capabilities for filtering (optional)
        heading_levels: Custom heading configurations
        extensions: Custom extension handlers
        sentence_detection: If True, split text into sentences
        language: Default language for sentence detection
        use_spacy: If True, use spaCy for sentence detection
        spacy_model: Exact spaCy package name, if supplied
        model_size: Exact spaCy model size ("sm", "md", "lg", "trf"), if supplied
        parse_yaml_header: If True, parse YAML front matter and apply
            heading/extensions config while stripping it from the body. If False,
            YAML front matter is preserved as plain text.
        strict_parse: If True, strip unsupported features based on capabilities.

    Returns:
        List of Paragraph objects
    """
    sentence_config = SentenceDetectionConfig(
        use_spacy=use_spacy,
        spacy_model=spacy_model,
        model_size=model_size,
    )
    if not text or not text.strip():
        return ParsedResult()

    from ssmd.frontmatter import parse_front_matter
    from ssmd.utils import build_config_from_header

    if parse_yaml_header:
        front_matter = parse_front_matter(text)
        if front_matter.present:
            header_config = build_config_from_header(front_matter.data)
            heading_levels = header_config.get("heading_levels", heading_levels)
            extensions = header_config.get("extensions", extensions)
            text = front_matter.body

    # Resolve capabilities
    caps = _resolve_capabilities(capabilities)

    # Split text into directive blocks
    directive_blocks = _split_directive_blocks(text)

    paragraphs: list[Paragraph] = []
    paragraph_index = 0
    sentence_index = 0
    detection_diagnostics: SentenceDetectionDiagnostics | None = None

    for block_index, (directive, block_text) in enumerate(directive_blocks):
        is_last_block = block_index == len(directive_blocks) - 1
        # Split block into paragraphs
        block_paragraphs = PARAGRAPH_PATTERN.split(block_text)

        for para_idx, paragraph in enumerate(block_paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            is_last_paragraph = para_idx == len(block_paragraphs) - 1
            paragraph_boundary = not is_last_paragraph or not is_last_block

            # Split paragraph into sentences if enabled
            if sentence_detection:
                split_result = _split_sentences(
                    paragraph,
                    language=language,
                    use_spacy=use_spacy,
                    spacy_model=sentence_config.spacy_model,
                    model_size=sentence_config.model_size,
                )
                sent_texts: list[str] = list(split_result)
                detection_diagnostics = split_result.diagnostics
            else:
                sent_texts = [paragraph]

            paragraph_sentences: list[Sentence] = []

            for sent_idx, sent_text in enumerate(sent_texts):
                sent_text = sent_text.strip()
                if not sent_text:
                    continue

                is_last_sent_in_para = sent_idx == len(sent_texts) - 1

                # Parse the sentence content into segments
                segments = _parse_segments(
                    sent_text,
                    capabilities=caps,
                    heading_levels=heading_levels,
                    extensions=extensions,
                )

                if segments:
                    sentence = Sentence(
                        segments=segments,
                        voice=directive.voice,
                        language=directive.language,
                        prosody=directive.prosody,
                        is_paragraph_end=is_last_sent_in_para and paragraph_boundary,
                        paragraph_index=paragraph_index,
                        sentence_index=sentence_index,
                    )
                    paragraph_sentences.append(sentence)
                    sentence_index += 1

            if paragraph_sentences:
                paragraphs.append(Paragraph(sentences=paragraph_sentences))
                paragraph_index += 1

    if strict_parse and caps:
        all_sentences = [sentence for paragraph in paragraphs for sentence in paragraph.sentences]
        _filter_sentences(all_sentences, caps)

    return ParsedResult(paragraphs, diagnostics=detection_diagnostics)


def parse_ssmd(
    text: str,
    *,
    capabilities: "TTSCapabilities | str | None" = None,
    heading_levels: dict | None = None,
    extensions: dict | None = None,
    sentence_detection: bool = True,
    language: str | None = None,
    use_spacy: bool | None = None,
    spacy_model: str | None = None,
    model_size: SpacyModelSize | None = None,
    parse_yaml_header: bool = True,
    strict_parse: bool = False,
) -> ParsedResult[Paragraph]:
    """Parse SSMD text into paragraphs (backward compatible name).

    This is an alias for parse_paragraphs().
    """
    return parse_paragraphs(
        text,
        capabilities=capabilities,
        heading_levels=heading_levels,
        extensions=extensions,
        sentence_detection=sentence_detection,
        language=language,
        use_spacy=use_spacy,
        spacy_model=spacy_model,
        model_size=model_size,
        parse_yaml_header=parse_yaml_header,
        strict_parse=strict_parse,
    )


def _resolve_capabilities(
    capabilities: "TTSCapabilities | str | None",
) -> "TTSCapabilities | None":
    """Resolve capabilities from string or object."""
    if capabilities is None:
        return None
    if isinstance(capabilities, str):
        from ssmd.capabilities import get_preset

        return get_preset(capabilities)
    return capabilities


def _split_directive_blocks(text: str) -> list[tuple[DirectiveAttrs, str]]:
    """Split text into directive blocks defined by <div ...> tags."""
    blocks: list[tuple[DirectiveAttrs, str]] = []
    stack: list[DirectiveAttrs] = [DirectiveAttrs()]
    current_lines: list[str] = []

    def flush_block() -> None:
        if not current_lines:
            return
        block_text = "\n".join(current_lines)
        if block_text.strip():
            blocks.append((stack[-1], block_text))
        current_lines.clear()

    for line in text.split("\n"):
        inline_match = DIV_DIRECTIVE_INLINE.match(line)
        if inline_match:
            flush_block()
            attrs = _parse_div_attrs(inline_match.group(1))
            directive = _merge_directives(stack[-1], attrs)
            blocks.append((directive, inline_match.group(2)))
            continue

        start_match = DIV_DIRECTIVE_START.match(line)
        if start_match:
            flush_block()
            attrs = _parse_div_attrs(start_match.group(1))
            stack.append(_merge_directives(stack[-1], attrs))
            continue

        if DIV_DIRECTIVE_END.match(line):
            if len(stack) > 1:
                flush_block()
                stack.pop()
                continue
            current_lines.append(line)
            continue

        current_lines.append(line)

    flush_block()

    if not blocks and text.strip():
        blocks.append((DirectiveAttrs(), text.strip()))

    return blocks


def _split_directive_blocks_with_warnings(
    text: str,
) -> tuple[list[tuple[DirectiveAttrs, str]], list[str]]:
    """Split directive blocks and collect parse warnings."""
    blocks: list[tuple[DirectiveAttrs, str]] = []
    warnings: list[str] = []
    stack: list[DirectiveAttrs] = [DirectiveAttrs()]
    current_lines: list[str] = []

    def flush_block() -> None:
        if not current_lines:
            return
        block_text = "\n".join(current_lines)
        if block_text.strip():
            blocks.append((stack[-1], block_text))
        current_lines.clear()

    for line in text.split("\n"):
        inline_match = DIV_DIRECTIVE_INLINE.match(line)
        if inline_match:
            flush_block()
            attrs = _parse_div_attrs(inline_match.group(1))
            directive = _merge_directives(stack[-1], attrs)
            blocks.append((directive, inline_match.group(2)))
            continue

        start_match = DIV_DIRECTIVE_START.match(line)
        if start_match:
            flush_block()
            attrs = _parse_div_attrs(start_match.group(1))
            stack.append(_merge_directives(stack[-1], attrs))
            continue

        if DIV_DIRECTIVE_END.match(line):
            if len(stack) > 1:
                flush_block()
                stack.pop()
                continue
            warnings.append("Unexpected </div> without matching <div>.")
            current_lines.append(line)
            continue

        current_lines.append(line)

    flush_block()

    if len(stack) > 1:
        warnings.append("Unclosed <div> directive block.")

    if not blocks and text.strip():
        blocks.append((DirectiveAttrs(), text.strip()))

    return blocks, warnings


def _parse_div_attrs(params: str) -> DirectiveAttrs:
    """Parse <div ...> attribute params into directive attrs."""
    params_map = _parse_annotation_params(params)
    directive = DirectiveAttrs()

    language = params_map.get("lang") or params_map.get("language")
    if language:
        directive.language = language

    voice = _parse_voice_annotation_params(params_map)
    if voice:
        directive.voice = voice

    if "voice" in params_map and directive.voice:
        directive.voice.name = params_map["voice"]

    prosody = _parse_prosody_params(params_map)
    if prosody:
        directive.prosody = prosody

    return directive


def _merge_directives(base: DirectiveAttrs, update: DirectiveAttrs) -> DirectiveAttrs:
    """Merge directive attributes for nested <div> blocks."""
    merged_voice = _merge_voice(base.voice, update.voice)
    merged_prosody = _merge_prosody(base.prosody, update.prosody)
    language = update.language or base.language
    return DirectiveAttrs(
        voice=merged_voice,
        language=language,
        prosody=merged_prosody,
    )


def _merge_voice(base: VoiceAttrs | None, update: VoiceAttrs | None) -> VoiceAttrs | None:
    if base is None and update is None:
        return None

    merged = VoiceAttrs()
    for field_name in ("name", "language", "gender", "variant", "selector_name", "age"):
        update_value = getattr(update, field_name) if update else None
        if update_value in (None, ""):
            update_value = None
        base_value = getattr(base, field_name) if base else None
        setattr(merged, field_name, update_value if update_value is not None else base_value)

    if not any(
        [
            merged.name,
            merged.language,
            merged.gender,
            merged.variant is not None,
            merged.selector_name,
            merged.age is not None,
        ]
    ):
        return None
    return merged


def _merge_prosody(
    base: ProsodyAttrs | None,
    update: ProsodyAttrs | None,
) -> ProsodyAttrs | None:
    if base is None and update is None:
        return None

    merged = ProsodyAttrs()
    for field_name in ("volume", "rate", "pitch"):
        update_value = getattr(update, field_name) if update else None
        if update_value in (None, ""):
            update_value = None
        base_value = getattr(base, field_name) if base else None
        setattr(merged, field_name, update_value if update_value is not None else base_value)
        if field_name in ("rate", "pitch"):
            flag_name = f"legacy_{field_name}"
            flag_value = (
                getattr(update, flag_name, False)
                if update_value is not None
                else (getattr(base, flag_name, False) if base else False)
            )
            setattr(merged, flag_name, flag_value)
    if not any([merged.volume, merged.rate, merged.pitch]):
        return None
    return merged


def resolve_voice_prosody(
    voice: VoiceAttrs | None,
    declared: ProsodyAttrs | None,
    voice_defaults: Mapping[str, VoiceProsodyDefaults] | VoiceDefaults,
    *,
    inherited: ProsodyAttrs | None = None,
) -> ProsodyAttrs | None:
    """Resolve effective prosody without mutating declared parser state.

    Fields are resolved independently. ``inherited`` represents an enclosing
    directive and is weaker than the current declaration but stronger than a
    logical voice default.
    """
    default = None
    if voice and voice.name:
        default = voice_defaults.get(voice.name)
    if declared is None and inherited is None and default is None:
        return None

    effective = ProsodyAttrs()
    for field_name in ("volume", "rate", "pitch"):
        declared_value = getattr(declared, field_name, None) if declared else None
        inherited_value = getattr(inherited, field_name, None) if inherited else None
        default_value = getattr(default, field_name, None) if default else None
        value = declared_value or inherited_value or default_value
        setattr(effective, field_name, value)
        if field_name in ("rate", "pitch") and declared_value is not None and declared:
            setattr(
                effective, f"legacy_{field_name}", getattr(declared, f"legacy_{field_name}", False)
            )
    if not any((effective.volume, effective.rate, effective.pitch)):
        return None
    return effective


def voice_prosody_sources(
    voice: VoiceAttrs | None,
    declared: ProsodyAttrs | None,
    voice_defaults: Mapping[str, VoiceProsodyDefaults] | VoiceDefaults,
    *,
    inherited: ProsodyAttrs | None = None,
    inline: bool = False,
) -> dict[str, str]:
    """Return the source of each resolved prosody field for inspection."""
    default = voice_defaults.get(voice.name) if voice and voice.name else None
    sources: dict[str, str] = {}
    for field_name in ("volume", "rate", "pitch"):
        if declared and getattr(declared, field_name):
            sources[field_name] = "inline" if inline else "directive"
        elif inherited and getattr(inherited, field_name):
            sources[field_name] = "inherited_directive"
        elif default and getattr(default, field_name):
            sources[field_name] = "voice_default"
        else:
            sources[field_name] = "engine_default"
    return sources


def _sentence_detection_selection(
    config: SentenceDetectionConfig,
) -> tuple[str, SpacyModelSize | None]:
    """Return the effective backend mode and model-size forwarding value."""
    if config.use_spacy is False and (config.spacy_model or config.model_size):
        warnings.warn(
            "spaCy model settings are ignored when use_spacy=False.",
            UserWarning,
            stacklevel=3,
        )
    if config.spacy_model and config.model_size and config.use_spacy is not False:
        warnings.warn(
            "model_size is ignored when an explicit model is supplied.",
            UserWarning,
            stacklevel=3,
        )
    if config.use_spacy is False:
        selection_mode = "regex"
    elif config.spacy_model:
        selection_mode = "explicit_model"
    elif config.model_size:
        selection_mode = "explicit_size"
    else:
        selection_mode = "automatic"
    effective_model_size = None if config.spacy_model else config.model_size
    return selection_mode, effective_model_size


def _split_sentences(
    text: str,
    language: str | None = None,
    use_spacy: bool | None = None,
    spacy_model: str | None = None,
    model_size: SpacyModelSize | None = None,
    *,
    escape_annotations: bool = True,
) -> ParsedResult[str]:
    """Split text into sentences using phrasplit."""
    sentence_config = SentenceDetectionConfig(
        use_spacy=use_spacy,
        spacy_model=spacy_model,
        model_size=model_size,
    )
    try:
        import phrasplit
    except ImportError:
        return ParsedResult(
            _simple_sentence_split(text),
            diagnostics=SentenceDetectionDiagnostics(
                selection_mode="fallback",
                effective_language=language or "en",
            ),
        )

    language_hint = language or "en"
    selection_mode, effective_model_size = _sentence_detection_selection(sentence_config)
    should_escape = escape_annotations
    escaped_text = text
    placeholder_values: list[str] = []
    placeholder_tokens: list[str] = []
    if should_escape:
        placeholder_base = 0xF100

        def _replace_placeholder(match: re.Match[str]) -> str:
            placeholder_values.append(match.group(0))
            placeholder = chr(placeholder_base + len(placeholder_values) - 1)
            placeholder_tokens.append(placeholder)
            return placeholder

        escaped_text = re.sub(r"\[[^\]]*\]\{(?:\\.|[^}])*\}", _replace_placeholder, escaped_text)
        escaped_text = re.sub(
            r"\.\.\.(?:\d+(?:\.\d+)?(?:s|ms)|[nwcsp])(?=\s|$|[.!?,;:])",
            _replace_placeholder,
            escaped_text,
        )
        for markup_pattern in INLINE_SENTENCE_MARKUP_PATTERNS:
            escaped_text = markup_pattern.sub(_replace_placeholder, escaped_text)

    split_result = phrasplit.split_text_with_diagnostics(
        escaped_text,
        mode="sentence",
        language_model=sentence_config.spacy_model,
        apply_corrections=True,
        split_on_colon=True,
        use_spacy=sentence_config.use_spacy,
        language=language_hint,
        model_size=effective_model_size,
    )
    backend = split_result.diagnostics
    resolution = backend.resolution
    diagnostics = SentenceDetectionDiagnostics(
        selection_mode=selection_mode,
        effective_language=backend.language,
        selected_model=resolution.selected_model if resolution else None,
        selected_model_size=resolution.model_size if resolution else None,
    )
    segments = split_result.segments

    # Group segments by sentence.
    sentences = []
    current = ""
    last_sent_id = None

    for seg in segments:
        if last_sent_id is not None and seg.sentence != last_sent_id:
            if current.strip():
                sentences.append(current)
            current = ""
        current += seg.text
        last_sent_id = seg.sentence

    if current.strip():
        sentences.append(current)

    line_boundary_sentences: list[str] = []
    for sentence in sentences:
        line_boundary_sentences.extend(_split_line_sentence_boundaries(sentence))
    sentences = [sentence for sentence in line_boundary_sentences if sentence.strip()]
    sentences = _merge_nonterminal_fragments(sentences)

    if not should_escape:
        return ParsedResult(sentences if sentences else [text], diagnostics=diagnostics)

    if not sentences:
        return ParsedResult([text], diagnostics=diagnostics)

    restored_sentences: list[str] = []
    for sentence in sentences:
        restored = sentence
        for placeholder_index, original_value in enumerate(placeholder_values):
            restored = restored.replace(placeholder_tokens[placeholder_index], original_value)
        restored_sentences.append(restored)

    merged_sentences: list[str] = []
    break_only_pattern = re.compile(r"^(?:\.\.\.(?:\d+(?:\.\d+)?(?:s|ms)|[nwcsp])\s*)+$")
    for sentence in restored_sentences:
        stripped = sentence.strip()
        if stripped and break_only_pattern.match(stripped) and merged_sentences:
            merged_sentences[-1] = merged_sentences[-1].rstrip() + " " + stripped
        else:
            merged_sentences.append(sentence)

    for idx, sentence in enumerate(merged_sentences[:-1]):
        merged_sentences[idx] = sentence.rstrip() + "\n"

    merged_sentences = _merge_single_letter_abbreviations(merged_sentences)
    return ParsedResult(merged_sentences, diagnostics=diagnostics)


def _merge_single_letter_abbreviations(sentences: list[str]) -> list[str]:
    """Keep a run of single-letter abbreviations in one sentence."""
    merged: list[str] = []
    single_letter = re.compile(r"^(?:[A-Za-z]\.)+$")
    for sentence in sentences:
        if (
            merged
            and single_letter.fullmatch(merged[-1].strip())
            and single_letter.fullmatch(sentence.strip())
        ):
            merged[-1] = f"{merged[-1].rstrip()} {sentence.lstrip()}"
        else:
            merged.append(sentence)
    return merged


def _split_line_sentence_boundaries(text: str) -> list[str]:
    """Preserve SSMD line and heading boundaries lost by model segmentation."""
    lines: list[str] = []
    for line in re.split(r"\n+", text):
        lines.extend(re.split(r"(?<=[!?])\s+(?=[A-Z])", line))
    if len(lines) == 1:
        return lines

    parts: list[str] = []
    current = lines[0]
    heading = re.compile(r"^\s*#{1,6}\s+")
    for line in lines[1:]:
        current_stripped = current.strip()
        if (
            re.search(r"[.!?]\s*$", current_stripped)
            or heading.match(current_stripped)
            or heading.match(line)
        ):
            parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}"
    parts.append(current)
    return parts


def _merge_nonterminal_fragments(sentences: list[str]) -> list[str]:
    """Reassemble long-text chunks that phrasplit kept without punctuation."""
    merged: list[str] = []
    heading_marker = re.compile(r"^\s*#{1,6}\s*$")
    for sentence in sentences:
        if merged and heading_marker.fullmatch(merged[-1]):
            marker = merged.pop().strip()
            heading_line, separator, remainder = sentence.partition("\n")
            merged.append(f"{marker} {heading_line.strip()}")
            if separator and remainder.strip():
                merged.append(remainder)
            continue
        if merged and not re.search(r"[.!?]\s*$", merged[-1].strip()):
            merged[-1] = f"{merged[-1].rstrip()} {sentence.lstrip()}"
        else:
            merged.append(sentence)
    return merged


def _simple_sentence_split(text: str) -> list[str]:
    """Simple regex-based sentence splitting."""
    # Split on sentence-ending punctuation followed by space or newline
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _parse_segments(  # noqa: C901
    text: str,
    capabilities: "TTSCapabilities | None" = None,
    heading_levels: dict | None = None,
    extensions: dict | None = None,
) -> list[Segment]:
    """Parse text into segments with SSMD features."""
    # Check for heading
    heading_match = HEADING_PATTERN.match(text)
    if heading_match:
        return _parse_heading(heading_match, heading_levels or DEFAULT_HEADING_LEVELS)

    segments: list[Segment] = []
    position = 0

    # Use the centralized token pattern so all parser paths recognize the same markup.
    combined = INLINE_MARKUP_TOKEN_PATTERN

    pending_breaks: list[BreakAttrs] = []
    pending_marks: list[str] = []

    for match in combined.finditer(text):
        if match.start() > position:
            plain = _normalize_text(text[position : match.start()])
            if plain:
                seg = Segment(text=plain)
                if pending_breaks:
                    seg.breaks_before = pending_breaks
                    pending_breaks = []
                if pending_marks:
                    seg.marks_before = pending_marks
                    pending_marks = []
                segments.append(seg)

        markup = match.group(0)
        pending_breaks, pending_marks, markup_seg = _handle_markup(
            markup,
            segments,
            pending_breaks,
            pending_marks,
            extensions,
        )
        if markup_seg:
            segments.append(markup_seg)

        position = match.end()

    # Add remaining text
    if position < len(text):
        plain = _normalize_text(text[position:])
        if plain:
            seg = Segment(text=plain)
            _apply_pending(seg, pending_breaks, pending_marks)
            segments.append(seg)

    # If no segments created but we have text, create a plain segment
    if not segments and text.strip():
        seg = Segment(text=text.strip())
        _apply_pending(seg, pending_breaks, pending_marks)
        segments.append(seg)

    return segments


def _handle_markup(
    markup: str,
    segments: list[Segment],
    pending_breaks: list[BreakAttrs],
    pending_marks: list[str],
    extensions: dict | None,
) -> tuple[list[BreakAttrs], list[str], Segment | None]:
    """Handle a single markup token and return any segment."""
    if markup.startswith("..."):
        brk = _parse_break(markup[3:])
        if segments:
            segments[-1].breaks_after.append(brk)
        else:
            pending_breaks.append(brk)
        return pending_breaks, pending_marks, None

    if markup.startswith("@"):
        mark_name = markup[1:]
        if segments:
            segments[-1].marks_after.append(mark_name)
        else:
            pending_marks.append(mark_name)
        return pending_breaks, pending_marks, None

    seg = _segment_from_markup(markup, extensions)
    if seg:
        _apply_pending(seg, pending_breaks, pending_marks)
        return [], [], seg

    return pending_breaks, pending_marks, None


def _segment_from_markup(markup: str, extensions: dict | None) -> Segment | None:
    """Build a segment from emphasis, annotation, or prosody markup."""
    for pattern, field_name, value in SYMBOLIC_PROSODY_RULES:
        match = pattern.fullmatch(markup)
        if match:
            if field_name == "volume":
                prosody = ProsodyAttrs(volume=value)
            elif field_name == "rate":
                prosody = ProsodyAttrs(rate=value)
            else:
                prosody = ProsodyAttrs(pitch=value)
            return Segment(text=match.group(1), prosody=prosody)
    if markup.startswith("**"):
        inner = STRONG_EMPHASIS_PATTERN.match(markup)
        if inner:
            return Segment(text=inner.group(1), emphasis="strong")
        return None

    if markup.startswith("*"):
        inner = MODERATE_EMPHASIS_PATTERN.match(markup)
        if inner:
            return Segment(text=inner.group(1), emphasis=True)
        return None

    if markup.startswith("~~"):
        inner = TILDE_REDUCED_EMPHASIS_PATTERN.match(markup)
        if inner:
            return Segment(text=inner.group(1), emphasis="reduced", emphasis_delimiter="~~")
        return None

    if markup.startswith("_") and not markup.startswith("__"):
        inner = REDUCED_EMPHASIS_PATTERN.match(markup)
        if inner:
            return Segment(text=inner.group(1), emphasis="reduced", emphasis_delimiter="_")
        return None

    if markup.startswith("["):
        return _parse_annotation(markup, extensions)

    return None


def _apply_pending(
    seg: Segment,
    pending_breaks: list[BreakAttrs],
    pending_marks: list[str],
) -> None:
    """Apply pending breaks and marks to a segment."""
    if pending_breaks:
        seg.breaks_before = pending_breaks.copy()
    if pending_marks:
        seg.marks_before = pending_marks.copy()


def _parse_heading(
    match: re.Match,
    heading_levels: dict,
) -> list[Segment]:
    """Parse heading into segments."""
    level = len(match.group(1))
    text = match.group(2).strip()

    if level not in heading_levels:
        return [Segment(text=text)]

    # Build segment with heading effects
    seg = Segment(text=text)

    for effect_type, value in heading_levels[level]:
        if effect_type == "emphasis":
            seg.emphasis = value
        elif effect_type == "pause":
            seg.breaks_after.append(BreakAttrs(time=value))
        elif effect_type == "pause_before":
            seg.breaks_before.append(BreakAttrs(time=value))
        elif effect_type == "prosody" and isinstance(value, dict):
            seg.prosody = ProsodyAttrs(
                volume=value.get("volume"),
                rate=value.get("rate"),
                pitch=value.get("pitch"),
                legacy_rate=value.get("rate") is not None,
                legacy_pitch=value.get("pitch") is not None,
            )

    return [seg]


def _parse_block_to_spans(
    clean_text: str,
    block_text: str,
    annotations: list[AnnotationSpan],
    warnings: list[str],
    preserve_whitespace: bool,
) -> str:
    if preserve_whitespace:
        segments, seg_warnings = _parse_segments_for_spans(
            block_text,
            normalize_text=False,
        )
        warnings.extend(seg_warnings)
        for segment, attrs_override, join_previous in segments:
            clean_text = _append_segment_spans(
                clean_text,
                segment,
                annotations,
                "inline",
                attrs_override=attrs_override,
                join_previous=join_previous,
            )
        return clean_text

    paragraphs = PARAGRAPH_PATTERN.split(block_text)
    for para_index, paragraph in enumerate(paragraphs):
        if not paragraph.strip():
            continue

        if clean_text and (para_index > 0 or clean_text.endswith("\n")):
            clean_text += "\n\n"

        clean_text = _parse_paragraph_normalized(
            clean_text,
            paragraph,
            annotations,
            warnings,
        )

    return clean_text


def _parse_paragraph_normalized(
    clean_text: str,
    paragraph: str,
    annotations: list[AnnotationSpan],
    warnings: list[str],
) -> str:
    segments, seg_warnings = _parse_segments_for_spans(paragraph)
    warnings.extend(seg_warnings)
    for segment, attrs_override, join_previous in segments:
        clean_text = _append_segment_spans_normalized(
            clean_text,
            segment,
            annotations,
            "inline",
            attrs_override=attrs_override,
            join_previous=join_previous,
        )

    return clean_text


def _emit_segment_events(
    events: list[StructuralEvent],
    position: int,
    segment: Segment,
    *,
    before: bool,
    include_breaks: bool = True,
    include_marks: bool = True,
) -> None:
    """Append zero-width events carried by a segment at a text boundary."""
    if before:
        breaks = segment.breaks_before if include_breaks else []
        marks = segment.marks_before if include_marks else []
    else:
        breaks = segment.breaks_after if include_breaks else []
        marks = segment.marks_after if include_marks else []

    for item in breaks:
        attrs: dict[str, str] = {}
        if item.time is not None:
            attrs["time"] = item.time
        if item.strength is not None:
            attrs["strength"] = item.strength
        events.append(
            StructuralEvent(
                pos=position,
                kind="break",
                anchor="before" if before else "after",
                attrs=attrs,
            )
        )
    for name in marks:
        events.append(
            StructuralEvent(
                pos=position,
                kind="mark",
                anchor="before" if before else "after",
                attrs={"name": name},
            )
        )


def _append_segment_spans(
    clean_text: str,
    segment: Segment,
    annotations: list[AnnotationSpan],
    kind: str,
    attrs_override: dict[str, str] | None = None,
    events: list[StructuralEvent] | None = None,
    join_previous: bool = False,
) -> str:
    """Append a segment and optionally its structural events."""
    start = len(clean_text)
    if events is not None:
        _emit_segment_events(events, start, segment, before=True)

    text = segment.to_text()
    if not text:
        return clean_text

    clean_text += text
    end = len(clean_text)

    attrs = attrs_override if attrs_override is not None else _segment_attrs_to_map(segment)
    if attrs:
        annotations.append(
            AnnotationSpan(
                char_start=start,
                char_end=end,
                attrs=attrs,
                kind=kind,
            )
        )

    if events is not None:
        _emit_segment_events(events, end, segment, before=False)
    return clean_text


def _append_segment_spans_normalized(
    clean_text: str,
    segment: Segment,
    annotations: list[AnnotationSpan],
    kind: str,
    attrs_override: dict[str, str] | None = None,
    events: list[StructuralEvent] | None = None,
    join_previous: bool = False,
) -> str:
    """Append a normalized segment and optionally its structural events."""
    text = segment.to_text()
    if not text:
        if events is not None:
            _emit_segment_events(events, len(clean_text), segment, before=True)
            _emit_segment_events(events, len(clean_text), segment, before=False)
        return clean_text

    prefix = ""
    if clean_text and not clean_text.endswith("\n") and not join_previous:
        if text and not text.startswith(tuple(".!?,:;")):
            prefix = " "

    char_start = len(clean_text) + len(prefix)
    if events is not None:
        _emit_segment_events(events, char_start, segment, before=True)
    clean_text = f"{clean_text}{prefix}{text}"
    char_end = len(clean_text)

    attrs = attrs_override if attrs_override is not None else _segment_attrs_to_map(segment)
    if attrs:
        annotations.append(
            AnnotationSpan(
                char_start=char_start,
                char_end=char_end,
                attrs=attrs,
                kind=kind,
            )
        )

    if events is not None:
        _emit_segment_events(events, char_end, segment, before=False)
    return clean_text


def _annotated_attrs_to_tagged(attrs: dict[str, str]) -> dict[str, str]:
    tag: str | None = None
    if "ext" in attrs:
        tag = "extension"
    elif "src" in attrs:
        tag = "audio"
    elif "sub" in attrs:
        tag = "sub"
    elif "ph" in attrs or "ipa" in attrs or "sampa" in attrs:
        tag = "phoneme"
    elif "as" in attrs:
        tag = "say-as"
    elif any(
        key in attrs
        for key in (
            "voice",
            "voice-lang",
            "voice_lang",
            "voice-name",
            "voice-languages",
            "gender",
            "age",
            "variant",
        )
    ):
        tag = "voice"
    elif "lang" in attrs or "language" in attrs:
        tag = "lang"
    elif any(k in attrs for k in ("volume", "rate", "pitch", "v", "r", "p", "vrp")):
        tag = "prosody"
    elif "emphasis" in attrs:
        tag = "emphasis"

    if tag:
        return {**attrs, "tag": tag}

    return attrs


def _segment_attrs_to_map(segment: Segment) -> dict[str, str]:  # noqa: C901
    attrs: dict[str, str] = {}

    if segment.language:
        attrs["lang"] = segment.language
        if segment.language_scope != "semantic":
            attrs["scope"] = segment.language_scope

    if segment.voice:
        if segment.voice.name:
            attrs["voice"] = segment.voice.name
        if segment.voice.selector_name:
            attrs["voice-name"] = segment.voice.selector_name
        if segment.voice.language:
            attrs["voice-languages"] = segment.voice.language
        if segment.voice.gender:
            attrs["gender"] = segment.voice.gender
        if segment.voice.age is not None:
            attrs["age"] = str(segment.voice.age)
        if segment.voice.variant is not None:
            attrs["variant"] = str(segment.voice.variant)

    if segment.say_as:
        attrs["as"] = segment.say_as.interpret_as
        if segment.say_as.format:
            attrs["format"] = segment.say_as.format
        if segment.say_as.detail:
            attrs["detail"] = str(segment.say_as.detail)

    if segment.substitution:
        attrs["sub"] = segment.substitution

    if segment.phoneme:
        attrs["ph"] = segment.phoneme.ph
        attrs["alphabet"] = segment.phoneme.alphabet

    if segment.extension:
        attrs["ext"] = segment.extension

    if segment.prosody:
        if segment.prosody.volume:
            attrs["volume"] = segment.prosody.volume
        if segment.prosody.rate:
            attrs["rate"] = segment.prosody.rate
        if segment.prosody.pitch:
            attrs["pitch"] = segment.prosody.pitch

    if segment.emphasis:
        if segment.emphasis is True or segment.emphasis == "moderate":
            attrs["emphasis"] = "moderate"
        else:
            attrs["emphasis"] = str(segment.emphasis)

    if segment.audio:
        attrs["src"] = segment.audio.src
        if segment.audio.clip_begin or segment.audio.clip_end:
            attrs["clip"] = f"{segment.audio.clip_begin or ''}-{segment.audio.clip_end or ''}"
        if segment.audio.speed:
            attrs["speed"] = segment.audio.speed
        if segment.audio.repeat_count is not None:
            attrs["repeat"] = str(segment.audio.repeat_count)
        if segment.audio.repeat_dur:
            attrs["repeatdur"] = segment.audio.repeat_dur
        if segment.audio.sound_level:
            attrs["level"] = segment.audio.sound_level
        if segment.audio.description:
            attrs["desc"] = segment.audio.description
        if segment.audio.alt_text:
            attrs["alt"] = segment.audio.alt_text

    return _annotated_attrs_to_tagged(attrs)


def _parse_segments_with_warnings(
    text: str,
    *,
    normalize_text: bool = True,
) -> tuple[list[Segment], list[str]]:
    segments, warnings = _parse_segments_for_spans(text, normalize_text=normalize_text)
    return [segment for segment, _, _ in segments], warnings


def _source_pieces_are_contiguous(
    source: str,
    previous_end: int | None,
    current_start: int,
) -> bool:
    """Return whether two emitted pieces touch without source whitespace."""
    if previous_end is None or previous_end != current_start or current_start == 0:
        return False
    return not source[previous_end - 1].isspace() and not source[current_start].isspace()


def _parse_segments_for_spans(
    text: str,
    *,
    normalize_text: bool = True,
    pending_breaks_out: list[BreakAttrs] | None = None,
    pending_marks_out: list[str] | None = None,
) -> tuple[list[tuple[Segment, dict[str, str] | None, bool]], list[str]]:
    """Parse inline pieces while retaining whether source boundaries are contiguous."""
    segments: list[tuple[Segment, dict[str, str] | None, bool]] = []
    warnings: list[str] = []
    position = 0
    previous_source_end: int | None = None
    can_join_previous = False
    pending_breaks: list[BreakAttrs] = []
    pending_marks: list[str] = []

    def add_piece(
        segment: Segment,
        attrs: dict[str, str] | None,
        source_start: int,
        source_end: int,
        *,
        allow_join: bool = True,
    ) -> None:
        nonlocal previous_source_end, can_join_previous
        join_previous = (
            allow_join
            and can_join_previous
            and _source_pieces_are_contiguous(text, previous_source_end, source_start)
        )
        segments.append((segment, attrs, join_previous))
        previous_source_end = source_end
        can_join_previous = True

    heading_match = HEADING_PATTERN.match(text)
    if heading_match:
        parsed = _parse_heading(heading_match, DEFAULT_HEADING_LEVELS)
        segments.extend((segment, _segment_attrs_to_map(segment), False) for segment in parsed)
        return segments, warnings

    for match in INLINE_MARKUP_TOKEN_PATTERN.finditer(text):
        if match.start() > position:
            plain_text = text[position : match.start()]
            plain = _normalize_text(plain_text) if normalize_text else plain_text
            if plain:
                seg = Segment(text=plain)
                has_pending = bool(pending_breaks or pending_marks)
                if pending_breaks:
                    seg.breaks_before = pending_breaks
                    pending_breaks = []
                if pending_marks:
                    seg.marks_before = pending_marks
                    pending_marks = []
                add_piece(
                    seg,
                    _segment_attrs_to_map(seg),
                    position,
                    match.start(),
                    allow_join=not has_pending,
                )

        markup = match.group(0)
        attrs_override: dict[str, str] | None = None
        if markup.startswith("["):
            annotation_match = ANNOTATION_PATTERN.match(markup)
            if annotation_match:
                attrs_override, attr_warnings = _parse_annotation_params_with_warnings(
                    annotation_match.group(2).strip()
                )
                warnings.extend(attr_warnings)
                attrs_override = {k: v for k, v in attrs_override.items() if v != ""}
                attrs_override = _annotated_attrs_to_tagged(attrs_override)

        current_segments = [segment for segment, _, _ in segments]
        pending_breaks, pending_marks, markup_seg = _handle_markup(
            markup,
            current_segments,
            pending_breaks,
            pending_marks,
            extensions=None,
        )
        if markup_seg:
            if attrs_override is None or not attrs_override:
                attrs_override = _segment_attrs_to_map(markup_seg)
            add_piece(
                markup_seg,
                attrs_override,
                match.start(),
                match.end(),
                allow_join=not (pending_breaks or pending_marks),
            )
        else:
            previous_source_end = match.end()
            can_join_previous = False

        position = match.end()

    if position < len(text):
        plain_text = text[position:]
        plain = _normalize_text(plain_text) if normalize_text else plain_text
        if plain:
            seg = Segment(text=plain)
            has_pending = bool(pending_breaks or pending_marks)
            _apply_pending(seg, pending_breaks, pending_marks)
            add_piece(
                seg, _segment_attrs_to_map(seg), position, len(text), allow_join=not has_pending
            )
            pending_breaks = []
            pending_marks = []
    if not segments and text.strip() and not pending_breaks and not pending_marks:
        content = _normalize_text(text) if normalize_text else text
        if content:
            seg = Segment(text=content)
            _apply_pending(seg, pending_breaks, pending_marks)
            add_piece(seg, _segment_attrs_to_map(seg), 0, len(text), allow_join=False)
            pending_breaks = []
            pending_marks = []

    if text.count("[") != text.count("]"):
        warnings.append("Unbalanced annotation brackets in input.")
    if text.count("{") != text.count("}"):
        warnings.append("Unbalanced annotation braces in input.")

    if pending_breaks_out is not None:
        pending_breaks_out.extend(pending_breaks)
    if pending_marks_out is not None:
        pending_marks_out.extend(pending_marks)

    return segments, warnings


def _directive_attrs_to_map(directive: DirectiveAttrs) -> dict[str, str]:
    attrs: dict[str, str] = {}

    if directive.language:
        attrs["lang"] = directive.language

    if directive.voice:
        if directive.voice.name:
            attrs["voice"] = directive.voice.name
        if directive.voice.selector_name:
            attrs["voice-name"] = directive.voice.selector_name
        if directive.voice.language:
            attrs["voice-languages"] = directive.voice.language
        if directive.voice.gender:
            attrs["gender"] = directive.voice.gender
        if directive.voice.age is not None:
            attrs["age"] = str(directive.voice.age)
        if directive.voice.variant is not None:
            attrs["variant"] = str(directive.voice.variant)

    if directive.prosody:
        if directive.prosody.volume:
            attrs["volume"] = directive.prosody.volume
        if directive.prosody.rate:
            attrs["rate"] = directive.prosody.rate
        if directive.prosody.pitch:
            attrs["pitch"] = directive.prosody.pitch

    return attrs


def _parse_break(modifier: str) -> BreakAttrs:
    """Parse break modifier into BreakAttrs."""
    if modifier in SSMD_BREAK_MARKER_TO_STRENGTH:
        return BreakAttrs(strength=SSMD_BREAK_MARKER_TO_STRENGTH[modifier])
    elif modifier.endswith("s") or modifier.endswith("ms"):
        return BreakAttrs(time=modifier)
    else:
        return BreakAttrs(time=f"{modifier}ms")


def _parse_annotation(markup: str, extensions: dict | None = None) -> Segment | None:
    """Parse [text]{key="value"} markup."""
    match = ANNOTATION_PATTERN.match(markup)
    if not match:
        return None

    text = match.group(1)
    params = match.group(2).strip()

    seg = Segment(text=text)
    params_map = _parse_annotation_params(params)
    if not params_map and params:
        return seg

    if not params_map:
        return seg

    if "src" in params_map:
        seg.audio = _parse_audio_annotation_params(params_map)
        return seg

    if "lang" in params_map:
        seg.language = params_map["lang"]
    elif "language" in params_map:
        seg.language = params_map["language"]

    scope = params_map.get("scope")
    if seg.language and scope in ("semantic", "pronunciation"):
        seg.language_scope = "semantic" if scope == "semantic" else "pronunciation"
    voice = _parse_voice_annotation_params(params_map)
    if voice:
        seg.voice = voice

    say_as = _parse_say_as_params(params_map)
    if say_as:
        seg.say_as = say_as

    phoneme = _parse_phoneme_params(params_map)
    if phoneme:
        seg.phoneme = phoneme

    if "sub" in params_map:
        seg.substitution = params_map["sub"]

    if "emphasis" in params_map:
        level = params_map["emphasis"].lower()
        if level in ("none", "reduced", "moderate", "strong"):
            seg.emphasis = level if level != "moderate" else True

    if "ext" in params_map:
        seg.extension = params_map["ext"]

    prosody = _parse_prosody_params(params_map)
    if prosody:
        seg.prosody = prosody

    return seg


def _parse_annotation_params(params: str) -> dict[str, str]:
    """Parse key="value" pairs from annotation params."""
    values, _ = _parse_annotation_params_with_warnings(params)
    return values


def _parse_annotation_params_with_warnings(  # noqa: C901
    params: str,
) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    warnings: list[str] = []

    if not params:
        return values, warnings

    key = ""
    value = ""
    state = "key"
    quote: str | None = None
    escape = False

    def _commit() -> None:
        nonlocal key, value
        if key:
            values[key.lower()] = value
        key = ""
        value = ""

    for ch in params:
        if state == "key":
            if ch.isspace():
                continue
            if ch == "=":
                if key:
                    state = "value"
                continue
            if ch.isalnum() or ch in "_-:":
                key += ch
                continue
            warnings.append(f"Unexpected character '{ch}' in attribute key.")
            continue

        if state == "value":
            if quote:
                # Handle escaping within quoted strings
                if escape:
                    value += ch
                    escape = False
                    continue

                if ch == "\\":
                    escape = True
                    continue

                if ch == quote:
                    _commit()
                    state = "key"
                    quote = None
                else:
                    value += ch
                continue

            if ch in ('"', "'"):
                quote = ch
                continue

            if ch.isspace() and value != "":
                _commit()
                state = "key"
                continue
            elif ch.isspace() and value == "":
                continue

            value += ch

    if quote is not None:
        warnings.append("Unterminated quote in annotation attributes.")
        if key:
            values[key.lower()] = value
        return values, warnings

    if key:
        if state == "value" and quote is None:
            _commit()
        elif state == "key":
            values[key.lower()] = ""

    if "scope" in values and not ("lang" in values or "language" in values):
        warnings.append("Language scope without language annotation.")
    elif "scope" in values and values["scope"] not in ("semantic", "pronunciation"):
        warnings.append(
            f"Invalid language scope '{values['scope']}'; expected semantic or pronunciation."
        )
    if "vrp" in values and _parse_vrp(values["vrp"]) is None:
        warnings.append(
            f"Invalid vrp value '{values['vrp']}'; expected exactly three digits matching "
            "[0-5][1-5][1-5]."
        )

    return values, warnings


def _parse_audio_annotation_params(params_map: dict[str, str]) -> AudioAttrs:
    """Parse audio parameters from annotation map."""
    audio = AudioAttrs(src=params_map["src"])

    clip = params_map.get("clip")
    if clip and "-" in clip:
        clip_begin, clip_end = clip.split("-", 1)
        audio.clip_begin = clip_begin.strip()
        audio.clip_end = clip_end.strip()

    if params_map.get("speed"):
        audio.speed = params_map["speed"]

    repeat = params_map.get("repeat")
    if repeat:
        try:
            number = float(repeat)
        except ValueError:
            number = 0
        if math.isfinite(number) and number > 0:
            audio.repeat_count = int(number) if number.is_integer() else number

    if params_map.get("repeatdur"):
        audio.repeat_dur = params_map["repeatdur"]

    if params_map.get("level"):
        audio.sound_level = params_map["level"]

    if params_map.get("desc"):
        audio.description = params_map["desc"]

    if params_map.get("alt"):
        audio.alt_text = params_map["alt"]
    return audio


def _parse_voice_annotation_params(params_map: dict[str, str]) -> VoiceAttrs | None:
    """Parse canonical voice selectors and 0.8 aliases."""
    keys = (
        "voice",
        "voice-name",
        "voice-languages",
        "voice-lang",
        "voice_lang",
        "gender",
        "age",
        "variant",
    )
    if not any(key in params_map for key in keys):
        return None

    voice = VoiceAttrs(
        name=params_map.get("voice") or params_map.get("voice-name"),
        language=(
            params_map.get("voice-languages")
            or params_map.get("voice-lang")
            or params_map.get("voice_lang")
        ),
        selector_name=params_map.get("voice-name"),
    )
    if "gender" in params_map:
        voice.gender = params_map["gender"].lower()  # type: ignore[assignment]
    for key in ("age", "variant"):
        if key in params_map:
            try:
                setattr(voice, key, int(params_map[key]))
            except ValueError:
                pass
    return voice


def _parse_say_as_params(params_map: dict[str, str]) -> SayAsAttrs | None:
    """Parse say-as params from annotation map."""
    interpret_as = params_map.get("as") or params_map.get("say-as")
    if not interpret_as:
        return None

    return SayAsAttrs(
        interpret_as=interpret_as,
        format=params_map.get("format"),
        detail=params_map.get("detail"),
    )


def _parse_phoneme_params(params_map: dict[str, str]) -> PhonemeAttrs | None:
    """Parse phoneme params from annotation map."""
    if "ipa" in params_map:
        return PhonemeAttrs(ph=params_map["ipa"], alphabet="ipa")

    if "sampa" in params_map:
        return PhonemeAttrs(ph=params_map["sampa"], alphabet="x-sampa")

    if "ph" in params_map:
        alphabet = params_map.get("alphabet", "ipa").lower()
        if alphabet == "sampa":
            alphabet = "x-sampa"
        return PhonemeAttrs(ph=params_map["ph"], alphabet=alphabet)

    return None


def _parse_vrp(value: str) -> tuple[str, str, str] | None:
    """Parse compact volume/rate/pitch digits in V/R/P order."""
    compact = value.strip()
    if not re.fullmatch(r"[0-5][1-5][1-5]", compact):
        return None
    return compact[0], compact[1], compact[2]


def _parse_prosody_params(params_map: dict[str, str]) -> ProsodyAttrs | None:
    """Parse named, aliased, and compact prosody params from an annotation map."""
    packed_volume = packed_rate = packed_pitch = None
    if "vrp" in params_map:
        packed = _parse_vrp(params_map["vrp"])
        if packed is not None:
            packed_volume, packed_rate, packed_pitch = packed

    volume = params_map.get("volume") or params_map.get("v") or packed_volume
    rate = params_map.get("rate") or params_map.get("r") or packed_rate
    pitch = params_map.get("pitch") or params_map.get("p") or packed_pitch

    if not any([volume, rate, pitch]):
        return None

    prosody = ProsodyAttrs()
    if volume:
        prosody.volume = _normalize_prosody_value(volume, PROSODY_VOLUME_MAP)
    if rate:
        prosody.rate = _normalize_prosody_value(rate, PROSODY_RATE_MAP)
    if pitch:
        prosody.pitch = _normalize_prosody_value(pitch, PROSODY_PITCH_MAP)
    prosody.legacy_rate = packed_rate is not None and not (
        params_map.get("rate") or params_map.get("r")
    )
    prosody.legacy_pitch = packed_pitch is not None and not (
        params_map.get("pitch") or params_map.get("p")
    )
    return prosody


def _normalize_prosody_value(value: str, mapping: dict[str, str]) -> str:
    """Normalize numeric, legacy, and natural prosody values."""
    stripped = value.strip()
    if stripped.isdigit() and stripped in mapping:
        return mapping[stripped]

    if mapping is PROSODY_RATE_MAP:
        return normalize_rate_value(stripped)
    if mapping is PROSODY_PITCH_MAP:
        return normalize_pitch_value(stripped)

    lowered = stripped.lower()
    if lowered in mapping.values():
        return lowered
    return stripped


def _is_language_code(value: str) -> bool:
    return bool(re.match(r"^[a-z]{2}(-[A-Z]{2})?$", value))


def _parse_voice_annotation(params: str) -> VoiceAttrs:
    """Parse voice annotation parameters."""
    voice = VoiceAttrs()

    # Check for complex params (with gender/variant)
    if "," in params:
        parts = [p.strip() for p in params.split(",")]
        first = parts[0]

        # First part is name or language
        if re.match(r"^[a-z]{2}(-[A-Z]{2})?$", first):
            voice.language = first
        else:
            voice.name = first

        # Parse remaining parts
        for part in parts[1:]:
            if part.startswith("gender:"):
                voice.gender = part[7:].strip().lower()  # type: ignore[assignment]
            elif part.startswith("variant:"):
                voice.variant = int(part[8:].strip())
    else:
        # Simple name or language
        if re.match(r"^[a-z]{2}(-[A-Z]{2})?$", params):
            voice.language = params
        else:
            voice.name = params

    return voice


# ═══════════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════════════════

# Re-export old names for compatibility
SSMDSegment = Segment
SSMDSentence = Sentence
SSMDParagraph = Paragraph


def parse_sentences(
    ssmd_text: str,
    *,
    capabilities: "TTSCapabilities | str | None" = None,
    include_default_voice: bool = True,
    sentence_detection: bool = True,
    language: str | None = None,
    model_size: SpacyModelSize | None = None,
    spacy_model: str | None = None,
    use_spacy: bool | None = None,
    heading_levels: dict | None = None,
    extensions: dict | None = None,
    parse_yaml_header: bool = True,
    strict_parse: bool = False,
) -> ParsedResult[Sentence]:
    """Parse SSMD text into sentences (backward compatible API).

    This is an alias for parse_paragraphs() with the old parameter names.
    Returned sentences include paragraph_index and sentence_index metadata.

    Args:
        ssmd_text: SSMD formatted text to parse
        capabilities: TTS capabilities or preset name
        include_default_voice: If False, exclude sentences without voice context
        sentence_detection: Enable/disable sentence splitting
        language: Language code for sentence detection
        model_size: Size of spacy model (sm/md/lg)
        spacy_model: Full spacy model name (deprecated, use model_size)
        use_spacy: Force use of spacy for sentence detection
        heading_levels: Custom heading configurations
        extensions: Custom extension handlers
        parse_yaml_header: If True, parse YAML front matter and apply
            heading/extensions config while stripping it from the body. If False,
            YAML front matter is preserved as plain text.
        strict_parse: If True, strip unsupported features based on capabilities.

    Returns:
        List of Sentence objects
    """
    paragraphs = parse_paragraphs(
        ssmd_text,
        capabilities=capabilities,
        sentence_detection=sentence_detection,
        language=language,
        model_size=model_size,
        spacy_model=spacy_model,
        use_spacy=use_spacy,
        heading_levels=heading_levels,
        extensions=extensions,
        parse_yaml_header=parse_yaml_header,
        strict_parse=strict_parse,
    )

    sentences = [sentence for paragraph in paragraphs for sentence in paragraph.sentences]

    # Filter out sentences without voice if requested
    if not include_default_voice:
        sentences = [s for s in sentences if s.voice is not None]

    return ParsedResult(sentences, diagnostics=paragraphs.diagnostics)


def parse_segments(
    ssmd_text: str,
    *,
    capabilities: "TTSCapabilities | str | None" = None,
    voice_context: VoiceAttrs | None = None,
) -> list[Segment]:
    """Parse SSMD text into segments (backward compatible API)."""
    if voice_context is not None:
        _ = voice_context
    caps = _resolve_capabilities(capabilities)
    return _parse_segments(ssmd_text, capabilities=caps)


def parse_voice_blocks(ssmd_text: str) -> list[tuple[DirectiveAttrs, str]]:
    """Parse SSMD text into directive blocks (backward compatible API).

    Returns list of (DirectiveAttrs, text) tuples.
    """
    return _split_directive_blocks(ssmd_text)


def _emit_pending_structure_events(
    events: list[StructuralEvent],
    position: int,
    breaks: list[BreakAttrs],
    marks: list[str],
) -> None:
    """Flush structural events that have no following text segment."""
    for item in breaks:
        attrs: dict[str, str] = {}
        if item.time is not None:
            attrs["time"] = item.time
        if item.strength is not None:
            attrs["strength"] = item.strength
        events.append(StructuralEvent(pos=position, kind="break", anchor="after", attrs=attrs))
    for name in marks:
        events.append(
            StructuralEvent(
                pos=position,
                kind="mark",
                anchor="after",
                attrs={"name": name},
            )
        )


def _parse_structure_paragraph(
    clean_text: str,
    paragraph: str,
    annotations: list[AnnotationSpan],
    events: list[StructuralEvent],
    warnings: list[str],
    *,
    normalize: bool,
) -> str:
    """Parse one paragraph using the same segment traversal as parse_spans."""
    pending_breaks: list[BreakAttrs] = []
    pending_marks: list[str] = []
    segments, paragraph_warnings = _parse_segments_for_spans(
        paragraph,
        normalize_text=normalize,
        pending_breaks_out=pending_breaks,
        pending_marks_out=pending_marks,
    )
    warnings.extend(paragraph_warnings)
    append = _append_segment_spans_normalized if normalize else _append_segment_spans
    for segment, attrs_override, join_previous in segments:
        clean_text = append(
            clean_text,
            segment,
            annotations,
            "inline",
            attrs_override=attrs_override,
            events=events,
            join_previous=join_previous,
        )
    if pending_breaks or pending_marks:
        _emit_pending_structure_events(events, len(clean_text), pending_breaks, pending_marks)
    return clean_text


def _parse_structure_block(
    clean_text: str,
    block_text: str,
    annotations: list[AnnotationSpan],
    events: list[StructuralEvent],
    warnings: list[str],
    *,
    normalize: bool,
) -> str:
    """Parse a directive block and retain paragraph boundary positions."""
    if normalize:
        paragraphs = PARAGRAPH_PATTERN.split(block_text)
        for para_index, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
            if clean_text and (para_index > 0 or clean_text.endswith("\n")):
                clean_text += "\n\n"
            clean_text = _parse_structure_paragraph(
                clean_text, paragraph, annotations, events, warnings, normalize=True
            )
            has_following = any(part.strip() for part in paragraphs[para_index + 1 :])
            if has_following:
                events.append(
                    StructuralEvent(
                        pos=len(clean_text),
                        kind="paragraph",
                        anchor="after",
                        attrs={},
                    )
                )
        return clean_text

    parts = re.split(r"(\n\n+)", block_text)
    for part_index in range(0, len(parts), 2):
        paragraph = parts[part_index]
        if paragraph:
            clean_text = _parse_structure_paragraph(
                clean_text, paragraph, annotations, events, warnings, normalize=False
            )
        if part_index + 1 < len(parts):
            separator = parts[part_index + 1]
            if separator and part_index + 2 < len(parts):
                events.append(
                    StructuralEvent(
                        pos=len(clean_text),
                        kind="paragraph",
                        anchor="after",
                        attrs={},
                    )
                )
                clean_text += separator
    return clean_text


def resolve_structure_defaults(
    result: ParseStructureResult,
    voice_defaults: Mapping[str, VoiceProsodyDefaults] | VoiceDefaults | None = None,
) -> ParseStructureResult:
    """Return structural annotations with inherited voice defaults resolved.

    ``annotations`` remains the declared source view. The resolved view is
    placed in ``effective_annotations`` for renderers that need semantics.
    """
    if voice_defaults is None:
        from ssmd.frontmatter import voice_defaults as header_voice_defaults

        voice_defaults = header_voice_defaults(result.header)
    result.effective_annotations = []
    for annotation in result.annotations:
        attrs = dict(annotation.attrs)
        voice_name = attrs.get("voice")
        defaults = voice_defaults.get(voice_name) if voice_name else None
        if defaults is not None:
            for field_name in ("volume", "rate", "pitch"):
                if field_name not in attrs and getattr(defaults, field_name):
                    attrs[field_name] = getattr(defaults, field_name)
        result.effective_annotations.append(
            AnnotationSpan(
                char_start=annotation.char_start,
                char_end=annotation.char_end,
                attrs=attrs,
                kind=annotation.kind,
                node_id=annotation.node_id,
                source_start=annotation.source_start,
                source_end=annotation.source_end,
            )
        )
    return result


class _CleanTextBuilder:
    def __init__(self, normalize: bool) -> None:
        self.normalize = normalize
        self.parts: list[str] = []
        self.length = 0
        self.pending_space = False
        self.tail = ""

    def append(self, value: str) -> None:
        if not self.normalize:
            self._append_raw(value)
            return
        for char in value:
            if char.isspace():
                self.pending_space = True
                continue
            if (
                self.pending_space
                and self.length
                and char not in "!?,:;."
                and not self.tail.endswith("\n")
            ):
                self._append_raw(" ")
            self.pending_space = False
            self._append_raw(char)

    def separate(self, gap: str) -> None:
        self.pending_space = False
        if not self.length:
            return
        if not self.normalize:
            self._append_raw(gap or "\n\n")
        elif not self.tail.endswith("\n\n"):
            self._append_raw("\n\n")

    def _append_raw(self, value: str) -> None:
        if not value:
            return
        self.parts.append(value)
        self.length += len(value)
        self.tail = (self.tail + value)[-2:]

    def build(self) -> str:
        return "".join(self.parts)


def _tagged_annotation_attrs(attrs: Mapping[str, str], tag: str) -> dict[str, str]:
    tagged = _annotated_attrs_to_tagged(dict(attrs))
    if "tag" not in tagged:
        tagged["tag"] = tag
    return tagged


def _emit_inline_nodes(
    nodes: tuple[Node, ...],
    builder: _CleanTextBuilder,
    annotations: list[AnnotationSpan],
    events: list[StructuralEvent],
) -> None:
    for node in nodes:
        if isinstance(node, TextNode):
            builder.append(node.value)
        elif isinstance(node, BreakNode):
            events.append(
                StructuralEvent(
                    builder.length,
                    "break",
                    "after",
                    node.attrs,
                    node.source_start,
                    node.source_end,
                )
            )
        elif isinstance(node, MarkNode):
            events.append(
                StructuralEvent(
                    builder.length,
                    "mark",
                    "after",
                    {"name": node.name},
                    node.source_start,
                    node.source_end,
                )
            )
        elif isinstance(node, (AnnotationNode, EmphasisNode)):
            start = builder.length
            _emit_inline_nodes(node.children, builder, annotations, events)
            end = builder.length
            if end > start:
                if isinstance(node, AnnotationNode):
                    attrs = _tagged_annotation_attrs(node.attrs, "annotation")
                    kind = attrs["tag"]
                else:
                    attrs = {"emphasis": node.level, "tag": "emphasis"}
                    kind = "emphasis"
                annotations.append(
                    AnnotationSpan(
                        start,
                        end,
                        attrs,
                        kind=kind,
                        source_start=node.source_start,
                        source_end=node.source_end,
                    )
                )


def _emit_block(
    node: Node,
    builder: _CleanTextBuilder,
    annotations: list[AnnotationSpan],
    events: list[StructuralEvent],
    source: str,
    source_offset: int,
    normalize: bool,
    previous_end: int | None,
    next_start: int | None,
    is_first: bool,
) -> None:
    if not is_first:
        gap = ""
        if previous_end is not None and next_start is not None:
            gap_start = max(0, previous_end - source_offset)
            gap_end = max(gap_start, next_start - source_offset)
            gap = source[gap_start:gap_end]
        position = builder.length
        builder.separate(gap)
        events.append(
            StructuralEvent(
                position,
                "paragraph",
                "after",
                {},
                previous_end,
                next_start,
            )
        )
    if isinstance(node, ParagraphNode):
        _emit_inline_nodes(node.children, builder, annotations, events)
    elif isinstance(node, HeadingNode):
        events.append(
            StructuralEvent(
                builder.length,
                "heading",
                "before",
                {"level": str(node.level)},
                node.source_start,
                node.source_end,
            )
        )
        _emit_inline_nodes(node.children, builder, annotations, events)
    elif isinstance(node, DirectiveNode):
        start = builder.length
        _emit_blocks(
            node.children,
            builder,
            annotations,
            events,
            source,
            source_offset,
            normalize,
        )
        end = builder.length
        if node.attrs and end > start:
            attrs = _tagged_annotation_attrs(node.attrs, "directive")
            annotations.append(
                AnnotationSpan(
                    start,
                    end,
                    attrs,
                    kind="directive",
                    source_start=node.source_start,
                    source_end=node.source_end,
                )
            )


def _emit_blocks(
    nodes: tuple[Node, ...],
    builder: _CleanTextBuilder,
    annotations: list[AnnotationSpan],
    events: list[StructuralEvent],
    source: str,
    source_offset: int,
    normalize: bool,
) -> None:
    previous: Node | None = None
    for index, node in enumerate(nodes):
        _emit_block(
            node,
            builder,
            annotations,
            events,
            source,
            source_offset,
            normalize,
            previous.source_end if previous is not None else None,
            node.source_start,
            index == 0,
        )
        previous = node


def _locate_diagnostic(source: str, diagnostic: Diagnostic) -> Diagnostic:
    if diagnostic.source_start is None:
        return diagnostic
    position = min(diagnostic.source_start, len(source))
    line = source.count("\n", 0, position) + 1
    line_start = source.rfind("\n", 0, position) + 1
    return Diagnostic(
        diagnostic.code,
        diagnostic.severity,
        diagnostic.message,
        diagnostic.source_start,
        diagnostic.source_end,
        line,
        position - line_start + 1,
        diagnostic.hint,
    )


def _front_matter_diagnostics(
    source: str,
    header: Mapping[str, Any],
    dialect: Literal["0.8", "0.9"],
) -> list[Diagnostic]:
    from ssmd.frontmatter import validate_front_matter

    diagnostics = []
    for issue in validate_front_matter(header, dialect=dialect):
        start = source.find(issue.field) if issue.field else None
        if start is not None and start < 0:
            start = None
        end = start + len(issue.field) if start is not None and issue.field else None
        diagnostics.append(
            _locate_diagnostic(
                source,
                Diagnostic(
                    code=issue.code,
                    severity=cast(Literal["error", "warning", "info"], issue.severity),
                    message=issue.message,
                    source_start=start,
                    source_end=end,
                ),
            )
        )
    return diagnostics


def _parse_structure_09(
    source: str,
    body: str,
    header: dict[str, Any],
    body_offset: int,
    *,
    normalize: bool,
    default_lang: str | None,
    dialect: Literal["0.8", "0.9"],
) -> ParseStructureResult:
    tokens, diagnostics = tokenize_blocks(
        body,
        source_offset=body_offset,
        dialect=dialect,
    )
    diagnostics.extend(validate_token_semantics(tokens))
    root = ast_from_tokens(
        tokens,
        source_start=body_offset,
        source_end=body_offset + len(body),
    )
    builder = _CleanTextBuilder(normalize)
    annotations: list[AnnotationSpan] = []
    events: list[StructuralEvent] = []
    _emit_blocks(
        root.children,
        builder,
        annotations,
        events,
        body,
        body_offset,
        normalize,
    )
    clean_text = builder.build()
    if default_lang and clean_text:
        annotations.append(
            AnnotationSpan(
                0,
                len(clean_text),
                {"lang": default_lang, "tag": "lang"},
                kind="language",
                source_start=0,
                source_end=len(source),
            )
        )

    diagnostics = [_locate_diagnostic(source, item) for item in diagnostics]
    annotations.sort(key=lambda item: (item.char_start, -item.char_end, item.source_start or 0))
    result = ParseStructureResult(
        clean_text=clean_text,
        annotations=annotations,
        events=events,
        header=header,
        warnings=[item.message for item in diagnostics],
        diagnostics=diagnostics,
    )
    return result


def parse_structure(
    text: str,
    *,
    normalize: bool = True,
    default_lang: str | None = None,
    preserve_whitespace: bool | None = None,
    parse_yaml_header: bool = True,
    resolve_defaults: bool = False,
    dialect: Literal["auto", "0.8", "0.9"] = "auto",
) -> ParseStructureResult:
    """Parse SSMD structure with a source-aware structural parser.

    ``auto`` selects strict 0.9 syntax for a document declaring
    ``ssmd_version: "0.9"`` and the legacy 0.8 parser for unversioned input.
    Sentence detection is never invoked.
    """
    if dialect not in ("auto", "0.8", "0.9"):
        raise ValueError("dialect must be 'auto', '0.8', or '0.9'")
    if preserve_whitespace is not None:
        normalize = not preserve_whitespace

    header: dict[str, Any] = {}
    body = text
    body_offset = 0
    if parse_yaml_header:
        from ssmd.frontmatter import parse_front_matter

        front_matter = parse_front_matter(text)
        if front_matter.present:
            header = front_matter.data
            body = front_matter.body
            body_offset = len(text) - len(body)

    selected_dialect = dialect
    if selected_dialect == "auto":
        version = header.get("ssmd_version")
        selected_dialect = "0.9" if version not in (None, "0.8") else "0.8"
    if selected_dialect == "0.8":
        result = _parse_structure_legacy(
            text,
            normalize=normalize,
            default_lang=default_lang,
            preserve_whitespace=None,
            parse_yaml_header=parse_yaml_header,
            resolve_defaults=False,
        )
    else:
        result = _parse_structure_09(
            text,
            body,
            header,
            body_offset,
            normalize=normalize,
            default_lang=default_lang,
            dialect=selected_dialect,
        )
    if parse_yaml_header and header:
        header_diagnostics = _front_matter_diagnostics(text, header, selected_dialect)
        result.diagnostics.extend(header_diagnostics)
        result.warnings.extend(
            item.message for item in header_diagnostics if item.severity == "warning"
        )
    return resolve_structure_defaults(result) if resolve_defaults else result


def _parse_structure_legacy(
    text: str,
    *,
    normalize: bool = True,
    default_lang: str | None = None,
    preserve_whitespace: bool | None = None,
    parse_yaml_header: bool = True,
    resolve_defaults: bool = False,
) -> ParseStructureResult:
    """Parse SSMD structure without sentence detection.

    The result contains clean text, clean-text annotation ranges, zero-width
    break/mark/paragraph events, front matter, warnings, and diagnostics. No
    sentence splitter is invoked by this API.

    Args:
        text: SSMD markdown text.
        normalize: Normalize whitespace between structural segments.
        default_lang: Optional language annotation for the complete output.
        preserve_whitespace: Deprecated compatibility option for ``normalize``.
        parse_yaml_header: Parse and remove YAML front matter.
    """
    if not text:
        return ParseStructureResult(clean_text="")

    header: dict[str, Any] = {}
    if parse_yaml_header:
        from ssmd.frontmatter import parse_front_matter

        front_matter = parse_front_matter(text)
        if front_matter.present:
            header = front_matter.data
            text = front_matter.body

    if preserve_whitespace is not None:
        normalize = not preserve_whitespace

    warnings: list[str] = []
    annotations: list[AnnotationSpan] = []
    events: list[StructuralEvent] = []
    blocks, directive_warnings = _split_directive_blocks_with_warnings(text)
    warnings.extend(directive_warnings)
    clean_text = ""

    for directive, block_text in blocks:
        block_start = len(clean_text)
        clean_text = _parse_structure_block(
            clean_text, block_text, annotations, events, warnings, normalize=normalize
        )
        block_end = len(clean_text)
        directive_attrs = _directive_attrs_to_map(directive)
        if directive_attrs and block_end > block_start:
            directive_attrs["tag"] = "div"
            annotations.append(
                AnnotationSpan(
                    char_start=block_start,
                    char_end=block_end,
                    attrs=directive_attrs,
                    kind="div",
                )
            )

    clean_text = unescape_ssmd_syntax(clean_text)
    if default_lang and clean_text:
        annotations.insert(
            0,
            AnnotationSpan(
                char_start=0,
                char_end=len(clean_text),
                attrs={"lang": default_lang},
                kind="language",
            ),
        )

    result = ParseStructureResult(
        clean_text=clean_text,
        annotations=annotations,
        events=events,
        header=header,
        warnings=warnings,
        diagnostics=diagnostics_from_warnings(text, warnings),
    )
    return resolve_structure_defaults(result) if resolve_defaults else result


def parse_spans(
    text: str,
    *,
    normalize: bool = True,
    default_lang: str | None = None,
    preserve_whitespace: bool | None = None,
    parse_yaml_header: bool = True,
    dialect: Literal["auto", "0.8", "0.9"] = "auto",
) -> ParseSpansResult:
    """Adapt the canonical structural parse to the legacy spans result type.

    Annotation offsets are 0-based, half-open coordinates in ``clean_text``.
    """
    structure = parse_structure(
        text,
        normalize=normalize,
        default_lang=default_lang,
        preserve_whitespace=preserve_whitespace,
        parse_yaml_header=parse_yaml_header,
        dialect=dialect,
    )
    return ParseSpansResult(
        clean_text=structure.clean_text,
        annotations=structure.annotations,
        warnings=structure.warnings,
        diagnostics=structure.diagnostics,
    )


def iter_sentences_spans(
    text_or_doc: str | Any,
    *,
    preserve_whitespace: bool = False,
    language: str | None = None,
    use_spacy: bool | None = None,
    spacy_model: str | None = None,
    model_size: SpacyModelSize | None = None,
) -> list[tuple[str, int, int]]:
    """Iterate over sentence spans in clean text coordinates."""
    if not text_or_doc:
        return []

    text = text_or_doc
    if not isinstance(text_or_doc, str):
        text = text_or_doc.ssmd

    clean_text = parse_spans(text, preserve_whitespace=preserve_whitespace).clean_text
    if not clean_text:
        return []

    sent_texts = _split_sentences(
        clean_text,
        language=language,
        use_spacy=use_spacy,
        spacy_model=spacy_model,
        model_size=model_size,
        escape_annotations=False,
    )

    spans: list[tuple[str, int, int]] = []
    cursor = 0
    for sent_text in sent_texts:
        if not sent_text:
            continue
        if preserve_whitespace:
            sentence = sent_text
            start = cursor
            end = start + len(sentence)
            spans.append((sentence, start, end))
            cursor = end
            continue

        sentence = sent_text.strip()
        if not sentence:
            continue

        start = cursor
        while start < len(clean_text) and clean_text[start].isspace():
            start += 1
        end = start + len(sentence)
        spans.append((sentence, start, end))
        cursor = end

    return spans


def lint(
    text: str,
    profile: str = "ssmd-core",
    *,
    parse_yaml_header: bool = True,
    dialect: Literal["auto", "0.8", "0.9"] = "auto",
) -> list[LintIssue]:
    """Lint SSMD text against a capability profile.

    Offsets in lint issues refer to the clean text coordinate system.
    """
    from ssmd.capabilities import get_profile

    issues: list[LintIssue] = []
    spans = parse_spans(text, parse_yaml_header=parse_yaml_header, dialect=dialect)
    profile_data = get_profile(profile)
    if parse_yaml_header:
        from ssmd.frontmatter import parse_front_matter, voice_defaults

        front_matter = parse_front_matter(text)
        if front_matter.present:
            issues.extend(
                _voice_prosody_consistency_issues(
                    front_matter.body, voice_defaults(front_matter.data)
                )
            )
        else:
            issues.extend(_voice_prosody_consistency_issues(text, {}))
    for diagnostic in spans.diagnostics:
        issues.append(
            LintIssue(
                severity="warn" if diagnostic.severity == "warning" else diagnostic.severity,
                message=diagnostic.message,
                code=diagnostic.code,
                source_start=diagnostic.source_start,
                source_end=diagnostic.source_end,
                line=diagnostic.line,
                column=diagnostic.column,
            )
        )

    for annotation in spans.annotations:
        attrs = annotation.attrs
        tag = attrs.get("tag") or annotation.kind

        if tag and tag not in profile_data.inline_tags and tag not in profile_data.block_tags:
            issues.append(
                LintIssue(
                    severity="error",
                    message=f"Tag '{tag}' is not supported by profile '{profile}'.",
                    char_start=annotation.char_start,
                    char_end=annotation.char_end,
                )
            )
            continue

        if tag:
            allowed_attrs = profile_data.attributes.get(tag, set())
            if allowed_attrs:
                for key in attrs:
                    canonical_key = "level" if tag == "emphasis" and key == "emphasis" else key
                    if key in {"tag", "name"}:
                        continue
                    if canonical_key not in allowed_attrs:
                        issues.append(
                            LintIssue(
                                severity="warn",
                                message=(
                                    f"Attribute '{key}' is not supported for '{tag}' "
                                    f"in profile '{profile}'."
                                ),
                                char_start=annotation.char_start,
                                char_end=annotation.char_end,
                                code="profile.unsupported_attribute",
                            )
                        )

    return issues


def _voice_prosody_consistency_issues(
    body: str,
    defaults: Mapping[str, VoiceProsodyDefaults] | VoiceDefaults,
) -> list[LintIssue]:
    """Return warnings for omitted fields on otherwise explicit voices."""
    counts: dict[str, dict[str, dict[str, int]]] = {}
    for directive, _ in _split_directive_blocks(body):
        if not directive.voice or not directive.voice.name:
            continue
        voice_name = directive.voice.name
        voice_counts = counts.setdefault(
            voice_name,
            {
                field_name: {"explicit": 0, "omitted": 0}
                for field_name in ("volume", "rate", "pitch")
            },
        )
        for field_name in ("volume", "rate", "pitch"):
            default = defaults.get(voice_name)
            if default and getattr(default, field_name):
                continue
            if directive.prosody and getattr(directive.prosody, field_name):
                voice_counts[field_name]["explicit"] += 1
            else:
                voice_counts[field_name]["omitted"] += 1

    issues: list[LintIssue] = []
    for voice_name, voice_counts in counts.items():
        for field_name, field_counts in voice_counts.items():
            if field_counts["explicit"] and field_counts["omitted"]:
                issues.append(
                    LintIssue(
                        severity="warn",
                        message=(
                            f"Voice '{voice_name}' explicitly uses {field_name} "
                            f"in {field_counts['explicit']} blocks but omits {field_name} "
                            f"in {field_counts['omitted']} blocks. Consider "
                            f"voice_defaults.{voice_name}.{field_name}."
                        ),
                        code="voice.prosody_inconsistent",
                    )
                )
    return issues


def _filter_sentences(sentences: list[Sentence], caps: "TTSCapabilities") -> None:  # noqa: C901
    for sentence in sentences:
        if sentence.language and not caps.language_scopes.get("sentence", True):
            sentence.language = None

        if sentence.prosody:
            if not caps.prosody:
                sentence.prosody = None
            else:
                if not caps.volume:
                    sentence.prosody.volume = None
                if not caps.rate:
                    sentence.prosody.rate = None
                if not caps.pitch:
                    sentence.prosody.pitch = None
                if not any(
                    [
                        sentence.prosody.volume,
                        sentence.prosody.rate,
                        sentence.prosody.pitch,
                    ]
                ):
                    sentence.prosody = None

        for segment in sentence.segments:
            if segment.audio and not caps.audio:
                segment.audio = None
            if segment.say_as and not caps.say_as:
                segment.say_as = None
            if segment.emphasis and not caps.emphasis:
                segment.emphasis = False
            if segment.language and not caps.language_scopes.get("sentence", True):
                segment.language = None
            if segment.phoneme and not caps.phoneme:
                segment.phoneme = None
            if segment.substitution and not caps.substitution:
                segment.substitution = None
            if segment.extension and not caps.supports_extension(segment.extension):
                segment.extension = None
            if segment.prosody:
                if not caps.prosody:
                    segment.prosody = None
                else:
                    if not caps.volume:
                        segment.prosody.volume = None
                    if not caps.rate:
                        segment.prosody.rate = None
                    if not caps.pitch:
                        segment.prosody.pitch = None
                    if not any(
                        [
                            segment.prosody.volume,
                            segment.prosody.rate,
                            segment.prosody.pitch,
                        ]
                    ):
                        segment.prosody = None
            if not caps.break_tags:
                segment.breaks_before = []
                segment.breaks_after = []
            if not caps.mark:
                segment.marks_before = []
                segment.marks_after = []

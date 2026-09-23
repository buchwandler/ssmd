"""SSMD - Speech Synthesis Markdown to SSML converter.

SSMD provides a lightweight markdown-like syntax for creating SSML
(Speech Synthesis Markup Language) documents. It's designed to be
more human-friendly than raw SSML while maintaining full compatibility.

Example:
    Basic usage::

        import ssmd

        # Create and build a document
        doc = ssmd.Document()
        doc.add_sentence("Hello *world*!")
        doc.add_sentence("This is SSMD.")

        # Export to different formats
        ssml = doc.to_ssml()
        text = doc.to_text()

        # Or use convenience functions for one-off conversions
        ssml = ssmd.to_ssml("Hello *world*!")

    Advanced usage with streaming::

        # Create parser with custom config
        doc = ssmd.Document(
            capabilities='pyttsx3',
            config={'auto_sentence_tags': True}
        )

        # Build document incrementally
        doc.add_paragraph("# Welcome")
        doc.add_sentence("Hello and *welcome* to SSMD!")

        # Stream to TTS
        for sentence in doc.sentences():
            tts_engine.speak(sentence)
"""

from collections.abc import Iterable
from typing import Any

import ssmd  # noqa: F401 - keeps module-qualified doctest examples executable
from ssmd.capabilities import (
    AMAZON_POLLY_CAPABILITIES,
    AZURE_TTS_CAPABILITIES,
    ESPEAK_CAPABILITIES,
    FULL_CAPABILITIES,
    GOOGLE_TTS_CAPABILITIES,
    MINIMAL_CAPABILITIES,
    PYTTSX3_CAPABILITIES,
    CapabilityProfile,
    TTSCapabilities,
    get_preset,
    get_profile,
    list_presets,
    list_profiles,
)
from ssmd.config import PauseDefaults
from ssmd.document import Document
from ssmd.formatter import (
    FormatError,
    format_canonical,
    format_ssmd,
    normalize_line_endings,
)
from ssmd.frontmatter import (
    FrontMatter,
    FrontMatterError,
    language_detection_hint,
    merge_generated_header,
    parse_front_matter,
    prosody_transitions,
    serialize_front_matter,
    voice_defaults,
)
from ssmd.paragraph import Paragraph
from ssmd.parser import (
    iter_sentences_spans,
    lint,
    parse_paragraphs,
    parse_segments,
    parse_sentences,
    parse_spans,
    parse_ssmd,
    parse_structure,
    parse_voice_blocks,
    resolve_structure_defaults,
)
from ssmd.rendering import LossPolicy, RenderError, RenderResult, RenderTarget, render_structure
from ssmd.segment import ExtensionHandler, Segment
from ssmd.sentence import Sentence
from ssmd.spans import (
    AnnotationSpan,
    Diagnostic,
    LintIssue,
    ParseSpansResult,
    ParseStructureResult,
    SentenceSpanLike,
    StructuralEvent,
)
from ssmd.ssml_parser import SSMLConversionError, SSMLParser
from ssmd.types import (
    DEFAULT_HEADING_LEVELS,
    AudioAttrs,
    BreakAttrs,
    DirectiveAttrs,
    HeadingConfig,
    LanguageAttrs,
    LanguageDetectionHint,
    LanguageDetectionMode,
    LanguageScope,
    ParsedResult,
    PhonemeAttrs,
    ProsodyAttrs,
    ProsodyTransitionDefaults,
    SayAsAttrs,
    SentenceDetectionConfig,
    SentenceDetectionDiagnostics,
    SpacyModelSize,
    VoiceAttrs,
    VoiceDefaults,
    VoiceProsodyDefaults,
)
from ssmd.utils import escape_ssmd_syntax, unescape_ssmd_syntax
from ssmd.voices import (
    VoiceMaterializationPlan,
    VoiceReferenceUse,
    VoiceResolution,
    extract_voice_references,
    resolve_voice,
)

SSMDSegment = Segment
SSMDSentence = Sentence
SSMDParagraph = Paragraph

try:
    from ssmd._version import version as __version__
except ImportError:
    __version__ = "unknown"


# ═══════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════


def to_ssml(
    ssmd_text: str,
    *,
    parse_yaml_header: bool = True,
    sentence_spans: Iterable[SentenceSpanLike] | None = None,
    **config: Any,
) -> str:
    """Convert SSMD to SSML (convenience function).

    Creates a temporary Document and converts to SSML.
    For repeated conversions with the same config, create a Document instance.

    Args:
        ssmd_text: SSMD markdown text
        **config: Optional configuration parameters
    sentence_spans: Optional external sentence boundaries with zero-based, half-open
        offsets in the structural clean-text coordinate space.

    Returns:
        SSML string

    Example:
        >>> ssmd.to_ssml("Hello *world*!")
        '<speak><p>Hello <emphasis>world</emphasis>!</p></speak>'
    """
    return Document(
        ssmd_text,
        config,
        parse_yaml_header=parse_yaml_header,
    ).to_ssml(sentence_spans=sentence_spans)


def to_text(ssmd_text: str, *, parse_yaml_header: bool = True, **config: Any) -> str:
    """Convert SSMD to plain text (convenience function).

    Strips all SSMD markup, returning plain text.

    Args:
        ssmd_text: SSMD markdown text
        **config: Optional configuration parameters

    Returns:
        Plain text with markup removed

    Example:
        >>> ssmd.to_text("Hello *world* @marker!")
        'Hello world @marker!'
    """
    return Document(ssmd_text, config, parse_yaml_header=parse_yaml_header).to_text()


def from_ssml(
    ssml_text: str,
    *,
    capabilities: "TTSCapabilities | str | None" = None,
    complete_document: bool = True,
    **config: Any,
) -> str:
    """Convert SSML to SSMD 0.9, returning a versioned document by default.

    Set ``complete_document=False`` to return only the SSMD body fragment.
    """
    parser = SSMLParser(config)
    return parser.to_ssmd(
        ssml_text,
        capabilities=capabilities,
        complete_document=complete_document,
    )


__all__ = [
    "Document",
    "FrontMatter",
    "FrontMatterError",
    "PauseDefaults",
    "to_ssml",
    "to_text",
    "from_ssml",
    "parse_front_matter",
    "serialize_front_matter",
    "language_detection_hint",
    "merge_generated_header",
    "voice_defaults",
    "prosody_transitions",
    "SSMLParser",
    "SSMLConversionError",
    "RenderTarget",
    "LossPolicy",
    "RenderResult",
    "RenderError",
    "render_structure",
    "TTSCapabilities",
    "get_preset",
    # Capability presets
    "ESPEAK_CAPABILITIES",
    "PYTTSX3_CAPABILITIES",
    "GOOGLE_TTS_CAPABILITIES",
    "AMAZON_POLLY_CAPABILITIES",
    "AZURE_TTS_CAPABILITIES",
    "MINIMAL_CAPABILITIES",
    "FULL_CAPABILITIES",
    # Parser functions
    "parse_paragraphs",
    "parse_ssmd",
    "parse_sentences",
    "parse_segments",
    "parse_voice_blocks",
    "extract_voice_references",
    "resolve_voice",
    "parse_spans",
    "parse_structure",
    "resolve_structure_defaults",
    "iter_sentences_spans",
    "lint",
    "FormatError",
    "format_canonical",
    "normalize_line_endings",
    "format_ssmd",
    # Utility functions
    "escape_ssmd_syntax",
    "unescape_ssmd_syntax",
    # New core classes
    "Segment",
    "ExtensionHandler",
    "Sentence",
    "Paragraph",
    # Types
    "VoiceAttrs",
    "ProsodyAttrs",
    "ProsodyTransitionDefaults",
    "VoiceDefaults",
    "VoiceProsodyDefaults",
    "BreakAttrs",
    "SayAsAttrs",
    "AudioAttrs",
    "PhonemeAttrs",
    "DirectiveAttrs",
    "LanguageScope",
    "LanguageAttrs",
    "LanguageDetectionMode",
    "LanguageDetectionHint",
    "SpacyModelSize",
    "SentenceDetectionConfig",
    "SentenceDetectionDiagnostics",
    "ParsedResult",
    "HeadingConfig",
    "DEFAULT_HEADING_LEVELS",
    "CapabilityProfile",
    "get_profile",
    "list_profiles",
    "list_presets",
    "Diagnostic",
    "LintIssue",
    "SentenceSpanLike",
    "AnnotationSpan",
    "ParseSpansResult",
    "ParseStructureResult",
    "StructuralEvent",
    "VoiceReferenceUse",
    "VoiceResolution",
    "VoiceMaterializationPlan",
    # Backward compatibility aliases
    "SSMDSegment",
    "SSMDSentence",
    "SSMDParagraph",
    "__version__",
]

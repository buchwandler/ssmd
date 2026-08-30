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
from ssmd.formatter import format_ssmd
from ssmd.frontmatter import (
    FrontMatter,
    FrontMatterError,
    merge_generated_header,
    parse_front_matter,
    serialize_front_matter,
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
)
from ssmd.segment import ExtensionHandler, Segment
from ssmd.sentence import Sentence
from ssmd.spans import (
    AnnotationSpan,
    LintIssue,
    ParseSpansResult,
    ParseStructureResult,
    StructuralEvent,
)
from ssmd.ssml_parser import SSMLParser
from ssmd.types import (
    DEFAULT_HEADING_LEVELS,
    AudioAttrs,
    BreakAttrs,
    DirectiveAttrs,
    HeadingConfig,
    ParsedResult,
    PhonemeAttrs,
    ProsodyAttrs,
    SayAsAttrs,
    SentenceDetectionConfig,
    SentenceDetectionDiagnostics,
    SpacyModelSize,
    VoiceAttrs,
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


def to_ssml(ssmd_text: str, *, parse_yaml_header: bool = True, **config: Any) -> str:
    """Convert SSMD to SSML (convenience function).

    Creates a temporary Document and converts to SSML.
    For repeated conversions with the same config, create a Document instance.

    Args:
        ssmd_text: SSMD markdown text
        **config: Optional configuration parameters

    Returns:
        SSML string

    Example:
        >>> ssmd.to_ssml("Hello *world*!")
        '<speak><p>Hello <emphasis>world</emphasis>!</p></speak>'
    """
    return Document(ssmd_text, config, parse_yaml_header=parse_yaml_header).to_ssml()


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
    **config: Any,
) -> str:
    """Convert SSML to SSMD format (convenience function).

    Args:
        ssml_text: SSML XML string
        capabilities: Optional TTS capabilities (preset name or object)
        **config: Optional configuration parameters

    Returns:
        SSMD markdown string

    Example:
        >>> ssml = '<speak><emphasis>Hello</emphasis> world</speak>'
        >>> ssmd.from_ssml(ssml)
        '*Hello* world\\n'
    """
    parser = SSMLParser(config)
    return parser.to_ssmd(ssml_text, capabilities=capabilities)


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
    "merge_generated_header",
    "SSMLParser",
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
    "iter_sentences_spans",
    "lint",
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
    "BreakAttrs",
    "SayAsAttrs",
    "AudioAttrs",
    "PhonemeAttrs",
    "DirectiveAttrs",
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
    "LintIssue",
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

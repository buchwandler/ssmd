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

from ssmd.document import Document
from ssmd.paragraph import Paragraph
from ssmd.ssml_parser import SSMLParser
from ssmd.capabilities import (
    TTSCapabilities,
    get_preset,
    ESPEAK_CAPABILITIES,
    PYTTSX3_CAPABILITIES,
    GOOGLE_TTS_CAPABILITIES,
    AMAZON_POLLY_CAPABILITIES,
    AZURE_TTS_CAPABILITIES,
    MINIMAL_CAPABILITIES,
    FULL_CAPABILITIES,
    CapabilityProfile,
    get_profile,
    list_profiles,
    list_presets,
)
from ssmd.parser import (
    parse_paragraphs,
    parse_ssmd,
    parse_sentences,
    parse_segments,
    parse_voice_blocks,
    parse_spans,
    iter_sentences_spans,
    lint,
)
from ssmd.spans import LintIssue, AnnotationSpan, ParseSpansResult
from ssmd.parser_types import (
    SSMDSegment,
    SSMDSentence,
    SSMDParagraph,
    VoiceAttrs,
    ProsodyAttrs,
    BreakAttrs,
    SayAsAttrs,
    AudioAttrs,
    PhonemeAttrs,
)
from ssmd.segment import ExtensionHandler, Segment
from ssmd.sentence import Sentence
from ssmd.types import (
    HeadingConfig,
    DEFAULT_HEADING_LEVELS,
)
from ssmd.formatter import format_ssmd
from ssmd.utils import escape_ssmd_syntax, unescape_ssmd_syntax

try:
    from ssmd._version import version as __version__
except ImportError:
    __version__ = "unknown"


# ═══════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════


def to_ssml(ssmd_text: str, *, parse_yaml_header: bool = False, **config: Any) -> str:
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
        '<speak>Hello <emphasis>world</emphasis>!</speak>'
    """
    return Document(ssmd_text, config, parse_yaml_header=parse_yaml_header).to_ssml()


def to_text(ssmd_text: str, *, parse_yaml_header: bool = False, **config: Any) -> str:
    """Convert SSMD to plain text (convenience function).

    Strips all SSMD markup, returning plain text.

    Args:
        ssmd_text: SSMD markdown text
        **config: Optional configuration parameters

    Returns:
        Plain text with markup removed

    Example:
        >>> ssmd.to_text("Hello *world* @marker!")
        'Hello world!'
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
        '*Hello* world'
    """
    parser = SSMLParser(config)
    return parser.to_ssmd(ssml_text, capabilities=capabilities)


__all__ = [
    "Document",
    "to_ssml",
    "to_text",
    "from_ssml",
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
    "parse_spans",
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
    "HeadingConfig",
    "DEFAULT_HEADING_LEVELS",
    "CapabilityProfile",
    "get_profile",
    "list_profiles",
    "list_presets",
    "LintIssue",
    "AnnotationSpan",
    "ParseSpansResult",
    # Backward compatibility aliases
    "SSMDSegment",
    "SSMDSentence",
    "SSMDParagraph",
    "__version__",
]

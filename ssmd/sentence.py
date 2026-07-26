"""Sentence - A collection of segments with voice context.

A Sentence represents a logical unit of speech that should be spoken together.
Sentences contain segments and have an optional voice context.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ssmd.segment import Segment
from ssmd.ssml_conversions import SSMD_BREAK_STRENGTH_MAP
from ssmd.types import BreakAttrs, ProsodyAttrs, VoiceAttrs

if TYPE_CHECKING:
    from ssmd.capabilities import TTSCapabilities


@dataclass
class Sentence:
    """A sentence containing segments with directive context.

    Represents a logical sentence unit that should be spoken together.
    Sentences are split on:
    - Directive changes (<div ...> blocks)
    - Sentence boundaries (.!?) when sentence_detection=True
    - Paragraph breaks (\n\n)

    Attributes:
        segments: List of segments in the sentence
        voice: Voice context for entire sentence (from <div voice=...> directives)
        language: Language directive for the sentence
        prosody: Prosody directive for the sentence
        is_paragraph_end: True if sentence ends with paragraph break
        paragraph_index: Zero-based paragraph index for this sentence
        sentence_index: Zero-based sentence index within the document
        breaks_after: Pauses after the sentence
    """

    segments: list[Segment] = field(default_factory=list)
    voice: VoiceAttrs | None = None
    language: str | None = None
    prosody: ProsodyAttrs | None = None
    is_paragraph_end: bool = False
    paragraph_index: int = 0
    sentence_index: int = 0
    breaks_after: list[BreakAttrs] = field(default_factory=list)

    def to_ssml(
        self,
        capabilities: "TTSCapabilities | None" = None,
        extensions: dict | None = None,
        wrap_sentence: bool = False,
        warnings: list[str] | None = None,
    ) -> str:
        """Convert sentence to SSML.

        Args:
            capabilities: TTS engine capabilities for filtering
            extensions: Custom extension handlers
            wrap_sentence: If True, wrap content in <s> tag
            warnings: Optional list to collect warnings

        Returns:
            SSML string
        """
        # Build segment content
        content_parts = []
        for segment in self.segments:
            content_parts.append(
                segment.to_ssml(
                    capabilities,
                    extensions,
                    warnings=warnings,
                )
            )

        # Join segments with spaces, but handle punctuation intelligently
        content = self._join_segments(content_parts)

        # Wrap in <s> tag if requested
        if wrap_sentence:
            content = f"<s>{content}</s>"

        # Apply directive wrappers (voice/language/prosody)
        content = self._wrap_directives(content, capabilities, warnings)

        # Add breaks after sentence
        if not capabilities or capabilities.break_tags:
            for brk in self.breaks_after:
                content += self._break_to_ssml(brk)

        return content

    def _join_segments(self, parts: list[str]) -> str:
        """Join SSML segment parts with appropriate spacing.

        Adds spaces between segments but not before punctuation.

        Args:
            parts: List of SSML strings for each segment

        Returns:
            Joined SSML string
        """
        import re

        if not parts:
            return ""

        result = parts[0]
        for i in range(1, len(parts)):
            part = parts[i]
            # Don't add space before punctuation or if part starts with <break
            if part and (
                re.match(r'^[.!?,;:\'")\]}>]', part)
                or part.startswith("<break")
                or part.startswith("<mark")
            ):
                result += part
            # Don't add space if previous part ends with opening bracket/quote
            elif result and result[-1] in "([{<\"'":
                result += part
            else:
                result += " " + part

        return result

    def _wrap_directives(
        self,
        content: str,
        capabilities: "TTSCapabilities | None",
        warnings: list[str] | None,
    ) -> str:
        """Apply voice, language, and prosody directives."""
        from ssmd.segment import _escape_xml_attr

        if self.voice:
            attrs = []
            if self.voice.name:
                name = _escape_xml_attr(self.voice.name)
                attrs.append(f'name="{name}"')
            else:
                if self.voice.language:
                    lang = _escape_xml_attr(self.voice.language)
                    attrs.append(f'language="{lang}"')
                if self.voice.gender:
                    gender = _escape_xml_attr(self.voice.gender)
                    attrs.append(f'gender="{gender}"')
                if self.voice.variant:
                    variant = _escape_xml_attr(str(self.voice.variant))
                    attrs.append(f'variant="{variant}"')

            if attrs:
                content = f"<voice {' '.join(attrs)}>{content}</voice>"

        if self.language and (not capabilities or capabilities.language):
            if not capabilities or capabilities.language_scopes.get("sentence", True):
                lang_escaped = _escape_xml_attr(self.language)
                content = f'<lang xml:lang="{lang_escaped}">{content}</lang>'
            elif warnings is not None:
                warnings.append(
                    f"Language scope 'sentence' not supported, dropping lang={self.language}"
                )

        if self.prosody and (not capabilities or capabilities.prosody):
            prosody_attrs = []
            if self.prosody.volume and (not capabilities or capabilities.volume):
                vol = _escape_xml_attr(self.prosody.volume)
                prosody_attrs.append(f'volume="{vol}"')
            if self.prosody.rate and (not capabilities or capabilities.rate):
                rate = _escape_xml_attr(self.prosody.rate)
                prosody_attrs.append(f'rate="{rate}"')
            if self.prosody.pitch and (not capabilities or capabilities.pitch):
                pitch = _escape_xml_attr(self.prosody.pitch)
                prosody_attrs.append(f'pitch="{pitch}"')

            if prosody_attrs:
                content = f"<prosody {' '.join(prosody_attrs)}>{content}</prosody>"

        return content

    def _break_to_ssml(self, brk: BreakAttrs) -> str:
        """Convert break to SSML."""
        from ssmd.segment import _escape_xml_attr

        if brk.time:
            time = _escape_xml_attr(brk.time)
            return f'<break time="{time}"/>'
        elif brk.strength:
            strength = _escape_xml_attr(brk.strength)
            return f'<break strength="{strength}"/>'
        return "<break/>"

    def to_ssmd(self) -> str:
        """Convert sentence to SSMD markdown.

        Returns:
            SSMD string
        """
        result = ""

        # Build segment content
        content_parts = [segment.to_ssmd() for segment in self.segments]
        result += self._join_text_parts(content_parts)

        # Add breaks after sentence
        for brk in self.breaks_after:
            result += " " + self._break_to_ssmd(brk)

        return result

    def _break_to_ssmd(self, brk: BreakAttrs) -> str:
        """Convert break to SSMD format."""
        if brk.time:
            return f"...{brk.time}"
        elif brk.strength:
            return SSMD_BREAK_STRENGTH_MAP.get(brk.strength, "...s")
        return "...s"

    def to_text(self) -> str:
        """Convert sentence to plain text.

        Returns:
            Plain text with all markup removed
        """
        text_parts = [segment.to_text() for segment in self.segments]
        return self._join_text_parts(text_parts)

    def _join_text_parts(self, parts: list[str]) -> str:
        """Join text parts with appropriate spacing.

        Adds spaces between parts but not before punctuation.

        Args:
            parts: List of text strings for each segment

        Returns:
            Joined text string
        """
        import re

        if not parts:
            return ""

        # Filter out empty parts
        parts = [p for p in parts if p]
        if not parts:
            return ""

        result = parts[0]
        for i in range(1, len(parts)):
            part = parts[i]
            # Don't add space before punctuation
            if part and re.match(r'^[.!?,;:\'")\]}>]', part):
                result += part
            # Don't add space if previous part ends with opening bracket/quote
            elif result and result[-1] in "([{<\"'":
                result += part
            else:
                result += " " + part

        return result

    @property
    def text(self) -> str:
        """Get plain text content of the sentence.

        Returns:
            Plain text string
        """
        return self.to_text()

    def __str__(self) -> str:
        """String representation returns plain text."""
        return self.to_text()

    def __len__(self) -> int:
        """Return number of segments."""
        return len(self.segments)

    def __iter__(self):
        """Iterate over segments."""
        return iter(self.segments)

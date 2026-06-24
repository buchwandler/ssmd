"""Segment - A piece of text with SSMD attributes.

A Segment represents a portion of text with specific formatting and processing
attributes. Segments are combined to form sentences.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ssmd.ssml_conversions import PROSODY_PITCH_MAP as PITCH_MAP
from ssmd.ssml_conversions import PROSODY_RATE_MAP as RATE_MAP
from ssmd.ssml_conversions import PROSODY_VOLUME_MAP as VOLUME_MAP
from ssmd.ssml_conversions import SSMD_BREAK_STRENGTH_MAP
from ssmd.types import (
    AudioAttrs,
    BreakAttrs,
    PhonemeAttrs,
    ProsodyAttrs,
    SayAsAttrs,
    VoiceAttrs,
)
from ssmd.utils import format_ssmd_attr

if TYPE_CHECKING:
    from ssmd.capabilities import TTSCapabilities


# Language code defaults (2-letter code -> full locale)
LANGUAGE_DEFAULTS = {
    "en": "en-US",
    "de": "de-DE",
    "fr": "fr-FR",
    "es": "es-ES",
    "it": "it-IT",
    "pt": "pt-PT",
    "ru": "ru-RU",
    "zh": "zh-CN",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "ar": "ar-SA",
    "hi": "hi-IN",
    "nl": "nl-NL",
    "pl": "pl-PL",
    "sv": "sv-SE",
    "da": "da-DK",
    "no": "no-NO",
    "fi": "fi-FI",
}


AMAZON_SSML_NAMESPACE = "https://amazon.com/ssml"


@dataclass(frozen=True)
class ExtensionHandler:
    handler: Callable[[str], str]
    namespaces: dict[str, str] = field(default_factory=dict)

    def __call__(self, text: str) -> str:
        return self.handler(text)


def _amazon_effect_handler(effect_name: str) -> ExtensionHandler:
    def _handler(text: str) -> str:
        return f'<amazon:effect name="{effect_name}">{text}</amazon:effect>'

    return ExtensionHandler(
        handler=_handler,
        namespaces={"amazon": AMAZON_SSML_NAMESPACE},
    )


# Default extension handlers
DEFAULT_EXTENSIONS = {
    "whisper": _amazon_effect_handler("whispered"),
    "drc": _amazon_effect_handler("drc"),
}


def _escape_xml_attr(value: str) -> str:
    """Escape a value for use in an XML attribute.

    Args:
        value: The attribute value to escape

    Returns:
        Escaped string safe for XML attribute
    """
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _escape_xml_text(value: str) -> str:
    """Escape a value for use in XML text content.

    Args:
        value: The text content to escape

    Returns:
        Escaped string safe for XML text
    """
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# X-SAMPA to IPA conversion table (lazy-loaded)
_XSAMPA_TABLE: dict[str, str] | None = None


def _load_xsampa_table() -> dict[str, str]:
    """Load X-SAMPA to IPA conversion table."""
    global _XSAMPA_TABLE
    if _XSAMPA_TABLE is not None:
        return _XSAMPA_TABLE

    table = {}
    # Try both old and new locations
    table_paths = [
        Path(__file__).parent / "xsampa_to_ipa.txt",
        Path(__file__).parent / "annotations" / "xsampa_to_ipa.txt",
    ]

    for table_file in table_paths:
        if table_file.exists():
            with open(table_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split(maxsplit=1)
                        if len(parts) == 2:
                            xsampa, ipa = parts
                            table[xsampa] = ipa
            break

    _XSAMPA_TABLE = table
    return table


def xsampa_to_ipa(xsampa: str) -> str:
    """Convert X-SAMPA notation to IPA.

    Args:
        xsampa: X-SAMPA phoneme string

    Returns:
        IPA phoneme string
    """
    table = _load_xsampa_table()

    # Sort by length (longest first) for proper replacement
    sorted_keys = sorted(table.keys(), key=len, reverse=True)

    result = xsampa
    for x in sorted_keys:
        result = result.replace(x, table[x])

    return result


def expand_language_code(code: str) -> str:
    """Expand 2-letter language code to full BCP-47 locale.

    Args:
        code: Language code (e.g., "en", "en-US")

    Returns:
        Full locale code (e.g., "en-US")
    """
    if code in LANGUAGE_DEFAULTS:
        return LANGUAGE_DEFAULTS[code]
    return code


@dataclass
class Segment:
    """A segment of text with SSMD features.

    Represents a portion of text with specific formatting and processing attributes.
    Segments are the atomic units of SSMD content.

    Attributes:
        text: Raw text content
        emphasis: Emphasis level (True/"moderate", "strong", "reduced", "none", False)
        prosody: Volume, rate, pitch settings
        language: Language code for this segment
        voice: Voice settings for this segment
        say_as: Text interpretation hints
        substitution: Replacement text (alias)
        phoneme: IPA pronunciation
        audio: Audio file to play
        extension: Platform-specific extension name
        breaks_before: Pauses before this segment
        breaks_after: Pauses after this segment
        marks_before: Event markers before this segment
        marks_after: Event markers after this segment
    """

    text: str

    # Styling features
    emphasis: bool | str = False  # True/"moderate", "strong", "reduced", "none"
    prosody: ProsodyAttrs | None = None
    language: str | None = None
    voice: VoiceAttrs | None = None

    # Text transformation features
    say_as: SayAsAttrs | None = None
    substitution: str | None = None
    phoneme: PhonemeAttrs | None = None

    # Media
    audio: AudioAttrs | None = None

    # Platform-specific
    extension: str | None = None

    # Breaks and marks
    breaks_before: list[BreakAttrs] = field(default_factory=list)
    breaks_after: list[BreakAttrs] = field(default_factory=list)
    marks_before: list[str] = field(default_factory=list)
    marks_after: list[str] = field(default_factory=list)

    def to_ssml(
        self,
        capabilities: "TTSCapabilities | None" = None,
        extensions: dict | None = None,
        warnings: list[str] | None = None,
    ) -> str:
        """Convert segment to SSML.

        Args:
            capabilities: TTS engine capabilities for filtering
            extensions: Custom extension handlers

        Returns:
            SSML string
        """
        result = ""

        # Add marks before
        if not capabilities or capabilities.mark:
            for mark in self.marks_before:
                mark_escaped = _escape_xml_attr(mark)
                result += f'<mark name="{mark_escaped}"/>'

        # Add breaks before
        if not capabilities or capabilities.break_tags:
            for brk in self.breaks_before:
                result += self._break_to_ssml(brk)

        # Build content with wrappers
        content = self._build_content_ssml(capabilities, extensions, warnings)
        result += content

        # Add breaks after
        if not capabilities or capabilities.break_tags:
            for brk in self.breaks_after:
                result += self._break_to_ssml(brk)

        # Add marks after
        if not capabilities or capabilities.mark:
            for mark in self.marks_after:
                mark_escaped = _escape_xml_attr(mark)
                result += f'<mark name="{mark_escaped}"/>'

        return result

    def _build_content_ssml(  # noqa: C901
        self,
        capabilities: "TTSCapabilities | None",
        extensions: dict | None,
        warnings: list[str] | None,
    ) -> str:
        """Build the main content SSML with all wrappers.

        Args:
            capabilities: TTS capabilities for filtering
            extensions: Custom extension handlers

        Returns:
            SSML content string
        """
        # Handle audio (replaces text)
        if self.audio:
            if capabilities and not capabilities.audio:
                return _escape_xml_text(self.text)  # Fallback to description
            return self._audio_to_ssml(self.audio)

        # Start with escaped text
        content = _escape_xml_text(self.text)

        # Apply substitution
        if self.substitution:
            if not capabilities or capabilities.substitution:
                alias = _escape_xml_attr(self.substitution)
                content = f'<sub alias="{alias}">{content}</sub>'

        # Apply phoneme
        elif self.phoneme:
            if not capabilities or capabilities.phoneme:
                ph = self.phoneme.ph
                # Convert X-SAMPA to IPA if needed
                if self.phoneme.alphabet.lower() in ("x-sampa", "sampa"):
                    ph = xsampa_to_ipa(ph)
                ph = _escape_xml_attr(ph)
                content = f'<phoneme alphabet="ipa" ph="{ph}">{content}</phoneme>'

        # Apply say-as
        elif self.say_as:
            if not capabilities or capabilities.say_as:
                if not capabilities:
                    content = self._say_as_to_ssml(self.say_as, content)
                else:
                    if self._supports_say_as(capabilities):
                        content = self._say_as_to_ssml(self.say_as, content)
                    elif warnings is not None:
                        warnings.append(
                            f"say-as '{self.say_as.interpret_as}' not "
                            "supported, dropping"
                        )

        # Apply emphasis
        if self.emphasis:
            if not capabilities or capabilities.emphasis:
                if not capabilities:
                    content = self._emphasis_to_ssml(content)
                else:
                    level = self._emphasis_level_key()
                    if not level or capabilities.supports_key(level, default=True):
                        content = self._emphasis_to_ssml(content)
                    elif warnings is not None:
                        warnings.append("emphasis level not supported, dropping")

        # Apply prosody
        if self.prosody:
            if not capabilities or capabilities.prosody:
                content = self._prosody_to_ssml(self.prosody, content, capabilities)

        # Apply language
        if self.language:
            if not capabilities or capabilities.language:
                if not capabilities or capabilities.language_scopes.get(
                    "sentence", True
                ):
                    lang = expand_language_code(self.language)
                    lang_escaped = _escape_xml_attr(lang)
                    content = f'<lang xml:lang="{lang_escaped}">{content}</lang>'

        # Apply voice (inline) - note: TTSCapabilities doesn't have voice attr
        # Voice is always enabled as it's fundamental to TTS
        if self.voice:
            content = self._voice_to_ssml(self.voice, content)

        # Apply extension
        if self.extension:
            if capabilities and not capabilities.supports_extension(self.extension):
                if warnings is not None:
                    warnings.append(
                        f"extension '{self.extension}' not supported, dropping"
                    )
            else:
                ext_handlers = {**DEFAULT_EXTENSIONS, **(extensions or {})}
                handler = ext_handlers.get(self.extension)
                if handler:
                    content = handler(content)

        return content

    def _emphasis_to_ssml(self, content: str) -> str:
        """Convert emphasis to SSML."""
        if self.emphasis is True or self.emphasis == "moderate":
            return f"<emphasis>{content}</emphasis>"
        elif self.emphasis == "strong":
            return f'<emphasis level="strong">{content}</emphasis>'
        elif self.emphasis == "reduced":
            return f'<emphasis level="reduced">{content}</emphasis>'
        elif self.emphasis == "none":
            return f'<emphasis level="none">{content}</emphasis>'
        return content

    def _emphasis_level_key(self) -> str | None:
        if self.emphasis is True or self.emphasis == "moderate":
            return 'attribute values››level="moderate" (default)'
        if self.emphasis == "strong":
            return 'attribute values››level="strong"'
        if self.emphasis == "reduced":
            return 'attribute values››level="reduced"'
        if self.emphasis == "none":
            return 'attribute values››level="none"'
        return None

    def _supports_say_as(self, capabilities: "TTSCapabilities") -> bool:
        if not self.say_as:
            return True
        interpret = self.say_as.interpret_as
        base_key = f'elements››interpret-as="{interpret}"'
        if not capabilities.supports_key(base_key, default=capabilities.say_as):
            format_value = self.say_as.format
            if format_value:
                format_key = (
                    f'attribute values››interpret-as="{interpret}" '
                    f'format="{format_value}"'
                )
                return capabilities.supports_key(format_key, default=False)
            return False
        if self.say_as.format:
            format_key = (
                f'attribute values››interpret-as="{interpret}"'
                f'format="{self.say_as.format}"'
            )
            return capabilities.supports_key(format_key, default=True)
        return True

    def _prosody_to_ssml(
        self,
        prosody: ProsodyAttrs,
        content: str,
        capabilities: "TTSCapabilities | None",
    ) -> str:
        """Convert prosody to SSML."""
        attrs = []

        if prosody.volume and (not capabilities or capabilities.volume):
            # Map numeric to named if needed
            vol = VOLUME_MAP.get(prosody.volume, prosody.volume)
            vol = _escape_xml_attr(vol)
            attrs.append(f'volume="{vol}"')

        if prosody.rate and (not capabilities or capabilities.rate):
            rate = RATE_MAP.get(prosody.rate, prosody.rate)
            rate = _escape_xml_attr(rate)
            attrs.append(f'rate="{rate}"')

        if prosody.pitch and (not capabilities or capabilities.pitch):
            pitch = PITCH_MAP.get(prosody.pitch, prosody.pitch)
            pitch = _escape_xml_attr(pitch)
            attrs.append(f'pitch="{pitch}"')

        if attrs:
            return f"<prosody {' '.join(attrs)}>{content}</prosody>"
        return content

    def _voice_to_ssml(self, voice: VoiceAttrs, content: str) -> str:
        """Convert voice to SSML."""
        attrs = []

        if voice.name:
            name = _escape_xml_attr(voice.name)
            attrs.append(f'name="{name}"')
        else:
            if voice.language:
                lang = _escape_xml_attr(voice.language)
                attrs.append(f'language="{lang}"')
            if voice.gender:
                gender = _escape_xml_attr(voice.gender)
                attrs.append(f'gender="{gender}"')
            if voice.variant:
                variant = _escape_xml_attr(str(voice.variant))
                attrs.append(f'variant="{variant}"')

        if attrs:
            return f"<voice {' '.join(attrs)}>{content}</voice>"
        return content

    def _say_as_to_ssml(self, say_as: SayAsAttrs, content: str) -> str:
        """Convert say-as to SSML."""
        interpret = _escape_xml_attr(say_as.interpret_as)
        attrs = [f'interpret-as="{interpret}"']

        if say_as.format:
            fmt = _escape_xml_attr(say_as.format)
            attrs.append(f'format="{fmt}"')
        if say_as.detail:
            detail = _escape_xml_attr(str(say_as.detail))
            attrs.append(f'detail="{detail}"')

        return f"<say-as {' '.join(attrs)}>{content}</say-as>"

    def _audio_to_ssml(self, audio: AudioAttrs) -> str:
        """Convert audio to SSML."""
        src = _escape_xml_attr(audio.src)
        attrs = [f'src="{src}"']

        if audio.clip_begin:
            cb = _escape_xml_attr(audio.clip_begin)
            attrs.append(f'clipBegin="{cb}"')
        if audio.clip_end:
            ce = _escape_xml_attr(audio.clip_end)
            attrs.append(f'clipEnd="{ce}"')
        if audio.speed:
            speed = _escape_xml_attr(audio.speed)
            attrs.append(f'speed="{speed}"')
        if audio.repeat_count:
            rc = _escape_xml_attr(str(audio.repeat_count))
            attrs.append(f'repeatCount="{rc}"')
        if audio.repeat_dur:
            rd = _escape_xml_attr(audio.repeat_dur)
            attrs.append(f'repeatDur="{rd}"')
        if audio.sound_level:
            sl = _escape_xml_attr(audio.sound_level)
            attrs.append(f'soundLevel="{sl}"')

        desc = ""
        if self.text:
            desc_text = _escape_xml_text(self.text)
            desc = f"<desc>{desc_text}</desc>"
        alt = _escape_xml_text(audio.alt_text) if audio.alt_text else ""

        return f"<audio {' '.join(attrs)}>{desc}{alt}</audio>"

    def _break_to_ssml(self, brk: BreakAttrs) -> str:
        """Convert break to SSML."""
        if brk.time:
            time = _escape_xml_attr(brk.time)
            return f'<break time="{time}"/>'
        elif brk.strength:
            strength = _escape_xml_attr(brk.strength)
            return f'<break strength="{strength}"/>'
        return "<break/>"

    def to_ssmd(self) -> str:
        """Convert segment to SSMD markdown.

        Returns:
            SSMD string
        """
        result = ""

        # Add marks before
        for mark in self.marks_before:
            result += f"@{mark} "

        # Add breaks before
        for brk in self.breaks_before:
            result += self._break_to_ssmd(brk) + " "

        # Build content
        content = self._build_content_ssmd()
        result += content

        # Add breaks after
        for brk in self.breaks_after:
            result += " " + self._break_to_ssmd(brk)

        # Add marks after
        for mark in self.marks_after:
            result += f" @{mark}"

        return result

    def _build_content_ssmd(self) -> str:  # noqa: C901
        """Build SSMD content with markup."""
        text = self.text

        # Handle audio
        if self.audio:
            return self._audio_to_ssmd(self.audio)

        annotations: list[tuple[str, str]] = []

        if self.language:
            annotations.append(("lang", self.language))

        if self.voice:
            annotations.extend(self._voice_to_ssmd_pairs(self.voice))

        if self.say_as:
            annotations.append(("as", self.say_as.interpret_as))
            if self.say_as.format:
                annotations.append(("format", self.say_as.format))
            if self.say_as.detail:
                annotations.append(("detail", self.say_as.detail))

        if self.substitution:
            annotations.append(("sub", self.substitution))

        if self.phoneme:
            annotations.append(("ph", self.phoneme.ph))
            annotations.append(("alphabet", self.phoneme.alphabet))

        if self.extension:
            annotations.append(("ext", self.extension))

        if self.prosody:
            annotations.extend(self._prosody_to_ssmd_pairs(self.prosody))

        if self.emphasis:
            if self.emphasis == "none":
                annotations.append(("emphasis", "none"))
            else:
                if self.emphasis is True or self.emphasis == "moderate":
                    text = f"*{text}*"
                elif self.emphasis == "strong":
                    text = f"**{text}**"
                elif self.emphasis == "reduced":
                    text = f"_{text}_"

        if annotations:
            annotation_str = self._format_annotation_pairs(annotations)
            return f"[{text}]{{{annotation_str}}}"

        return text

    def _format_annotation_pairs(self, pairs: list[tuple[str, str]]) -> str:
        """Format annotation key/value pairs."""
        return " ".join([format_ssmd_attr(key, value) for key, value in pairs])

    def _prosody_to_ssmd_pairs(self, prosody: ProsodyAttrs) -> list[tuple[str, str]]:
        """Convert prosody to annotation pairs."""
        pairs: list[tuple[str, str]] = []

        if prosody.volume:
            pairs.append(("volume", prosody.volume))

        if prosody.rate:
            pairs.append(("rate", prosody.rate))

        if prosody.pitch:
            pairs.append(("pitch", prosody.pitch))

        return pairs

    def _voice_to_ssmd_pairs(self, voice: VoiceAttrs) -> list[tuple[str, str]]:
        """Convert voice to annotation pairs."""
        pairs: list[tuple[str, str]] = []
        if voice.name:
            pairs.append(("voice", voice.name))
        if voice.language:
            pairs.append(("voice-lang", voice.language))
        if voice.gender:
            pairs.append(("gender", voice.gender))
        if voice.variant is not None:
            pairs.append(("variant", str(voice.variant)))
        return pairs

    def _audio_to_ssmd(self, audio: AudioAttrs) -> str:
        """Convert audio to SSMD format."""
        pairs: list[tuple[str, str]] = [("src", audio.src)]

        if audio.clip_begin or audio.clip_end:
            pairs.append(("clip", f"{audio.clip_begin or ''}-{audio.clip_end or ''}"))
        if audio.speed:
            pairs.append(("speed", audio.speed))
        if audio.repeat_count:
            pairs.append(("repeat", str(audio.repeat_count)))
        if audio.repeat_dur:
            pairs.append(("repeatDur", audio.repeat_dur))
        if audio.sound_level:
            pairs.append(("level", audio.sound_level))
        if audio.alt_text:
            pairs.append(("alt", audio.alt_text))

        annotation_str = self._format_annotation_pairs(pairs)
        return f"[{self.text}]{{{annotation_str}}}"

    def _break_to_ssmd(self, brk: BreakAttrs) -> str:
        """Convert break to SSMD format."""
        if brk.time:
            return f"...{brk.time}"
        elif brk.strength:
            return SSMD_BREAK_STRENGTH_MAP.get(brk.strength, "...s")
        return "...s"

    def to_text(self) -> str:
        """Convert segment to plain text.

        Returns:
            Plain text with all markup removed
        """
        if self.audio:
            return self.text  # Return description
        if self.substitution:
            return self.substitution  # Return the spoken alias
        return self.text

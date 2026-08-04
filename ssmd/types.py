"""Data types for SSMD.

This module defines the core data structures used throughout the SSMD library.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

SpacyModelSize = Literal["sm", "md", "lg", "trf"]
SPACY_MODEL_SIZES: tuple[SpacyModelSize, ...] = ("sm", "md", "lg", "trf")


@dataclass(frozen=True)
class SentenceDetectionConfig:
    """Configuration forwarded to the phrasplit sentence detector."""

    use_spacy: bool | None = None
    spacy_model: str | None = None
    model_size: SpacyModelSize | None = None

    def __post_init__(self) -> None:
        """Reject malformed sentence-detection values early and deterministically."""
        if self.use_spacy not in (None, True, False):
            raise ValueError("sentence_use_spacy must be true, false, or unset")
        if self.spacy_model is not None and (
            not isinstance(self.spacy_model, str) or not self.spacy_model.strip()
        ):
            raise ValueError("sentence_spacy_model must be a non-empty package string")
        if self.model_size is not None and self.model_size not in SPACY_MODEL_SIZES:
            allowed = ", ".join(SPACY_MODEL_SIZES)
            raise ValueError(f"sentence_model_size must be one of {allowed}")


@dataclass(frozen=True)
class SentenceDetectionDiagnostics:
    """Structured information about one sentence-detector backend selection."""

    selection_mode: str
    effective_language: str
    selected_model: str | None = None
    selected_model_size: SpacyModelSize | None = None


T = TypeVar("T")


class ParsedResult(list[T], Generic[T]):
    """List-compatible parser result carrying optional sentence diagnostics."""

    def __init__(
        self,
        values: Iterable[T] = (),
        *,
        diagnostics: SentenceDetectionDiagnostics | None = None,
    ) -> None:
        super().__init__(values)
        self.diagnostics = diagnostics


@dataclass
class VoiceAttrs:
    """Voice attributes for TTS voice selection.

    Attributes:
        name: Voice name (e.g., "Joanna", "en-US-Wavenet-A")
        language: BCP-47 language code (e.g., "en-US", "fr-FR")
        gender: Voice gender
        variant: Variant number for disambiguation
    """

    name: str | None = None
    language: str | None = None
    gender: Literal["male", "female", "neutral"] | None = None
    variant: int | None = None


@dataclass
class ProsodyAttrs:
    """Prosody attributes for volume, rate, and pitch control.

    Attributes:
        volume: Volume level ('silent', 'x-soft', 'soft', 'medium', 'loud',
                'x-loud', or relative like '+10dB')
        rate: Speech rate ('x-slow', 'slow', 'medium', 'fast', 'x-fast',
              or relative like '+20%')
        pitch: Pitch level ('x-low', 'low', 'medium', 'high', 'x-high',
               or relative like '-5%')
    """

    volume: str | None = None
    rate: str | None = None
    pitch: str | None = None


@dataclass
class DirectiveAttrs:
    """Directive attributes that apply to a <div> block.

    Attributes:
        voice: Voice attributes to apply (optional)
        language: Language code for <lang> wrapping
        prosody: Prosody attributes to apply
    """

    voice: VoiceAttrs | None = None
    language: str | None = None
    prosody: ProsodyAttrs | None = None


@dataclass
class BreakAttrs:
    """Break/pause attributes.

    Attributes:
        time: Time duration (e.g., '500ms', '2s')
        strength: Break strength ('none', 'x-weak', 'medium', 'strong', 'x-strong')
    """

    time: str | None = None
    strength: str | None = None


@dataclass
class SayAsAttrs:
    """Say-as attributes for text interpretation.

    Attributes:
        interpret_as: Interpretation type ('telephone', 'date', 'cardinal',
                      'ordinal', 'characters', 'expletive', etc.)
        format: Optional format string (e.g., 'dd.mm.yyyy' for dates)
        detail: Optional detail level (e.g., '2' for verbosity)
    """

    interpret_as: str
    format: str | None = None
    detail: str | None = None


@dataclass
class AudioAttrs:
    """Audio file attributes.

    Attributes:
        src: Audio file URL or path
        alt_text: Fallback text if audio cannot be played
        clip_begin: Start time for playback (e.g., "0s", "500ms")
        clip_end: End time for playback (e.g., "10s", "5000ms")
        speed: Playback speed as percentage (e.g., "150%", "80%")
        repeat_count: Number of times to repeat audio
        repeat_dur: Total duration for repetitions (e.g., "10s")
        sound_level: Volume adjustment in dB (e.g., "+6dB", "-3dB")
    """

    src: str
    alt_text: str | None = None
    clip_begin: str | None = None
    clip_end: str | None = None
    speed: str | None = None
    repeat_count: int | None = None
    repeat_dur: str | None = None
    sound_level: str | None = None


@dataclass
class PhonemeAttrs:
    """Phoneme pronunciation attributes.

    Attributes:
        ph: Phonetic pronunciation string
        alphabet: Phonetic alphabet (ipa or x-sampa)
    """

    ph: str
    alphabet: str = "ipa"


# Heading configuration type
HeadingEffect = tuple[str, str | dict[str, str]]  # e.g., ('emphasis', 'strong')
HeadingConfig = dict[int, list[HeadingEffect]]


# Default heading configurations
DEFAULT_HEADING_LEVELS: HeadingConfig = {
    1: [("pause_before", "300ms"), ("emphasis", "strong"), ("pause", "300ms")],
    2: [("pause_before", "75ms"), ("emphasis", "moderate"), ("pause", "75ms")],
    3: [("pause_before", "50ms"), ("pause", "50ms")],
}

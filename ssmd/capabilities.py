"""TTS capability definitions and presets.

This module defines which SSML features are supported by various TTS engines
and provides capability-based filtering for SSMD processing.
"""

import copy
import importlib.resources as resources
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ssmd  # noqa: F401 - keeps module-qualified doctest examples executable


@dataclass
class CapabilityProfile:
    name: str
    inline_tags: set[str] = field(default_factory=set)
    block_tags: set[str] = field(default_factory=set)
    attributes: dict[str, set[str]] = field(default_factory=dict)
    values: dict[str, set[str]] = field(default_factory=dict)


class TTSCapabilities:
    """Define TTS engine capabilities.

    This class allows you to specify which SSML features your TTS engine
    supports. Unsupported features will be automatically stripped to plain text.

    Example:
        >>> # Basic TTS with minimal support
        >>> caps = TTSCapabilities(
        ...     emphasis=False,
        ...     break_tags=True,
        ...     prosody=False
        ... )
        >>>
        >>> doc = ssmd.Document("Hello *world*!", capabilities=caps)
        >>> ssml = doc.to_ssml()
        >>> # Output: <speak><p>Hello world!</p></speak>
        >>> # (emphasis stripped because not supported)
    """

    def __init__(
        self,
        # Core features
        emphasis: bool = True,
        break_tags: bool = True,
        paragraph: bool = True,
        # Language & pronunciation
        language: bool = True,
        phoneme: bool = True,
        substitution: bool = True,
        # Prosody (volume, rate, pitch)
        prosody: bool = True,
        volume: bool = True,
        rate: bool = True,
        pitch: bool = True,
        # Advanced features
        say_as: bool = True,
        audio: bool = True,
        mark: bool = True,
        # Extensions (platform-specific)
        extensions: dict[str, bool] | None = None,
        # Sentence and heading support
        sentence_tags: bool = True,
        heading_emphasis: bool = True,
        # ssml-green raw capabilities
        ssml_green: dict[str, bool] | None = None,
        language_scopes: dict[str, bool] | None = None,
    ):
        """Initialize TTS capabilities.

        Args:
            emphasis: Support for <emphasis> tags
            break_tags: Support for <break> tags
            paragraph: Support for <p> tags
            language: Support for <lang> tags
            phoneme: Support for <phoneme> tags
            substitution: Support for <sub> tags
            prosody: Support for <prosody> tags (general)
            volume: Support for volume attribute
            rate: Support for rate attribute
            pitch: Support for pitch attribute
            say_as: Support for <say-as> tags
            audio: Support for <audio> tags
            mark: Support for <mark> tags
            extensions: Dict of extension names and their support
            sentence_tags: Support for <s> tags
            heading_emphasis: Support for heading emphasis
            ssml_green: Raw ssml-green capabilities map (flattened)
            language_scopes: Optional language scope support map
        """
        self.emphasis = emphasis
        self.break_tags = break_tags
        self.paragraph = paragraph
        self.language = language
        self.phoneme = phoneme
        self.substitution = substitution
        self.prosody = prosody
        self.volume = volume and prosody
        self.rate = rate and prosody
        self.pitch = pitch and prosody
        self.say_as = say_as
        self.audio = audio
        self.mark = mark
        self.extensions = extensions or {}
        self.sentence_tags = sentence_tags
        self.heading_emphasis = heading_emphasis
        self.ssml_green = ssml_green or {}
        self.language_scopes = language_scopes or {}

    def to_config(self) -> dict[str, Any]:
        """Convert capabilities to SSMD config.

        Returns:
            Configuration dict for SSMD converter
        """
        config: dict[str, Any] = {
            "skip": [],
            "capabilities": self,
        }

        # Skip processors for unsupported features
        if not self.emphasis:
            config["skip"].append("emphasis")
        if not self.break_tags:
            config["skip"].append("break")
        if not self.paragraph:
            config["skip"].append("paragraph")
        if not self.mark:
            config["skip"].append("mark")

        # Prosody is handled specially (selective attributes)
        if not self.prosody:
            config["skip"].append("prosody")

        # Headings handled by modifying heading_levels
        if not self.heading_emphasis:
            config["heading_levels"] = {}  # No heading processing

        return config

    def supports_extension(self, extension_name: str) -> bool:
        """Check if an extension is supported.

        Args:
            extension_name: Name of the extension

        Returns:
            True if supported
        """
        return self.extensions.get(extension_name, False)

    def supports_key(self, key: str, default: bool = True) -> bool:
        """Check raw ssml-green capability key.

        Args:
            key: ssml-green key to check
            default: Default if key is missing

        Returns:
            True if supported
        """
        return self.ssml_green.get(key, default)


# Preset capability definitions for common TTS engines
ESPEAK_CAPABILITIES = TTSCapabilities(
    emphasis=False,  # eSpeak doesn't support emphasis
    break_tags=True,
    paragraph=False,  # eSpeak treats paragraphs as plain text
    language=True,
    phoneme=True,  # eSpeak has good phoneme support
    substitution=False,
    prosody=True,
    volume=True,
    rate=True,
    pitch=True,
    say_as=True,
    audio=True,
    mark=True,
    sentence_tags=True,
    heading_emphasis=True,
)

PYTTSX3_CAPABILITIES = TTSCapabilities(
    emphasis=False,  # pyttsx3 has minimal SSML support
    break_tags=False,
    paragraph=False,
    language=False,  # Voice selection, not SSML
    phoneme=False,
    substitution=False,
    prosody=True,  # Via properties, not SSML
    volume=True,
    rate=True,
    pitch=False,
    say_as=False,
    audio=False,
    mark=False,
    sentence_tags=False,
    heading_emphasis=False,
)

GOOGLE_TTS_CAPABILITIES = TTSCapabilities(
    emphasis=True,
    break_tags=True,
    paragraph=True,
    language=True,
    phoneme=True,
    substitution=True,
    prosody=True,
    volume=True,
    rate=True,
    pitch=True,
    say_as=True,
    audio=True,
    mark=True,
    sentence_tags=True,
    heading_emphasis=True,
)

AMAZON_POLLY_CAPABILITIES = TTSCapabilities(
    emphasis=True,
    break_tags=True,
    paragraph=True,
    language=True,
    phoneme=True,
    substitution=True,
    prosody=True,
    volume=True,
    rate=True,
    pitch=True,
    say_as=True,
    audio=False,  # Limited audio support
    mark=True,
    extensions={"whisper": True, "drc": True},  # Amazon-specific
    sentence_tags=True,
    heading_emphasis=True,
)

AZURE_TTS_CAPABILITIES = TTSCapabilities(
    emphasis=True,
    break_tags=True,
    paragraph=True,
    language=True,
    phoneme=True,
    substitution=True,
    prosody=True,
    volume=True,
    rate=True,
    pitch=True,
    say_as=True,
    audio=True,
    mark=True,
    sentence_tags=True,
    heading_emphasis=True,
)

# Minimal fallback (plain text only)
MINIMAL_CAPABILITIES = TTSCapabilities(
    emphasis=False,
    break_tags=False,
    paragraph=False,
    language=False,
    phoneme=False,
    substitution=False,
    prosody=False,
    say_as=False,
    audio=False,
    mark=False,
    sentence_tags=False,
    heading_emphasis=False,
)

# Full SSML support (reference)
FULL_CAPABILITIES = TTSCapabilities()

SSMD_CORE_PROFILE = CapabilityProfile(
    name="ssmd-core",
    inline_tags={
        "emphasis",
        "break",
        "lang",
        "voice",
        "mark",
        "phoneme",
        "prosody",
        "say-as",
        "sub",
        "audio",
        "extension",
    },
    block_tags={
        "div",
        "heading",
        "paragraph",
    },
    attributes={
        "audio": {
            "src",
            "clip",
            "speed",
            "repeat",
            "repeatDur",
            "level",
            "alt",
        },
        "emphasis": {"level"},
        "lang": {"lang"},
        "phoneme": {"ph", "ipa", "sampa", "alphabet"},
        "prosody": {"volume", "rate", "pitch", "v", "r", "p"},
        "say-as": {"as", "format", "detail"},
        "sub": {"sub"},
        "voice": {"voice", "voice-lang", "gender", "variant"},
        "div": {
            "lang",
            "voice",
            "voice-lang",
            "gender",
            "variant",
            "volume",
            "rate",
            "pitch",
        },
        "heading": {"level"},
        "break": {"time", "strength"},
        "mark": {"name"},
        "extension": {"ext"},
    },
)

KOKORO_PROFILE = CapabilityProfile(
    name="kokoro",
    inline_tags={tag for tag in SSMD_CORE_PROFILE.inline_tags if tag != "extension"},
    block_tags=SSMD_CORE_PROFILE.block_tags.copy(),
    attributes={
        key: value.copy()
        for key, value in SSMD_CORE_PROFILE.attributes.items()
        if key != "extension"
    },
)


GOOGLE_SSML_PROFILE = CapabilityProfile(
    name="google-ssml",
    inline_tags=SSMD_CORE_PROFILE.inline_tags.copy(),
    block_tags=SSMD_CORE_PROFILE.block_tags.copy(),
    attributes={key: value.copy() for key, value in SSMD_CORE_PROFILE.attributes.items()},
)

PROFILES: dict[str, CapabilityProfile] = {
    "ssmd-core": SSMD_CORE_PROFILE,
    "kokoro": KOKORO_PROFILE,
    "google-ssml": GOOGLE_SSML_PROFILE,
}


def get_profile(name: str) -> CapabilityProfile:
    profile = PROFILES.get(name)
    if profile is None:
        available = ", ".join(sorted(PROFILES.keys()))
        raise ValueError(f"Unknown profile '{name}'. Available: {available}")
    return copy.deepcopy(profile)


def list_profiles() -> list[str]:
    return sorted(PROFILES.keys())


def _flatten_ssml_green(data: dict[str, Any]) -> dict[str, bool]:
    flat: dict[str, bool] = {}
    for section in data.values():
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            if isinstance(value, bool):
                flat[key] = value
    return flat


def _load_ssml_green_data(data: str) -> TTSCapabilities:
    flat = _flatten_ssml_green(json.loads(data))

    emphasis = flat.get("elements››level (optional)", True)
    if emphasis:
        level_values = [
            'attribute values››level="strong"',
            'attribute values››level="moderate" (default)',
            'attribute values››level="none"',
            'attribute values››level="reduced"',
        ]
        if any(k in flat for k in level_values) and not any(
            flat.get(k, False) for k in level_values
        ):
            emphasis = False

    break_tags = flat.get("elements››strength (optional)", True) or flat.get(
        "elements››time (optional)", True
    )

    phoneme = flat.get("elements››ph (required)", True)
    substitution = flat.get("elements››alias (required)", True)
    prosody = (
        flat.get("elements››rate (optional)", True)
        or flat.get("elements››pitch (optional)", True)
        or flat.get("elements››volume (optional)", True)
    )

    language_root = flat.get("elements››xml:lang (required)", True)
    language_sentence = flat.get("elements›~~(sentence)›xml:lang (optional)", True)
    language_paragraph = flat.get("elements› (paragraph)›xml:lang (optional)", True)
    language = language_root or language_sentence or language_paragraph

    say_as = flat.get("elements››interpret-as (required)", True)

    caps = TTSCapabilities(
        emphasis=emphasis,
        break_tags=break_tags,
        paragraph=True,
        language=language,
        phoneme=phoneme,
        substitution=substitution,
        prosody=prosody,
        volume=flat.get("elements››volume (optional)", True),
        rate=flat.get("elements››rate (optional)", True),
        pitch=flat.get("elements››pitch (optional)", True),
        say_as=say_as,
        ssml_green=flat,
        language_scopes={
            "root": language_root,
            "sentence": language_sentence,
            "paragraph": language_paragraph,
        },
    )
    return caps


def load_ssml_green_platform(path: str | Path) -> TTSCapabilities:
    return _load_ssml_green_data(Path(path).read_text(encoding="utf-8"))


# Preset lookup
PRESETS: dict[str, TTSCapabilities] = {
    "espeak": ESPEAK_CAPABILITIES,
    "pyttsx3": PYTTSX3_CAPABILITIES,
    "google": GOOGLE_TTS_CAPABILITIES,
    "polly": AMAZON_POLLY_CAPABILITIES,
    "amazon": AMAZON_POLLY_CAPABILITIES,
    "azure": AZURE_TTS_CAPABILITIES,
    "microsoft": AZURE_TTS_CAPABILITIES,
    "minimal": MINIMAL_CAPABILITIES,
    "full": FULL_CAPABILITIES,
}

SSML_GREEN_FILES = {
    "alexa": "amazon-alexa.json",
    "amazon": "amazon-polly.json",
    "polly": "amazon-polly.json",
    "google": "google-home.json",
    "ibm": "ibm-watson.json",
    "watson": "ibm-watson.json",
    "azure": "microsoft-azure.json",
    "microsoft": "microsoft-azure.json",
    "cortana": "microsoft-cortana.json",
}


def _load_ssml_green_preset(name: str) -> TTSCapabilities | None:
    file_name = SSML_GREEN_FILES.get(name)
    if not file_name:
        return None
    data_path = resources.files("ssmd").joinpath("data").joinpath(file_name)
    if not data_path.is_file():
        raise FileNotFoundError(f"Installed package data is missing: ssmd/data/{file_name}")
    return _load_ssml_green_data(data_path.read_text(encoding="utf-8"))


def get_preset(name: str) -> TTSCapabilities:
    """Get a preset capability configuration.

    Args:
        name: Preset name (espeak, pyttsx3, google, polly, azure, minimal, full)

    Returns:
        TTSCapabilities instance

    Raises:
        ValueError: If preset not found
    """
    preset_name = name.lower()
    ssml_green_caps = _load_ssml_green_preset(preset_name)
    if ssml_green_caps is not None:
        preset = PRESETS.get(preset_name)
        if preset and preset.extensions:
            ssml_green_caps.extensions = preset.extensions.copy()
        return ssml_green_caps

    if preset_name not in PRESETS:
        available = ", ".join(sorted(PRESETS.keys()))
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")

    return copy.deepcopy(PRESETS[preset_name])


def list_presets() -> list[str]:
    """Return the sorted names of available capability presets.

    Example:
        >>> ssmd.list_presets()
        ['amazon', 'azure', 'espeak', 'full', 'google', 'microsoft', 'minimal', 'polly', 'pyttsx3']
    """
    return sorted(PRESETS.keys())

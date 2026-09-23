"""YAML front matter parsing and serialization for SSMD documents."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

import yaml

from ssmd.ssml_conversions import (
    NATURAL_PITCH_MAP,
    NATURAL_RATE_MAP,
    PROSODY_PITCH_MAP,
    PROSODY_RATE_MAP,
    PROSODY_VOLUME_MAP,
    normalize_pitch_value,
    normalize_rate_value,
)
from ssmd.types import (
    LanguageDetectionHint,
    LanguageDetectionMode,
    ProsodyTransitionDefaults,
    VoiceDefaults,
    VoiceProsodyDefaults,
)

PORTABLE_09_KEYS = frozenset(
    {
        "ssmd_version",
        "title",
        "language",
        "voice_bindings",
        "voice_defaults",
        "pause_defaults",
        "prosody_transitions",
        "language_detection",
        "requires",
    }
)
LEGACY_08_KEYS = frozenset(
    {
        "ssmd_version",
        "title",
        "voice_bindings",
        "pause_defaults",
        "heading",
        "extensions",
        "language_detection",
        "voice_defaults",
        "prosody_transitions",
    }
)
FRONT_MATTER_KEYS = PORTABLE_09_KEYS | LEGACY_08_KEYS
_LANGUAGE_TAG_PATTERN = re.compile(
    r"(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}|[A-Za-z]{4}|[A-Za-z]{5,8})"
    r"(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|[0-9]{3}))?"
    r"(?:-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*"
    r"(?:-[0-9A-WY-Za-wy-z](?:-[A-Za-z0-9]{2,8})+)*"
    r"(?:-x(?:-[A-Za-z0-9]{1,8})+)?|x(?:-[A-Za-z0-9]{1,8})+",
    re.IGNORECASE,
)
_GRANDFATHERED_LANGUAGE_TAGS = frozenset(
    {
        "art-lojban",
        "cel-gaulish",
        "en-gb-oed",
        "i-ami",
        "i-bnn",
        "i-default",
        "i-enochian",
        "i-hak",
        "i-klingon",
        "i-lux",
        "i-mingo",
        "i-navajo",
        "i-pwn",
        "i-tao",
        "i-tay",
        "i-tsu",
        "no-bok",
        "no-nyn",
        "sgn-be-fr",
        "sgn-be-nl",
        "sgn-ch-de",
        "zh-guoyu",
        "zh-hakka",
        "zh-min",
        "zh-min-nan",
        "zh-xiang",
    }
)


@dataclass(frozen=True)
class FrontMatterIssue:
    """A stable front matter diagnostic."""

    code: str
    severity: str
    message: str
    line: int | None = None
    column: int | None = None

    field: str | None = None


class FrontMatterError(ValueError):
    """Raised when a present front matter block cannot be parsed safely."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "header.yaml_invalid",
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.line = line
        self.column = column


@dataclass(frozen=True)
class FrontMatter:
    """Parsed SSMD front matter and the body that follows it."""

    data: dict[str, Any]
    body: str
    present: bool
    source_end: int | None = None
    raw: str | None = None


def _line_error(mark: Any) -> tuple[int | None, int | None]:
    """Return the line and column from a PyYAML mark-like object."""
    if mark is None:
        return None, None
    return getattr(mark, "line", 0) + 1, getattr(mark, "column", 0) + 1


def parse_front_matter(text: str) -> FrontMatter:
    """Parse an SSMD front matter block from *text*.

    Only a line containing exactly ``---`` can open a block.  The matching
    closing delimiter may be ``---`` or ``...``.  Text without a front matter
    block is returned unchanged and never parsed as YAML.
    """
    if not text:
        return FrontMatter({}, text, False)

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return FrontMatter({}, text, False)

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") in {"---", "..."}:
            closing_index = index
            break

    if closing_index is None:
        raise FrontMatterError(
            "YAML front matter is missing a closing delimiter",
            code="header.yaml_invalid",
            line=1,
            column=1,
        )

    raw = "".join(lines[1:closing_index])
    body = "".join(lines[closing_index + 1 :]).lstrip("\r\n")
    source_end = sum(len(line) for line in lines[: closing_index + 1])

    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        error_line, error_column = _line_error(getattr(exc, "problem_mark", None))
        detail = getattr(exc, "problem", None) or str(exc)
        raise FrontMatterError(
            f"Invalid YAML front matter: {detail}",
            code="header.yaml_invalid",
            line=error_line,
            column=error_column,
        ) from exc

    if loaded is None:
        data: dict[str, Any] = {}
    elif not isinstance(loaded, dict):
        raise FrontMatterError(
            "YAML front matter root must be a mapping",
            code="header.root_not_mapping",
            line=1,
            column=1,
        )
    else:
        data = dict(loaded)

    return FrontMatter(data, body, True, source_end=source_end, raw=raw)


def language_detection_hint(
    header: Mapping[str, Any],
) -> LanguageDetectionHint | None:
    """Return a typed language-detection hint from a validated header."""
    value = header.get("language_detection")
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("language_detection must be a mapping")
    mode = cast(LanguageDetectionMode, value.get("mode"))
    languages = value.get("languages", ())
    if isinstance(languages, str):
        raise ValueError("language_detection languages must be a sequence")
    if not isinstance(languages, (list, tuple)):
        raise ValueError("language_detection languages must be a sequence")
    normalized_languages = cast(tuple[str, ...], tuple(languages))
    return LanguageDetectionHint(mode=mode, languages=normalized_languages)


def voice_defaults(header: Mapping[str, Any]) -> VoiceDefaults:
    """Return typed logical voice prosody defaults from a header."""
    raw = header.get("voice_defaults")
    if not isinstance(raw, Mapping):
        return {}
    result: VoiceDefaults = {}
    for voice, values in raw.items():
        if not isinstance(values, Mapping):
            continue
        result[str(voice)] = VoiceProsodyDefaults(
            volume=_optional_string(values.get("volume")),
            rate=_optional_string(values.get("rate")),
            pitch=_optional_string(values.get("pitch")),
        )
    return result


def prosody_transitions(header: Mapping[str, Any]) -> ProsodyTransitionDefaults | None:
    """Return typed transition hints from a valid header."""
    raw = header.get("prosody_transitions")
    if not isinstance(raw, Mapping):
        return None
    return ProsodyTransitionDefaults(
        enabled=raw.get("enabled", True),
        same_voice_only=raw.get("same_voice_only", True),
        rate=_normalized_duration(raw.get("rate")),
        pitch=_normalized_duration(raw.get("pitch")),
        volume=_normalized_duration(raw.get("volume")),
    )


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _normalized_duration(value: Any) -> str | None:
    if value is None:
        return None
    from ssmd.durations import parse_duration

    return parse_duration(value)


def _valid_prosody_value(field_name: str, value: str) -> bool:
    normalized = value.strip().lower()
    if field_name == "rate":
        return (
            normalize_rate_value(value) in NATURAL_RATE_MAP
            or normalized in PROSODY_RATE_MAP.values()
            or bool(re.fullmatch(r"[+-]?\d+(?:\.\d+)?%", normalized))
        )
    if field_name == "pitch":
        return (
            normalize_pitch_value(value) in NATURAL_PITCH_MAP
            or normalized in PROSODY_PITCH_MAP.values()
            or bool(re.fullmatch(r"[+-]?\d+(?:\.\d+)?%", normalized))
        )
    return (
        normalized in PROSODY_VOLUME_MAP.values()
        or normalized.isdigit()
        and normalized in PROSODY_VOLUME_MAP
        or bool(re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:%|db)", normalized))
    )


def _validate_voice_defaults(value: Any) -> list[FrontMatterIssue]:
    if not isinstance(value, Mapping):
        return [
            FrontMatterIssue(
                "header.voice_defaults_invalid",
                "error",
                "voice_defaults must be a mapping",
            )
        ]
    issues: list[FrontMatterIssue] = []
    for voice, defaults in value.items():
        if not isinstance(defaults, Mapping):
            issues.append(
                FrontMatterIssue(
                    "header.voice_default_invalid",
                    "error",
                    f"voice_defaults.{voice} must be a mapping",
                )
            )
            continue
        for key, raw_value in defaults.items():
            if key not in {"volume", "rate", "pitch"}:
                issues.append(
                    FrontMatterIssue(
                        "header.voice_default_unknown_key",
                        "warn",
                        f"Unknown voice default key for {voice}: {key}",
                    )
                )
            elif (
                not isinstance(raw_value, str)
                or not raw_value.strip()
                or not _valid_prosody_value(str(key), raw_value)
            ):
                issues.append(
                    FrontMatterIssue(
                        "header.voice_default_prosody_invalid",
                        "error",
                        f"voice_defaults.{voice}.{key} must be a valid prosody value",
                    )
                )
    return issues


def _validate_prosody_transitions(value: Any) -> list[FrontMatterIssue]:
    if not isinstance(value, Mapping):
        return [
            FrontMatterIssue(
                "header.prosody_transitions_invalid",
                "error",
                "prosody_transitions must be a mapping",
            )
        ]
    issues: list[FrontMatterIssue] = []
    for key in value:
        if key not in {"enabled", "same_voice_only", "rate", "pitch", "volume"}:
            issues.append(
                FrontMatterIssue(
                    "header.prosody_transition_unknown_key",
                    "warn",
                    f"Unknown prosody transition key: {key}",
                )
            )
    for key in ("enabled", "same_voice_only"):
        if key in value and not isinstance(value[key], bool):
            issues.append(
                FrontMatterIssue(
                    "header.prosody_transition_option_invalid",
                    "error",
                    f"prosody_transitions.{key} must be a boolean",
                )
            )
    from ssmd.durations import parse_duration

    for key in ("rate", "pitch", "volume"):
        if key in value:
            try:
                parse_duration(value[key])
            except (TypeError, ValueError) as exc:
                issues.append(
                    FrontMatterIssue(
                        "header.prosody_transition_duration_invalid",
                        "error",
                        f"prosody_transitions.{key}: {exc}",
                    )
                )
    return issues


def _uses_09_schema(data: Mapping[str, Any], dialect: Literal["auto", "0.8", "0.9"]) -> bool:
    if dialect == "0.9":
        return True
    if dialect == "0.8":
        return False
    return data.get("ssmd_version") not in (None, "0.8", 0.8)


def _valid_language_tag(value: Any) -> bool:
    return isinstance(value, str) and (
        value.casefold() in _GRANDFATHERED_LANGUAGE_TAGS
        or _LANGUAGE_TAG_PATTERN.fullmatch(value) is not None
    )


def _validate_requires(value: Any) -> list[FrontMatterIssue]:
    if not isinstance(value, Mapping):
        return [
            FrontMatterIssue(
                "header.requires_invalid",
                "error",
                "requires must be a mapping",
                field="requires",
            )
        ]

    issues = [
        FrontMatterIssue(
            "header.requires_unknown_key",
            "warn",
            f"Unknown requires key: {key}",
            field="requires",
        )
        for key in value
        if key != "extensions"
    ]
    extensions = value.get("extensions", [])
    if not isinstance(extensions, (list, tuple)) or any(
        not isinstance(extension, str)
        or re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+", extension) is None
        for extension in extensions
    ):
        issues.append(
            FrontMatterIssue(
                "header.requires_extensions_invalid",
                "error",
                "requires.extensions must be a sequence of namespaced identifiers",
                field="requires",
            )
        )
    return issues


def _validate_language_detection(value: Any, is_09: bool) -> list[FrontMatterIssue]:
    if not isinstance(value, Mapping):
        return [
            FrontMatterIssue(
                "header.language_detection_invalid",
                "error",
                "language_detection must be a mapping",
                field="language_detection",
            )
        ]

    issues: list[FrontMatterIssue] = []
    mode = value.get("mode")
    if mode not in ("off", "auto"):
        issues.append(
            FrontMatterIssue(
                "header.language_detection_mode_invalid",
                "error",
                "language_detection mode must be off or auto",
                field="language_detection",
            )
        )
    languages = value.get("languages")
    language_values = tuple(languages) if isinstance(languages, (list, tuple)) else ()
    valid_languages = bool(language_values) and all(
        _valid_language_tag(language) if is_09 else isinstance(language, str) and bool(language)
        for language in language_values
    )
    if languages is not None and not valid_languages:
        issues.append(
            FrontMatterIssue(
                "header.language_detection_languages_invalid",
                "error",
                "language_detection languages must be a non-empty sequence of valid tags",
                field="language_detection",
            )
        )
    if mode == "auto" and (not valid_languages or len(set(language_values)) < 2):
        issues.append(
            FrontMatterIssue(
                "header.language_detection_languages_invalid",
                "error",
                "auto language detection requires at least two distinct languages",
                field="language_detection",
            )
        )
    return issues


def validate_front_matter(
    data: Mapping[str, Any],
    *,
    dialect: Literal["auto", "0.8", "0.9"] = "auto",
) -> list[FrontMatterIssue]:
    """Validate front matter against the selected version's schema."""
    is_09 = _uses_09_schema(data, dialect)
    allowed_keys = PORTABLE_09_KEYS if is_09 else LEGACY_08_KEYS
    issues: list[FrontMatterIssue] = []

    for key in data:
        if key in allowed_keys or key == "extensions":
            continue
        if is_09 and key == "heading":
            issues.append(
                FrontMatterIssue(
                    "header.nonportable_key",
                    "error",
                    "heading belongs to trusted application configuration, not portable front matter",
                    field=key,
                )
            )
        else:
            issues.append(
                FrontMatterIssue(
                    "header.unknown_key",
                    "warn",
                    f"Unknown front matter key: {key}",
                    field=key,
                )
            )

    if "ssmd_version" in data:
        expected_version = "0.9" if is_09 else "0.8"
        if not isinstance(data["ssmd_version"], str) or data["ssmd_version"] != expected_version:
            issues.append(
                FrontMatterIssue(
                    "header.version_unsupported",
                    "error",
                    f"ssmd_version must be the string {expected_version!r} for this dialect",
                    field="ssmd_version",
                )
            )

    if is_09 and "language" in data and not _valid_language_tag(data["language"]):
        issues.append(
            FrontMatterIssue(
                "language.invalid_tag",
                "error",
                "language must be a valid BCP-47 tag",
                field="language",
            )
        )

    if is_09 and "requires" in data:
        issues.extend(_validate_requires(data["requires"]))
    if "title" in data and not isinstance(data["title"], str):
        issues.append(
            FrontMatterIssue(
                "header.title_invalid",
                "error",
                "title must be a string",
                field="title",
            )
        )

    if "voice_bindings" in data and not isinstance(data["voice_bindings"], Mapping):
        issues.append(
            FrontMatterIssue(
                "header.voice_bindings_invalid",
                "error",
                "voice_bindings must be a mapping",
                field="voice_bindings",
            )
        )
    if "pause_defaults" in data and not isinstance(data["pause_defaults"], Mapping):
        issues.append(
            FrontMatterIssue(
                "header.pause_defaults_invalid",
                "error",
                "pause_defaults must be a mapping",
                field="pause_defaults",
            )
        )

    if "voice_defaults" in data:
        issues.extend(_validate_voice_defaults(data["voice_defaults"]))

    if "prosody_transitions" in data:
        issues.extend(_validate_prosody_transitions(data["prosody_transitions"]))

    if "language_detection" in data:
        issues.extend(_validate_language_detection(data["language_detection"], is_09))

    if "extensions" in data:
        issues.append(
            FrontMatterIssue(
                "header.extension_template_unsafe",
                "error",
                "Portable SSMD front matter cannot define renderer extension handlers",
                field="extensions",
            )
        )
    return issues


def _ordered_header(data: Mapping[str, Any]) -> dict[str, Any]:
    """Order recognized generated keys after existing metadata."""
    recognized = (
        "title",
        "voice_bindings",
        "voice_defaults",
        "pause_defaults",
        "prosody_transitions",
        "heading",
        "extensions",
        "language_detection",
    )
    result: dict[str, Any] = {key: value for key, value in data.items() if key not in recognized}
    for key in recognized:
        if key in data:
            result[key] = data[key]
    return result


def serialize_front_matter(data: Mapping[str, Any], body: str) -> str:
    """Serialize a mapping and body with deterministic SSMD delimiters."""
    if not isinstance(data, Mapping):
        raise ValueError("front matter data must be a mapping")
    header = yaml.safe_dump(
        _ordered_header(data),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).rstrip("\n")
    clean_body = body.lstrip("\r\n")
    return f"---\n{header}\n---\n{clean_body}" if header else f"---\n---\n{clean_body}"


def _merge_defaults(explicit: Any, generated: Any) -> Any:
    """Merge explicit values over generated defaults recursively."""
    if isinstance(explicit, Mapping) and isinstance(generated, Mapping):
        merged = dict(generated)
        for key, value in explicit.items():
            merged[key] = _merge_defaults(value, merged[key]) if key in merged else value
        return merged
    return explicit


def merge_generated_header(
    existing: Mapping[str, Any],
    generated: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge generated defaults without replacing explicit document values."""
    merged = _merge_defaults(existing, generated)
    return _ordered_header(merged)


__all__ = [
    "FRONT_MATTER_KEYS",
    "FrontMatter",
    "FrontMatterError",
    "FrontMatterIssue",
    "merge_generated_header",
    "language_detection_hint",
    "voice_defaults",
    "prosody_transitions",
    "parse_front_matter",
    "serialize_front_matter",
    "validate_front_matter",
]

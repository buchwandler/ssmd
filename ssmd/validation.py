"""Semantic validation for normalized SSMD 0.9 attributes."""

from __future__ import annotations

import math
import re

from ssmd.durations import DURATION_PATTERN
from ssmd.frontmatter import _valid_language_tag, _valid_prosody_value
from ssmd.spans import Diagnostic
from ssmd.tokenizer import Token


def _diagnostic(
    code: str,
    message: str,
    source_range: tuple[int, int],
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity="error",
        message=message,
        source_start=source_range[0],
        source_end=source_range[1],
    )


def _positive_finite_real(value: str) -> bool:
    try:
        numeric_value = float(value)
    except ValueError:
        return False
    return math.isfinite(numeric_value) and numeric_value > 0


def _valid_audio_duration(value: str) -> bool:
    match = DURATION_PATTERN.fullmatch(value)
    return match is not None and math.isfinite(float(match.group("value")))


def _valid_audio_clip(value: str) -> bool:
    if "-" not in value:
        return False
    begin, end = value.split("-", 1)
    return bool(begin or end) and all(
        not endpoint or _valid_audio_duration(endpoint) for endpoint in (begin, end)
    )


def _valid_attribute_value(
    name: str, value: str, *, is_audio: bool = False
) -> tuple[str, str] | None:
    if name in {"lang", "language"} and not _valid_language_tag(value):
        return "language.invalid_tag", "Language values must be valid BCP-47 tags."
    if name == "gender" and value not in {"male", "female", "neutral"}:
        return "voice.invalid_gender", "Voice gender must be male, female, or neutral."
    if name == "age" and re.fullmatch(r"[0-9]+", value) is None:
        return "voice.invalid_age", "Voice age must be a non-negative integer."
    if name == "variant" and (re.fullmatch(r"[0-9]+", value) is None or not value.lstrip("0")):
        return "voice.invalid_variant", "Voice variant must be a positive integer."
    if name == "repeat" and not _positive_finite_real(value):
        return (
            "audio.invalid_repeat_count",
            "Audio repeat count must be a finite positive real number.",
        )
    if is_audio:
        if name == "src" and not value.strip():
            return "audio.src.empty", "Audio src must be a non-empty source string."
        if name == "clip" and not _valid_audio_clip(value):
            return "audio.clip.invalid", "Audio clip must use START-END with valid times."
        if name == "repeatdur" and not _valid_audio_duration(value):
            return "audio.repeatdur.invalid", "Audio repeatdur must use a valid time value."
        if name == "speed" and re.fullmatch(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)%", value) is None:
            return "audio.speed.invalid", "Audio speed must be a numeric percentage."
        if (
            name == "level"
            and re.fullmatch(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)dB", value, re.IGNORECASE) is None
        ):
            return "audio.level.invalid", "Audio level must be a numeric decibel value."
    if name in {"volume", "rate", "pitch"} and not _valid_prosody_value(name, value):
        return (
            f"prosody.invalid_{name}",
            f"Prosody {name} must use a supported named or numeric value.",
        )
    return None


def validate_token_semantics(tokens: tuple[Token, ...]) -> list[Diagnostic]:
    """Return source-ranged diagnostics for invalid normalized token attributes."""
    diagnostics: list[Diagnostic] = []
    for token in tokens:
        for name, value in token.attrs.items():
            problem = _valid_attribute_value(name, value, is_audio="src" in token.attrs)
            if problem is not None:
                source_range = token.attribute_ranges.get(
                    name, (token.source_start, token.source_end)
                )
                diagnostics.append(_diagnostic(*problem, source_range))
        diagnostics.extend(validate_token_semantics(token.children))
    return diagnostics

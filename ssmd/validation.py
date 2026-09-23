"""Semantic validation for normalized SSMD 0.9 attributes."""

from __future__ import annotations

import math
import re

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


def _valid_attribute_value(name: str, value: str) -> tuple[str, str] | None:
    if name in {"lang", "language"} and not _valid_language_tag(value):
        return "language.invalid_tag", "Language values must be valid BCP-47 tags."
    if name == "gender" and value not in {"male", "female", "neutral"}:
        return "voice.invalid_gender", "Voice gender must be male, female, or neutral."
    if name == "age" and re.fullmatch(r"[0-9]+", value) is None:
        return "voice.invalid_age", "Voice age must be a non-negative integer."
    if name == "variant" and (re.fullmatch(r"[0-9]+", value) is None or not value.lstrip("0")):
        return "voice.invalid_variant", "Voice variant must be a positive integer."
    if name == "repeat" and not _positive_finite_real(value):
        return "audio.invalid_repeat_count", "Audio repeat count must be a finite positive real number."
    if name in {"volume", "rate", "pitch"} and not _valid_prosody_value(name, value):
        return f"prosody.invalid_{name}", f"Prosody {name} must use a supported named or numeric value."
    return None


def validate_token_semantics(tokens: tuple[Token, ...]) -> list[Diagnostic]:
    """Return source-ranged diagnostics for invalid normalized token attributes."""
    diagnostics: list[Diagnostic] = []
    for token in tokens:
        for name, value in token.attrs.items():
            problem = _valid_attribute_value(name, value)
            if problem is not None:
                source_range = token.attribute_ranges.get(name, (token.source_start, token.source_end))
                diagnostics.append(_diagnostic(*problem, source_range))
        diagnostics.extend(validate_token_semantics(token.children))
    return diagnostics

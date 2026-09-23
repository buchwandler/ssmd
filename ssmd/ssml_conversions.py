"""Shared SSML/SSMD conversion tables."""

PROSODY_VOLUME_MAP = {
    "0": "silent",
    "1": "x-soft",
    "2": "soft",
    "3": "medium",
    "4": "loud",
    "5": "x-loud",
}

PROSODY_RATE_MAP = {
    "1": "x-slow",
    "2": "slow",
    "3": "medium",
    "4": "fast",
    "5": "x-fast",
}

PROSODY_PITCH_MAP = {
    "1": "x-low",
    "2": "low",
    "3": "medium",
    "4": "high",
    "5": "x-high",
}

NATURAL_RATE_MAP = {
    "very-slow": "65%",
    "slow": "80%",
    "moderate": "90%",
    "normal": "100%",
    "brisk": "110%",
    "fast": "125%",
    "very-fast": "150%",
}

NATURAL_PITCH_MAP = {
    "very-low": "-20%",
    "low": "-12%",
    "moderate-low": "-6%",
    "normal": "+0%",
    "moderate-high": "+6%",
    "high": "+12%",
    "very-high": "+20%",
}


def normalize_rate_value(value: str) -> str:
    """Normalize a semantic or legacy rate name to its canonical spelling."""
    stripped = value.strip().lower()
    return (
        stripped
        if stripped in NATURAL_RATE_MAP or stripped in PROSODY_RATE_MAP.values()
        else value.strip()
    )


def normalize_pitch_value(value: str) -> str:
    """Normalize a semantic or legacy pitch name to its canonical spelling."""
    stripped = value.strip().lower()
    return (
        stripped
        if stripped in NATURAL_PITCH_MAP or stripped in PROSODY_PITCH_MAP.values()
        else value.strip()
    )


SSMD_BREAK_STRENGTH_MAP = {
    "none": "...n",
    "x-weak": "...w",
    "weak": "...w",
    "medium": "...c",
    "strong": "...s",
    "x-strong": "...p",
}

SSML_BREAK_STRENGTH_MAP = {
    "none": "",
    "x-weak": ".",
    "weak": ".",
    "medium": "...",
    "strong": "...s",
    "x-strong": "...p",
}

SSMD_BREAK_MARKER_TO_STRENGTH = {
    "n": "none",
    "w": "x-weak",
    "c": "medium",
    "s": "strong",
    "p": "x-strong",
}

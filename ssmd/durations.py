"""Validation helpers for SSMD pause durations."""

from __future__ import annotations

import re

DURATION_PATTERN = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s)$")


def parse_duration(value: str | int | float) -> str:
    """Normalize a non-negative duration expressed in milliseconds or seconds."""
    if isinstance(value, bool):
        raise ValueError("duration must be a string such as 250ms or 1.5s")
    text = str(value).strip()
    match = DURATION_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError("duration must use NUMBERms or NUMBERs")
    number = float(match.group("value"))
    if number < 0:
        raise ValueError("duration cannot be negative")
    number_text = str(int(number)) if number.is_integer() else format(number, "g")
    return f"{number_text}{match.group('unit')}"


def duration_milliseconds(value: str | int | float) -> float:
    """Convert a validated duration to milliseconds for comparisons."""
    normalized = parse_duration(value)
    match = DURATION_PATTERN.fullmatch(normalized)
    assert match is not None
    number = float(match.group("value"))
    return number * (1000 if match.group("unit") == "s" else 1)


__all__ = ["DURATION_PATTERN", "duration_milliseconds", "parse_duration"]

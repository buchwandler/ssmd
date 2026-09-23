"""Tests for the natural seven-step prosody scale."""

import pytest

import ssmd


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("very-slow", "65%"),
        ("slow", "80%"),
        ("moderate", "90%"),
        ("normal", "100%"),
        ("brisk", "110%"),
        ("fast", "125%"),
        ("very-fast", "150%"),
    ],
)
def test_natural_rate_levels_compile_to_percentages(value, expected):
    result = ssmd.to_ssml(f'[text]{{rate="{value}"}}')
    assert f'rate="{expected}"' in result


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("very-low", "-20%"),
        ("low", "-12%"),
        ("moderate-low", "-6%"),
        ("normal", "+0%"),
        ("moderate-high", "+6%"),
        ("high", "+12%"),
        ("very-high", "+20%"),
    ],
)
def test_natural_pitch_levels_compile_to_percentages(value, expected):
    result = ssmd.to_ssml(f'[text]{{pitch="{value}"}}')
    assert f'pitch="{expected}"' in result


def test_explicit_numeric_prosody_remains_unchanged():
    result = ssmd.to_ssml('[text]{rate="87%" pitch="-3%"}')
    assert 'rate="87%"' in result
    assert 'pitch="-3%"' in result


def test_natural_names_are_preserved_in_canonical_ssmd():
    assert ssmd.Document('[text]{rate="brisk" pitch="moderate-high"}').to_ssmd() == (
        '[text]{rate="brisk" pitch="moderate-high"}'
    )

"""Tests for opaque audio sources and generic audio semantics."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

import ssmd

SFX_URI = "sfx:impact.knock?material=oak&count=3&force=0.7&seed=42"


def _document(body: str) -> str:
    return f'---\nssmd_version: "0.9"\n---\n{body}'


def test_audio_src_preserves_sfx_uri() -> None:
    source = _document(f'[three knocks]{{src="{SFX_URI}"}}')

    structure = ssmd.parse_structure(source)
    audio_annotation = next(
        span for span in structure.annotations if span.attrs.get("tag") == "audio"
    )
    canonical = ssmd.Document(source).to_ssmd()
    rendered = ssmd.Document(source).to_ssml(target="generic")
    audio_element = next(
        element for element in ET.fromstring(rendered).iter() if element.tag.endswith("audio")
    )

    assert audio_annotation.attrs["src"] == SFX_URI
    assert f'src="{SFX_URI}"' in canonical
    assert audio_element.attrib["src"] == SFX_URI


def test_unknown_audio_scheme_is_not_renderer_rejected() -> None:
    source_uri = "custom-media:thing?id=123"
    source = _document(f'[fallback]{{src="{source_uri}"}}')

    structure = ssmd.parse_structure(source)
    audio_annotation = next(
        span for span in structure.annotations if span.attrs.get("tag") == "audio"
    )
    rendered = ssmd.Document(source).to_ssml(target="generic")
    audio_element = next(
        element for element in ET.fromstring(rendered).iter() if element.tag.endswith("audio")
    )

    assert audio_annotation.attrs["src"] == source_uri
    assert audio_element.attrib["src"] == source_uri


def test_sfx_uri_with_generic_audio_controls() -> None:
    source = _document(
        f'[spoken fallback]{{src="{SFX_URI}" clip="100ms-800ms" speed="90%" '
        'repeat="2.5" repeatdur="3s" level="-3dB" desc="Three wooden knocks"}'
    )
    canonical = ssmd.Document(source).to_ssmd()

    structure = ssmd.parse_structure(source)
    annotation = next(span for span in structure.annotations if span.attrs.get("tag") == "audio")
    rendered = ssmd.Document(source).to_ssml(target="generic")
    audio_element = next(
        element for element in ET.fromstring(rendered).iter() if element.tag.endswith("audio")
    )
    description = next(element for element in audio_element if element.tag.endswith("desc"))

    assert annotation.attrs == {
        "src": SFX_URI,
        "clip": "100ms-800ms",
        "speed": "90%",
        "repeat": "2.5",
        "repeatdur": "3s",
        "level": "-3dB",
        "desc": "Three wooden knocks",
        "tag": "audio",
    }
    assert audio_element.attrib == {
        "src": SFX_URI,
        "clipBegin": "100ms",
        "clipEnd": "800ms",
        "speed": "90%",
        "repeatCount": "2.5",
        "repeatDur": "3s",
        "soundLevel": "-3dB",
    }
    assert all(
        f'{key}="{value}"' in canonical
        for key, value in {
            "src": SFX_URI,
            "clip": "100ms-800ms",
            "speed": "90%",
            "repeat": "2.5",
            "repeatdur": "3s",
            "level": "-3dB",
            "desc": "Three wooden knocks",
        }.items()
    )
    assert description.text == "Three wooden knocks"
    assert description.tail == "spoken fallback"


def test_audio_desc_is_metadata() -> None:
    source = _document('[knocks]{src="sfx:impact.knock?seed=42" desc="Three wooden knocks"}')
    rendered = ssmd.Document(source).to_ssml(target="generic")
    audio_element = next(
        element for element in ET.fromstring(rendered).iter() if element.tag.endswith("audio")
    )
    description = next(element for element in audio_element if element.tag.endswith("desc"))

    assert description.text == "Three wooden knocks"
    assert description.tail == "knocks"


@pytest.mark.parametrize(
    ("attributes", "diagnostic_code"),
    [
        ('src="   "', "audio.src.empty"),
        ('src="sound.wav" clip="bad-time-800ms"', "audio.clip.invalid"),
        ('src="sound.wav" repeatdur="soon"', "audio.repeatdur.invalid"),
        ('src="sound.wav" speed="fast"', "audio.speed.invalid"),
        ('src="sound.wav" level="loud"', "audio.level.invalid"),
        ('src="sound.wav" repeat="0"', "audio.invalid_repeat_count"),
        ('src="sound.wav" repeat="inf"', "audio.invalid_repeat_count"),
    ],
)
def test_invalid_generic_audio_values_have_audio_diagnostics(
    attributes: str, diagnostic_code: str
) -> None:
    result = ssmd.parse_structure(_document(f"[fallback]{{{attributes}}}"))

    assert diagnostic_code in {item.code for item in result.diagnostics}


def test_audio_repeat_decimal_preserved() -> None:
    source = _document('[effect]{src="sfx:impact.knock?seed=42" repeat="2.5"}')

    structure = ssmd.parse_structure(source)
    annotation = next(span for span in structure.annotations if span.attrs.get("tag") == "audio")
    rendered = ssmd.Document(source).to_ssml(target="generic")
    audio_element = next(
        element for element in ET.fromstring(rendered).iter() if element.tag.endswith("audio")
    )

    assert annotation.attrs["repeat"] == "2.5"
    assert audio_element.attrib["repeatCount"] == "2.5"


@pytest.mark.parametrize(
    ("dialect", "normalize"),
    [("0.9", True), ("0.9", False), ("0.8", True), ("0.8", False)],
)
def test_empty_media_annotation_survives(dialect: str, normalize: bool) -> None:
    source = 'Before. []{src="sfx:impact.knock?seed=42"} After.'
    result = ssmd.parse_structure(source, dialect=dialect, normalize=normalize)

    audio_annotations = [span for span in result.annotations if span.attrs.get("tag") == "audio"]

    assert "Before." in result.clean_text
    assert "After." in result.clean_text
    assert len(audio_annotations) == 1
    assert audio_annotations[0].char_start == audio_annotations[0].char_end
    assert audio_annotations[0].attrs["src"] == "sfx:impact.knock?seed=42"

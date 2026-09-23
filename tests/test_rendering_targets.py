"""Tests for explicit rendering targets and conversion-loss reporting."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

import ssmd
from ssmd.rendering import RenderError


def test_bcp47_language_tags_are_preserved() -> None:
    document = ssmd.Document(
        '---\nssmd_version: "0.9"\nlanguage: "sr-Latn"\n---\n[Bonjour]{lang="fr"}'
    )

    output = document.to_ssml()
    root = ET.fromstring(output)

    assert root.attrib["{http://www.w3.org/XML/1998/namespace}lang"] == "sr-Latn"
    lang = next(element for element in root.iter() if element.tag.endswith("lang"))
    assert lang.attrib["{http://www.w3.org/XML/1998/namespace}lang"] == "fr"
    assert "fr-FR" not in output


def test_ssml_11_requires_explicit_root_language() -> None:
    with pytest.raises(RenderError) as error:
        ssmd.Document("Hello").to_ssml(target="ssml-1.1")

    assert error.value.diagnostics[0].code == "render.language.required"


def test_provider_language_scopes_report_omitted_root_and_inline_language() -> None:
    capabilities = ssmd.TTSCapabilities(language_scopes={"root": False, "sentence": False})
    document = ssmd.Document(
        '---\nssmd_version: "0.9"\nlanguage: "en"\n---\n[Bonjour]{lang="fr"}',
        capabilities=capabilities,
    )

    output = document.to_ssml(target="provider", loss_policy="warn")

    assert "xml:lang" not in output
    assert "<lang" not in output
    assert (
        sum(item.code == "render.unsupported.language" for item in document.render_diagnostics) == 2
    )

    output = ssmd.Document("Hello").to_ssml(target="ssml-1.1", language="en")
    root = ET.fromstring(output)
    assert root.tag == "{http://www.w3.org/2001/10/synthesis}speak"
    assert root.attrib["version"] == "1.1"
    assert root.attrib["{http://www.w3.org/XML/1998/namespace}lang"] == "en"


def test_voice_features_map_to_ssml_voice_attributes_together() -> None:
    output = ssmd.Document(
        '[Hello]{voice="narrator" voice-name="Narrator A" voice-languages="en-GB" '
        'gender="female" age="32" variant="2"}'
    ).to_ssml(target="generic")

    assert (
        '<voice name="Narrator A" languages="en-GB" gender="female" age="32" variant="2">'
        "Hello</voice>"
    ) in output
    assert 'language="en-GB"' not in output


def test_audio_repeat_real_description_and_fallback_are_distinct() -> None:
    output = ssmd.Document(
        '[Fallback words]{src="audio.wav" repeat="2.5" desc="A short sound"}'
    ).to_ssml(target="generic")
    root = ET.fromstring(output)
    audio = next(element for element in root.iter() if element.tag.endswith("audio"))
    desc = next(element for element in audio if element.tag.endswith("desc"))

    assert audio.attrib["repeatCount"] == "2.5"
    assert desc.text == "A short sound"
    assert desc.tail == "Fallback words"


def test_audio_alt_is_diagnosed_in_compatibility_and_rejected_in_09() -> None:
    legacy = ssmd.Document('[Sound]{src="sound.wav" alt="Legacy fallback"}')
    legacy.to_ssml(target="generic")
    assert any(item.code == "render.audio.alt_legacy" for item in legacy.render_diagnostics)

    versioned = ssmd.Document(
        '---\nssmd_version: "0.9"\n---\n[Fallback words]{src="sound.wav" alt="Legacy fallback"}'
    )
    with pytest.raises(RenderError) as error:
        versioned.to_ssml()
    assert any(item.code == "syntax.legacy_attribute_alias" for item in error.value.diagnostics)


def test_provider_loss_policies_are_explicit() -> None:
    document = ssmd.Document("*Important*", capabilities="minimal")

    warned = document.to_ssml(target="provider", loss_policy="warn")
    assert "<emphasis" not in warned
    assert any(item.code == "render.unsupported.emphasis" for item in document.render_diagnostics)

    dropped = ssmd.Document("*Important*", capabilities="minimal")
    dropped.to_ssml(target="provider", loss_policy="drop")
    assert any(item.severity == "info" for item in dropped.render_diagnostics)

    with pytest.raises(RenderError) as error:
        ssmd.Document("*Important*", capabilities="minimal").to_ssml(
            target="provider", loss_policy="error"
        )
    assert error.value.diagnostics[0].code == "render.unsupported.emphasis"
    assert error.value.diagnostics[0].severity == "error"


def test_trusted_extension_registry_is_used_and_declared_namespaced() -> None:
    handler = ssmd.ExtensionHandler(
        lambda text: f"<custom:effect>{text}</custom:effect>",
        namespaces={"custom": "https://example.com/ssml"},
    )
    output = ssmd.Document(
        '[Hello]{ext="example:effect"}',
        config={"extensions": {"example:effect": handler}},
    ).to_ssml(target="generic")
    ET.fromstring(output)

    assert 'xmlns:custom="https://example.com/ssml"' in output
    assert "<custom:effect>Hello</custom:effect>" in output


def test_multisentence_voice_scope_survives_ssml_roundtrip() -> None:
    source = '<speak><voice name="Narrator"><s>Hello. </s><s>Goodbye.</s></voice></speak>'

    document = ssmd.Document.from_ssml(source)
    rendered = document.to_ssml()

    assert document.ssmd.startswith(':::{voice-name="Narrator"}')
    assert rendered.count("<voice ") == 1
    assert "Hello." in rendered
    assert "Goodbye." in rendered


def test_versioned_multisentence_voice_scope_roundtrips() -> None:
    source = (
        '---\nssmd_version: "0.9"\n---\n'
        ':::{voice="moderator"}\n'
        "Sentence one. Sentence two. Sentence three.\n:::"
    )
    rendered = ssmd.Document(source).to_ssml()
    roundtripped = ssmd.Document.from_ssml(rendered).ssmd
    structure = ssmd.parse_structure(roundtripped, dialect="0.9")

    assert len(structure.annotations) == 1
    assert structure.annotations[0].char_start == 0
    assert structure.annotations[0].char_end == len(structure.clean_text)
    assert structure.annotations[0].attrs["voice-name"] == "moderator"

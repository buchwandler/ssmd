"""Demonstrate capability-aware rendering of strict SSMD 0.9 documents."""

from __future__ import annotations

from ssmd import Document, TTSCapabilities
from ssmd.parser import parse_structure

CONTENT = """\
---
ssmd_version: '0.9'
title: Capability Filtering Demo
---
# Welcome

Hello and **welcome** to SSMD! This is *very exciting* content.

Let's pause here ...500ms for effect. [Bonjour]{lang="fr"} everyone!

The number is [123]{as="cardinal"}. [Whispered text]{ext="whisper"} is an optional Polly extension.
"""


def demonstrate_capability_filtering() -> None:
    """Render the same strict source for several target capability presets."""
    print("SSMD 0.9 Capability Filtering Demo")
    print("\nSource document:")
    print(CONTENT)

    for name in ("minimal", "pyttsx3", "espeak", "google", "polly"):
        document = Document(CONTENT, capabilities=name, config={"dialect": "0.9"})
        rendered = document.to_ssml()
        print(f"\n{name} output:")
        print(rendered[:500])


def demonstrate_custom_capabilities() -> None:
    """Show filtering with a small custom SSML capability set."""
    capabilities = TTSCapabilities(
        emphasis=True,
        break_tags=True,
        paragraph=True,
        language=True,
        prosody=False,
        say_as=False,
        audio=False,
        mark=True,
        phoneme=False,
    )
    source = """\
---
ssmd_version: '0.9'
---
Hello **world**! Pause here ...500ms please. Say [bonjour]{lang="fr"} to everyone.
This phrase is *emphasized*. The number is [123]{as="cardinal"}. Place @marker here.
"""
    document = Document(source, capabilities=capabilities, config={"dialect": "0.9"})

    print("\nCustom capabilities support emphasis, breaks, language, and marks.")
    print(document.to_ssml())


def demonstrate_capability_aware_rendering() -> None:
    """Render one strict document for eSpeak without sentence-oriented APIs."""
    source = """\
---
ssmd_version: '0.9'
---
# Story Time

Once upon a time, there was a *brave* knight. He traveled ...300ms across distant lands.
[Bonjour]{lang="fr"} said the French wizard. This story is *very exciting*!
"""
    structure = parse_structure(source, dialect="0.9")
    document = Document(
        source,
        capabilities="espeak",
        config={"dialect": "0.9"},
    )

    print("\nCapability-aware eSpeak rendering:")
    print(f"Paragraph events: {sum(event.kind == 'paragraph' for event in structure.events)}")
    print(f"Clean text: {structure.clean_text}")
    print(document.to_ssml())


if __name__ == "__main__":
    demonstrate_capability_filtering()
    demonstrate_custom_capabilities()
    demonstrate_capability_aware_rendering()

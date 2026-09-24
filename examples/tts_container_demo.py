"""Use a strict SSMD 0.9 Document as a rendering container for TTS."""

from __future__ import annotations

import re
import time

from ssmd import Document
from ssmd.parser import parse_structure

CONTENT = """\
---
ssmd_version: '0.9'
title: Presentation Demo
---
# Welcome to SSMD

Hello and *welcome* to our presentation! Today we'll discuss some ...200ms exciting topics.

# What is SSMD?

SSMD stands for [S S M D]{sub="Speech Synthesis Markup Language"}. It's a ~~much easier~~ way to write TTS content.

# Features

Say [bonjour]{lang="fr"} to everyone. You can also add pauses ...500ms and phonetic annotations such as [tomato]{ph="təˈmeɪtoʊ"}.

# Conclusion

Thank you for listening @end and we hope you enjoyed the presentation.
"""


class MockTTSEngine:
    """Simulate an external TTS engine consuming rendered SSML."""

    def speak(self, ssml: str) -> None:
        """Print a text preview and simulate speech duration."""
        text = re.sub(r"<[^>]+>", "", ssml)
        print(f"Speaking: {text[:100]}...")
        time.sleep(len(text) * 0.005)

    def wait_until_done(self) -> None:
        """Represent the synchronization point used by a real playback engine."""


def main() -> None:
    """Inspect structure, render the document, and pass it to the mock engine."""
    structure = parse_structure(CONTENT, dialect="0.9")
    document = Document(CONTENT, config={"dialect": "0.9"}, strict=True)

    print("SSMD 0.9 Document Container Demo")
    print(f"Clean text characters: {len(structure.clean_text)}")
    print(f"Paragraph events: {sum(event.kind == 'paragraph' for event in structure.events)}")
    print("\nPlain text:")
    print(structure.clean_text)

    ssml = document.to_ssml()
    print("\nRendered SSML:")
    print(ssml)
    print("\nSubmitting rendered document to the mock TTS engine:")
    engine = MockTTSEngine()
    engine.speak(ssml)
    engine.wait_until_done()


if __name__ == "__main__":
    main()

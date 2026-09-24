"""Render and inspect a strict SSMD 0.9 story without sentence-level APIs."""

from __future__ import annotations

from ssmd import Document
from ssmd.parser import parse_structure

STORY = """\
---
ssmd_version: '0.9'
title: The Discovery
---
# Chapter 3: The Discovery

:::{voice="narrator" voice-languages="en-GB"}
[Emma]{lang="en-GB"} stepped into the dusty library ...800ms, her eyes adjusting to the dim light. **"This is it"** she whispered to herself.

The ancient book lay on the pedestal @book at the exact spot the [map]{sub="treasure map"} had indicated.

She approached slowly, her footsteps echoing in the silence. Each step seemed to say [creak]{ph="kriːk"}.
:::

# The Revelation

:::{voice="narrator" voice-languages="en-GB"}
As she opened the book ...1s, a brilliant *golden light* erupted from the pages! The text was in [Latin]{lang="la"}, but somehow she could understand it perfectly.

"By the power vested in these pages," the book seemed to say, "knowledge shall flow to those who seek it with a pure heart."

Emma felt a warmth spreading through her fingers. She knew @moment that her life would never be the same again ...2s.
:::
"""


def main() -> None:
    """Inspect the story structure and render the complete SSML document."""
    structure = parse_structure(STORY, dialect="0.9")
    document = Document(STORY, config={"dialect": "0.9"}, strict=True)

    print("SSMD 0.9 Story Reader Demo")
    print(f"Clean text characters: {len(structure.clean_text)}")
    print(f"Paragraph events: {sum(event.kind == 'paragraph' for event in structure.events)}")
    print(f"Annotation spans: {len(structure.annotations)}")
    print("\nStory text:")
    print(structure.clean_text)
    print("\nRendered SSML:")
    print(document.to_ssml())

    if any(item.severity == "error" for item in structure.diagnostics):
        raise SystemExit("The story contains strict 0.9 syntax errors.")


if __name__ == "__main__":
    main()

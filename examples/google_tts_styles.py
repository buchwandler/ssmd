"""Demonstrate Google-style SSMD extensions with canonical 0.9 source."""

from __future__ import annotations

import ssmd

STYLES = ("cheerful", "calm", "empathetic", "firm", "lively", "serious")


def google_style_extension(style: str):
    """Create an extension handler that emits a Google TTS style element."""
    return lambda text: f'<google:style name="{style}">{text}</google:style>'


EXTENSIONS = {style: google_style_extension(style) for style in STYLES}

STYLE_EXAMPLES = """\
---
ssmd_version: '0.9'
title: Google TTS Style Examples
---
# Customer Service

[Welcome to our support line!]{ext="cheerful"}
[I understand this must be frustrating.]{ext="empathetic"}
[Let me help you resolve this issue.]{ext="calm"}

# News Broadcast

[Good evening, I'm your news anchor.]{ext="serious"}
[Today's top story is truly extraordinary!]{ext="lively"}

# Leadership Speech

[We need to take action now.]{ext="firm"}
[Together, we can make a difference!]{ext="cheerful"}
"""

MULTI_VOICE_EXAMPLE = """\
---
ssmd_version: '0.9'
title: Multi-voice Google TTS Example
---
:::{voice="en-US-Wavenet-F"}
[Hello! How can I help you today?]{ext="cheerful"}
:::
:::{voice="en-US-Wavenet-C"}
I'm having trouble with my order.
:::
:::{voice="en-US-Wavenet-F"}
[I completely understand your concern.]{ext="empathetic"}
Let me look into that for you right away.
:::
"""


def main() -> None:
    """Render 0.9 documents using explicitly registered provider extensions."""
    for title, source in (
        ("Speaking styles", STYLE_EXAMPLES),
        ("Styles with voice directives", MULTI_VOICE_EXAMPLE),
    ):
        print(f"\n{title}\n{'=' * 60}")
        print(source)
        print(ssmd.to_ssml(source, extensions=EXTENSIONS))

    print("\nUsage notes")
    print("1. Register provider style handlers before rendering extension annotations.")
    print('2. Use [text]{ext="style_name"} with a handler for that style.')
    print("3. Combine provider extensions with canonical voice directives.")
    print("4. Style availability depends on the selected Google Cloud voice.")
    print("5. A Google Cloud client is required only to synthesize the resulting SSML.")


if __name__ == "__main__":
    main()

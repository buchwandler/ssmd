# Examples

Use the strict SSMD 0.9 examples below for new documents. Complete documents declare
`ssmd_version: '0.9'`, use canonical long-form attributes and fenced `:::` directives
for block-aligned scopes. Runnable examples live in the
[examples directory on GitHub](https://github.com/buchwandler/ssmd/tree/main/examples).

## Canonical SSMD 0.9 document

Save complete documents with an `.ssmd.md` filename when an SSMD-specific suffix is
useful. This example covers front matter, paragraphs, emphasis, pauses, language, voice,
marks, and prosody:

```text
---
ssmd_version: '0.9'
title: Welcome
---
# Welcome

*Hello* and **welcome** to SSMD ...500ms.

[Bonjour]{lang="fr-FR"} tout le monde!

:::{voice="host" voice-languages="en-US"}
Welcome to the show.
:::
:::{voice="guest" voice-languages="en-US"}
Thanks for having me.
:::

:::{volume="loud" rate="fast" pitch="high"}
This passage is loud, fast, and high-pitched.
:::

I always wanted a @marker cat as a pet.
```

Adjacent fenced directives with no blank line between them belong to the same semantic
paragraph. Their clean text receives ordinary inline separation and no paragraph event.
A blank line between sibling directives creates a paragraph boundary; canonical
formatting preserves this distinction. A voice change does not by itself create a
paragraph pause.

Use inline voice annotations for genuinely short, mixed-flow spans:

```text
The host said [hello]{voice="host"}, then the guest replied.
```

## Parse strict 0.9 structure

`parse_structure()` is the sentence-neutral API for strict 0.9 documents. It returns
clean text, annotation ranges, structural events, front matter, and source-aware
diagnostics without running sentence detection:

```python
from pathlib import Path

from ssmd.parser import lint, parse_structure

source = Path("story.ssmd.md").read_text(encoding="utf-8")
structure = parse_structure(source, dialect="0.9")
issues = lint(source, dialect="0.9")

print(structure.clean_text)
print(structure.annotations)
print(structure.events)
print(structure.header)
print(issues)
```

Annotation ranges are half-open offsets into `clean_text`. Break, mark, heading, and
paragraph events use clean-text boundary positions. Paragraph events represent document
structure; they do not prescribe a pause duration. A downstream TTS pipeline may
normalize the clean text and then supply explicit sentence spans to rendering.

## Render for a TTS target

Use `Document` for complete-document rendering and capability adaptation. Do not use its
sentence/list APIs for strict 0.9 documents; those are compatibility APIs for legacy
input.

```python
from ssmd import Document

source = """\
---
ssmd_version: '0.9'
---
# Announcement

Hello *world*! [Bonjour]{lang="fr"} everyone ...300ms.
"""
document = Document(source, config={"dialect": "0.9"}, capabilities="espeak")
print(document.to_text())
print(document.to_ssml())
```

For runnable structural, story-rendering, capability, and provider-extension examples,
see:

- [`examples/parser_demo.py`](../examples/parser_demo.py)
- [`examples/tts_rich_parser_demo.py`](../examples/tts_rich_parser_demo.py)
- [`examples/story_reader_demo.py`](../examples/story_reader_demo.py)
- [`examples/tts_container_demo.py`](../examples/tts_container_demo.py)
- [`examples/tts_with_capabilities.py`](../examples/tts_with_capabilities.py)
- [`examples/google_tts_styles.py`](../examples/google_tts_styles.py)

Google style annotations require explicitly registered trusted extension handlers; they
are provider-specific, not part of the portable all-features example.

## Legacy 0.8 sentence-parser compatibility

The following snippet intentionally demonstrates an unversioned legacy 0.8 input and the
sentence-oriented compatibility API. It is not a strict 0.9 authoring example. New
documents should use fenced directives and `parse_structure()` instead.

```python
from ssmd import parse_sentences

legacy_script = """\
<div voice="host">
Welcome to the show.
</div>

<div voice="guest">
Thanks for having me.
</div>
"""

for sentence in parse_sentences(legacy_script):
    voice = sentence.voice.name if sentence.voice else "default"
    print(f"[{voice}] {''.join(segment.text for segment in sentence.segments)}")
```

For conversion of existing files, use the semantic migration command and review any
manual actions before replacing the source:

```bash
ssmd --json migrate legacy.ssmd --to 0.9 -o story-09.ssmd.md
```

See the [syntax reference](syntax.md), [parser API](parser.md), and [span API](spans.md)
for more detail.

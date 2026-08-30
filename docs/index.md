# SSMD - Speech Synthesis Markdown

**SSMD** (Speech Synthesis Markdown) is a lightweight Python library that provides a
human-friendly markdown-like syntax for creating SSML (Speech Synthesis Markup Language)
documents. It's designed to make TTS (Text-to-Speech) content more readable and
maintainable. See `SPECIFICATION.md` in the repo for the canonical syntax rules.

```{image} https://img.shields.io/pypi/v/ssmd
:alt: PyPI Version
:target: https://pypi.org/project/ssmd/
```

```{image} https://img.shields.io/pypi/pyversions/ssmd
:alt: Python Versions
```

```{image} https://codecov.io/gh/buchwandler/ssmd/graph/badge.svg?token=iCHXwbjAXG
:alt: Code Coverage
:target: https://codecov.io/gh/buchwandler/ssmd
```

## Features

✨ **Markdown-like syntax** - More intuitive than raw SSML

🎯 **Full SSML support** - All major SSML features covered

🔄 **Bidirectional** - Convert SSMD↔SSML or strip to plain text

📊 **Parser API** - Extract structured data for custom TTS pipelines

📝 **TTS streaming** - Iterate through sentences for real-time TTS

🎛️ **TTS capabilities** - Auto-filter features based on engine support

🎨 **Extensible** - Custom extensions for platform-specific features

🧪 **Type-safe** - Full mypy type checking support

## Structure-only downstream parsing

For downstream TTS pipelines that own written-to-spoken normalization and sentence
segmentation, use `ssmd.parse_structure()` to obtain clean text, annotation ranges,
zero-width break/mark/paragraph events, and YAML front matter without invoking sentence
detection:

```text
SSMD parse_structure()
    -> caller-owned text normalization
    -> caller-owned sentence segmentation
    -> caller-owned TTS/G2P
```

Annotations refer to ranges in `clean_text`; structural event positions refer to
boundaries in that text. SSMD removes its markup and preserves metadata, but does not
perform general written-to-spoken language normalization.

## Quick Example

```python
import ssmd

# Convert SSMD to SSML
ssml = ssmd.to_ssml("Hello *world*!")
# → <speak>Hello <emphasis>world</emphasis>!</speak>

# Convert SSML back to SSMD
ssmd_text = ssmd.from_ssml('<speak><emphasis>Hello</emphasis></speak>')
# → *Hello*

# Strip markup for plain text
plain = ssmd.to_text("Hello *world* @marker!")
# → Hello world!

# Or use the Parser API for structured data
from ssmd import parse_paragraphs

for paragraph in parse_paragraphs("Hello *world*!"):
    for sentence in paragraph.sentences:
        for seg in sentence.segments:
            print(f"Text: {seg.text}, Emphasis: {seg.emphasis}")
```

## Table of Contents

```{toctree}
:caption: User Guide
:maxdepth: 2

installation
quickstart
cli
syntax
capabilities
spans
parser
ssml_conversion
examples
changelog
```

```{toctree}
:caption: API Reference
:maxdepth: 2

api
```

# Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`

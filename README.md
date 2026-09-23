[![PyPI - Version](https://img.shields.io/pypi/v/ssmd)](https://pypi.org/project/ssmd/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ssmd)
![PyPI - Downloads](https://img.shields.io/pypi/dm/ssmd)
[![codecov](https://codecov.io/gh/buchwandler/ssmd/graph/badge.svg?token=lLTHC8zKO3)](https://codecov.io/gh/buchwandler/ssmd)

# SSMD - Speech Synthesis Markdown

**SSMD** (Speech Synthesis Markdown) is a lightweight Python library that provides a
human-friendly markdown-like syntax for creating SSML (Speech Synthesis Markup Language)
documents. It's designed to make TTS (Text-to-Speech) content more readable and
maintainable.

## Features

- **Canonical SSMD 0.9 syntax** for versioned, readable speech documents
- **Scoped SSML output** for generic, SSML 1.1, and provider-adapted targets
- **Bidirectional conversion** with unsupported conversion losses surfaced explicitly
- **Document APIs**, provider-aware capability adaptation, and trusted extensions

## SSMD 0.9 documents

New documents should declare their dialect and use canonical 0.9 syntax:

```ssmd
---
ssmd_version: "0.9"
---
# Episode title

:::{voice="moderator"}
Welcome to the show.
:::

:::{voice="guest"}
Thanks for having me.
:::

[Bonjour]{lang="fr"}
[important]{volume="loud" rate="fast" pitch="high"}
```

Raw `<div>` blocks, `voice-lang`, compact prosody aliases, and symbolic prosody forms are
legacy compatibility syntax. Use `ssmd migrate` to make an explicit, verified upgrade.
## Installation

```bash
pip install ssmd
```

SSMD includes intelligent sentence detection via **phrasplit**. Runtime dependencies
include `phrasplit` and `pyyaml` (for YAML front matter parsing); pass `use_spacy=False`
for the fast regex splitter or enable a spaCy model for higher accuracy.

### Optional: Enhanced Accuracy with spaCy

For best sentence detection accuracy, especially with complex or informal text, install
spaCy support:

```bash
pip install "ssmd[spacy]"

# Install language models for the languages you need
python -m spacy download en_core_web_sm  # English (small, ~30MB)
python -m spacy download en_core_web_md  # English (medium, better accuracy, ~100MB)
python -m spacy download en_core_web_lg  # English (large, best accuracy, ~500MB)
python -m spacy download fr_core_news_sm  # French
python -m spacy download de_core_news_sm  # German
python -m spacy download es_core_news_sm  # Spanish
# See https://spacy.io/models for all available models
```

**Performance comparison:**

| Mode                          | Speed       | Accuracy | Size    | Use Case                      |
| ----------------------------- | ----------- | -------- | ------- | ----------------------------- |
| **Regex (`use_spacy=False`)** | ~60x faster | ~85-90%  | 0 MB    | Simple text, speed-critical   |
| **spaCy small models**        | Baseline    | ~95%     | ~30 MB  | Balanced accuracy/performance |
| **spaCy large models**        | Slower      | ~98%+    | ~500 MB | Best accuracy, complex text   |
| **spaCy transformer**         | Slowest     | ~99%+    | ~1 GB   | Research, maximum quality     |

Without spaCy, SSMD uses fast regex-based sentence splitting that works great for
well-formatted text. With spaCy, you get ML-powered detection for complex cases like
abbreviations, URLs, and informal writing.

Or install from source:

```bash
git clone https://github.com/buchwandler/ssmd.git
cd ssmd
pip install -e .
```

## Quick Start

### Basic Usage
The canonical 0.9 example above is a standalone document. Short conversion strings below are body
fragments for brevity.

```python
import ssmd

# Convert SSMD to SSML
ssml = ssmd.to_ssml("Hello *world*!")
print(ssml)
# Output: <speak>Hello <emphasis>world</emphasis>!</speak>

# Strip SSMD markup for plain text
plain = ssmd.to_text("Hello *world* @marker!")
print(plain)
# Output: Hello world!

# Convert SSML back to SSMD
ssmd_text = ssmd.from_ssml('<speak><emphasis>Hello</emphasis></speak>')
print(ssmd_text)
# Output is a complete document beginning with an SSMD 0.9 version header:
# ---
# ssmd_version: '0.9'
# ---
# *Hello*
```

## Command Line Interface

```bash
# Validate SSMD syntax and profile compatibility
ssmd lint story.ssmd

# Validate with a target capability profile (kokoro, google-ssml, ...)
ssmd lint story.ssmd --profile kokoro

# CI: fail on warnings too
ssmd lint story.ssmd --fail-on-warn

# Machine-readable JSON output (preferred)
ssmd --json lint story.ssmd
ssmd --json profiles
ssmd --json voices list --provider kokoro
ssmd --json inspect story.ssmd --spans
# Atomically create a formatted, validated SSMD file
ssmd --json create draft.ssmd -o story.ssmd --fail-on-warn

# Convert SSMD to SSML
ssmd to-ssml story.ssmd -o story.ssml
ssmd to-ssml story.ssmd --target ssml-1.1 --language en  # strict target with root language

# Convert SSML to SSMD
ssmd from-ssml story.ssml -o story.ssmd

# General conversion (auto-detects input format from extension)
ssmd convert story.ssmd --to ssml -o story.ssml
ssmd convert story.ssml --from ssml --to ssmd -o story.ssmd
ssmd convert story.ssmd --to text -o story.txt

# Read from stdin
cat story.ssmd | ssmd convert - --from ssmd --to ssml

# Plain text with strict target-capability filtering
ssmd text story.ssmd --capabilities minimal

# Format SSMD in-place
ssmd fmt story.ssmd -w

# Check whether formatting would change (useful in CI)
ssmd fmt story.ssmd --check

# List supported lint profiles and capability presets
ssmd profiles
ssmd --json profiles

# Inspect parsed spans, sentences, or paragraphs
ssmd inspect story.ssmd --spans
ssmd inspect story.ssmd --sentences
```

### Authoring configuration and portable headers

SSMD parses YAML front matter by default. The exact `---` opening delimiter must be on
the first line, and the closing delimiter may be `---` or `...`. Header metadata is
portable document data; the local authoring config is separate and defaults to
`~/.config/ssmd/config.yaml` on Linux.

```bash
ssmd config init
ssmd voices add kokoro af_sarah --language en-US --gender female
ssmd voices bind kokoro moderator af_sarah
ssmd config set authoring.default_voice_provider kokoro
ssmd config set pause_defaults.enabled true
ssmd config set pause_defaults.sentence 250ms

ssmd --json create draft.ssmd -o review.ssmd --voice-provider kokoro
ssmd --json lint review.ssmd --voice-provider kokoro --roundtrip --fail-on-warn
```

`create` materializes only the bindings used by the document and eligible
`pause_defaults`; `lint`, `inspect`, `text`, `to-ssml`, and `fmt` do not rewrite source
headers. Use `--config PATH` or `SSMD_CONFIG` to select a different authoring config and
`--no-yaml-header` only when leading `---` must be treated as literal content. Portable
`title` metadata is preserved in the header and excluded from plain text and SSML
speech. In JSON mode, treat `result.created` and the output path as mandatory success
checks in addition to the process exit code and top-level `ok`.

### Document API - Build TTS Content Incrementally

```python
from ssmd import Document

# Create a document and build it piece by piece
doc = Document()
doc.add_sentence("Hello and *welcome* to SSMD!")
doc.add_sentence("This is a great tool for TTS.")
doc.add_paragraph("Let's start a new paragraph here.")

# Export to different formats
ssml = doc.to_ssml()      # SSML output
markdown = doc.to_ssmd()  # SSMD markdown
text = doc.to_text()      # Plain text

# Access document content
print(doc.ssmd)           # Raw SSMD content
print(len(doc))           # Number of sentences
print(len(list(doc.paragraphs())))  # Number of paragraphs
```

### TTS Streaming Integration

Perfect for streaming TTS where you process sentences one at a time:

```python
from ssmd import Document

# Create document with configuration
doc = Document(
    config={'auto_sentence_tags': True},
    capabilities='pyttsx3'  # Auto-filter for pyttsx3 support
)

# Build the document
doc.add_paragraph("# Chapter 1: Introduction")
doc.add_sentence("Welcome to the *amazing* world of SSMD!")
doc.add_sentence("This makes TTS content much easier to write.")
doc.add_paragraph("# Chapter 2: Features")
doc.add_sentence("You can use all kinds of markup.")
doc.add_sentence("Including ...500ms pauses and [special pronunciations]{ph=\"speSl\"}.")

# Iterate through sentences for TTS
for i, sentence in enumerate(doc.sentences(), 1):
    print(f"Sentence {i}: {sentence}")
    # Your TTS engine here:
    # tts_engine.speak(sentence)
    # await tts_engine.wait_until_done()

# Or access specific sentences
sentence_count = len(list(doc.sentences()))
print(f"Total sentences: {sentence_count}")
print(f"Total paragraphs: {len(list(doc.paragraphs()))}")
print(f"First sentence: {doc[0]}")
print(f"Last sentence: {doc[-1]}")
```

### TTS pipeline integration: parse first, normalize second, segment third

Use `parse_spans()` when a downstream TTS orchestrator must normalize text before
calculating sentence boundaries:

```text
SSMD parse -> semantic preparation/normalization -> sentence splitting -> G2P
```

```python
parsed = ssmd.parse_spans(source)
prepared_text = normalize(parsed.clean_text, parsed.annotations)
sentence_spans = split_with_offsets(prepared_text)
ssml = ssmd.to_ssml(source, sentence_spans=sentence_spans)
```

SSMD owns structural markup, clean text, metadata, and offsets. It does not perform
number or abbreviation normalization, generic language detection, Spokenform
integration, or G2P. Remap annotation offsets after normalization and protect explicit
`ph` and `ipa` ranges. Automatic sentence detection remains available for standalone
conversion.

### Document Editing

```python
from ssmd import Document

# Load from existing content
doc = Document("First sentence. Second sentence. Third sentence.")

# Edit like a list
doc[0] = "Modified first sentence."
del doc[1]  # Remove second sentence

# String operations
doc.replace("sentence", "line")

# Merge documents
doc2 = Document("Additional content.")
doc.merge(doc2)

# Split into individual sentences
sentences = doc.split()  # Returns list of Document objects
```

### TTS Engine Capabilities

SSMD can automatically filter SSML features based on your TTS engine's capabilities.
This ensures compatibility by stripping unsupported tags to plain text.

#### Using Presets

```python
from ssmd import Document

# Use a preset for your TTS engine
doc = Document("*Hello* [world]{lang=\"en\"}!", capabilities='pyttsx3')
ssml = doc.to_ssml()

# pyttsx3 doesn't support emphasis or language tags, so they're stripped:
# <speak>Hello world!</speak>
```

**Available Presets:**

- `minimal` - Plain text only (no SSML)
- `pyttsx3` - Minimal support (basic prosody only)
- `espeak` - Moderate support (breaks, language, prosody, phonemes)
- `google` / `azure` / `microsoft` - Provider-specific capability adaptation; support varies by feature
- `polly` / `amazon` - Provider-specific features, including configured Amazon extensions
- `full` - Enable all features implemented by the SSMD renderer; this is not a claim of universal SSML support

#### Custom Capabilities

```python
from ssmd import Document, TTSCapabilities

# Define exactly what your TTS supports
caps = TTSCapabilities(
    emphasis=False,      # No <emphasis> support
    break_tags=True,     # Supports <break>
    paragraph=True,      # Supports <p>
    language=False,      # No language switching
    prosody=True,        # Supports volume/rate/pitch
    say_as=False,        # No <say-as>
    audio=False,         # No audio files
    mark=False,          # No markers
)

doc = Document("*Hello* world!", capabilities=caps)
```

#### Capability-Aware Streaming


Capability profiles do not adapt generic output automatically. Select the provider target and a
loss policy, then inspect diagnostics before sending each streamed sentence:

```python
from ssmd import Document

source = '''---
ssmd_version: "0.9"
---
# Welcome
*Hello* world!
[Bonjour]{lang="fr"} everyone!'''
doc = Document(source, capabilities="espeak")

for sentence_doc in doc.sentences(as_documents=True):
    ssml = sentence_doc.to_ssml(target="provider", loss_policy="warn")
    diagnostics = sentence_doc.render_diagnostics
    tts_engine.speak(ssml)
```

Provider presets describe SSMD renderer mappings, not universal service support. See
[`docs/capabilities.md`](docs/capabilities.md) for target and loss-policy guidance.

Built-in presets can produce different SSML for the same source. Select `target="provider"` and
an explicit loss policy, then inspect conversion diagnostics. Presets do not guarantee that a
specific endpoint or voice accepts every generated feature.

See [`docs/capabilities.md`](docs/capabilities.md) for supported preset details and examples.
## SSMD Syntax Reference

New documents should declare `ssmd_version: "0.9"` and use the canonical forms below. The
`ssmd_version` front-matter field selects strict 0.9 parsing; migration is the explicit
way to upgrade legacy input.

### Document structure and front matter

```yaml
---
ssmd_version: "0.9"
title: Review podcast
---
```

Front matter is metadata and is not spoken. `title`, voice bindings, pause defaults,
language-detection hints, and voice defaults are validated portable metadata. Local provider
inventories and executable extension handlers belong in trusted user configuration, not the
document header.

### Text, emphasis, paragraphs, and breaks

```ssmd
Ordinary text uses Markdown-style paragraphs.

*moderate emphasis*, **strong emphasis**, and ~~reduced emphasis~~.
A bare ... is literal ellipsis; use ...500ms, ...2s, ...w, ...c, ...s, or ...p for a break.

@chapter
```

Blank lines separate paragraphs. Headings use `#` through `######`. Escape SSMD metacharacters
when they should be spoken literally.

### Annotations and language

Annotations use `[text]{key="value"}`. Attribute values are quoted, and canonical output
uses double quotes with deterministic attribute ordering.

```ssmd
[Bonjour]{lang="fr"}
[File]{lang="en" scope="pronunciation"}
[H2O]{sub="water"}
[123]{as="cardinal"}
[tomato]{ipa="təˈmeɪtoʊ"}
```

`lang` is a BCP-47 language tag. The default `scope` is `semantic`; use
`scope="pronunciation"` only when language metadata should affect pronunciation processing
without changing semantic language context.

### Voice selection

`voice` identifies a logical or concrete voice. Feature-based selectors use the canonical
`voice-name`, `voice-languages`, `gender`, `age`, and `variant` attributes:

```ssmd
[Hello]{voice="host"}
[Bonjour]{voice-languages="fr-FR" gender="female"}
[Hello]{voice-name="en-US-Wavenet-A" voice-languages="en-US"}

:::{voice="host"}
A sustained passage spoken by the host.
:::
```

Use front-matter `voice_bindings` to map logical references to provider voices. For dialogue,
fenced directive blocks keep each speaker's scope visible. Raw `<div>` blocks are legacy
compatibility syntax, not canonical 0.9.

### Prosody

Use explicit named or numeric values for `volume`, `rate`, and `pitch`:

```ssmd
[loud]{volume="loud"}
[fast]{rate="fast"}
[high]{pitch="high"}
[urgent]{volume="x-loud" rate="fast" pitch="high"}
```

Relative numeric values such as `rate="+20%"` are supported. Compact `vrp`, short
`v`/`r`/`p` aliases, punctuation shorthand, and symbolic delimiters are compatibility forms
and MUST NOT be used for new 0.9 documents.

### Audio and extensions

Audio annotations use `src`; `desc` carries description metadata, while annotation content
is spoken fallback text:

```ssmd
[doorbell]{src="https://example.com/bell.mp3" desc="Doorbell"}
[Play this if audio fails]{src="bell.mp3"}
[jingle]{src="ad.mp3" repeat="3"}
```

Extension annotations are interpreted only by configured trusted handlers. Portable document
front matter cannot contain executable extension templates. Provider-specific output and
extension support depend on the selected target and registered handlers.

### Legacy input and migration

Unversioned documents retain legacy compatibility behavior; explicit `ssmd_version: "0.8"`
selects the same legacy dialect. Examples such as raw `<div>`, `voice-lang`, `_reduced_`,
`vrp`, and symbolic prosody are not canonical 0.9. Run `ssmd migrate FILE --to 0.9` to
request a semantic-equivalence-checked conversion. Review manual actions when the tool cannot
prove that the source can be represented safely.

```bash
ssmd --json migrate legacy.ssmd --to 0.9
```

## Parser API - Extract Structured Data

## Legacy sentence parser APIs
These compatibility sentence and span helpers use the legacy parser. For strict 0.9 parsing,
use `parse_structure(..., dialect="0.9")` or `Document` with a declared `ssmd_version`.

### When to Use the Parser

- **Custom TTS integration** - Process SSMD features programmatically
- **Text transformations** - Handle say-as, substitution, and phoneme conversions
- **Multi-voice dialogue** - Build voice-specific processing pipelines
- **Feature extraction** - Analyze SSMD content without generating SSML

### Quick Example

```python
from ssmd import parse_paragraphs

script = """
<div voice="sarah">
Hello! Call [+1-555-0123]{as="telephone"} for info.
[H2O]{sub="water"} is important.
</div>

<div voice="michael">
Thanks *Sarah*!
</div>
"""

# Parse into structured paragraphs
paragraphs = parse_paragraphs(script)

for paragraph in paragraphs:
    for sentence in paragraph.sentences:
        # Get voice configuration
        voice_name = sentence.voice.name if sentence.voice else "default"

        # Process each segment
        full_text = ""
        for seg in sentence.segments:
            # Handle text transformations
            if seg.say_as:
                # Your TTS engine converts based on interpret_as
                text = convert_say_as(seg.text, seg.say_as.interpret_as)
            elif seg.substitution:
                # Use substitution text instead of original
                text = seg.substitution
            elif seg.phoneme:
                # Use phoneme for pronunciation
                text = seg.text  # TTS engine handles phoneme
            else:
                text = seg.text

            full_text += text

        # Speak the complete sentence
        tts.speak(full_text, voice=voice_name)
```

### Parser Functions

#### `parse_paragraphs(text, **options)` → `list[Paragraph]`

Parse SSMD text into structured paragraphs with sentences and segments.

**Returns:** List of `Paragraph` objects.

**Example:**

```python
from ssmd import parse_paragraphs

paragraphs = parse_paragraphs("First sentence.\n\nSecond paragraph.")

for paragraph in paragraphs:
    for sentence in paragraph.sentences:
        print(sentence.text)
```

#### `parse_sentences(text, **options)` → `list[Sentence]`

Parse SSMD text into structured sentences with segments.

> **Note:** `SSMDSentence` is a backward-compatibility alias for `Sentence`.

**Parameters:**

- `text` (str): SSMD text to parse
- `sentence_detection` (bool): Split text into sentences (default: True)
- `include_default_voice` (bool): Include text before first voice directive (default:
  True)
- `capabilities` (TTSCapabilities | str): Filter features based on TTS engine support
- `language` (str): Language code for sentence detection (default: "en")
- `model_size` (str): Exact spaCy model tier - "sm", "md", "lg", or "trf" (unset by
  default)
- `spacy_model` (str): Exact spaCy package name; takes precedence over `model_size`
- `use_spacy` (bool): If False, use fast regex splitting instead of spaCy (default:
  True)

**Returns:** List of `Sentence` objects (alias: `SSMDSentence`). Each sentence includes
`paragraph_index` and `sentence_index` for document ordering.

**Example:**

```python
from ssmd import parse_sentences

# Automatic: phrasplit selects the highest installed compatible model for English
sentences = parse_sentences("Hello *world*! This is great.")

for sent in sentences:
    print(f"Voice: {sent.voice.name if sent.voice else 'default'}")
    print(f"Segments: {len(sent.segments)}")
    for seg in sent.segments:
        print(f"  - {seg.text!r} (emphasis={seg.emphasis})")

# Fast mode: no spaCy required (uses regex)
sentences = parse_sentences("Hello world. Fast mode.", use_spacy=False)

# High quality: use large spaCy model for better accuracy
sentences = parse_sentences("Complex text here.", model_size="lg")

# Exact package (preserved unchanged through the parser and Document APIs)
sentences = parse_sentences("Medical text.", spacy_model="en_core_web_lg")
```

**Sentence Detection Configuration:**

SSMD supports flexible sentence detection with quality/speed tradeoffs:

- **Fast mode** (`use_spacy=False`): Regex-based splitting, no dependencies, ~60x faster
- **Automatic selection** (default): phrasplit chooses the highest installed compatible
  model for the document language and falls back to regex when no usable model exists
- **Small models** (`model_size="sm"`): Best balance of speed and accuracy
- **Medium models** (`model_size="md"`): Better accuracy for complex text
- **Large models** (`model_size="lg"`): Best accuracy, slower
- **Transformer models** (`model_size="trf"`): Research-grade accuracy, slowest

When both `spacy_model` and `model_size` are supplied, the exact package wins and SSMD
emits a warning that the size is ignored. Parser results expose `result.diagnostics`
with `selection_mode`, `effective_language`, and `selected_model`.

The parser works out-of-the-box with fast regex mode. Install `ssmd[spacy]` and language
models for ML-powered accuracy.

**Installation note:** Larger spaCy models need manual installation:

```bash
# First install spaCy support
pip install "ssmd[spacy]"

# Then install models
python -m spacy download en_core_web_md
python -m spacy download fr_core_news_md

# Large models
python -m spacy download en_core_web_lg

# Transformer models
python -m spacy download en_core_web_trf
```

#### `parse_segments(text, **options)` → `list[Segment]`

Parse SSMD text into segments without sentence grouping.

> **Note:** `SSMDSegment` is a backward-compatibility alias for `Segment`.

**Parameters:**

- `text` (str): SSMD text to parse
- `capabilities` (TTSCapabilities | str): Filter features based on TTS engine support
- `voice_context` (VoiceAttrs | None): Voice context for the segments (optional)

**Returns:** List of `Segment` objects (alias: `SSMDSegment`)

**Example:**

```python
from ssmd import parse_segments

segments = parse_segments("Call [+1-555-0123]{as=\"telephone\"} now")

for seg in segments:
    if seg.say_as:
        print(f"Say-as: {seg.text!r} as {seg.say_as.interpret_as}")
```

#### `parse_voice_blocks(text)` → `list[tuple[VoiceAttrs | None, str]]`

Split text by voice directives.

**Returns:** List of (voice_attrs, text) tuples

**Example:**

```python
from ssmd import parse_voice_blocks

blocks = parse_voice_blocks("""
<div voice="sarah">
Hello from Sarah
</div>

<div voice="michael">
Hello from Michael
</div>
""")

for voice, text in blocks:
    print(f"{voice.name}: {text.strip()}")
```

### Data Structures

#### `Paragraph` (alias: `SSMDParagraph`)

Represents a paragraph containing sentences.

**Attributes:**

- `sentences` (list[Sentence]): List of sentences in the paragraph

#### `Sentence` (alias: `SSMDSentence`)

Represents a complete sentence with voice context.

**Attributes:**

- `segments` (list[Segment]): List of text segments
- `voice` (VoiceAttrs | None): Voice configuration
- `is_paragraph_end` (bool): Whether sentence ends a paragraph
- `paragraph_index` (int): Zero-based paragraph index for this sentence
- `sentence_index` (int): Zero-based sentence index within the document
- `breaks_after` (list[BreakAttrs]): Pauses after the sentence

#### `Segment` (alias: `SSMDSegment`)

Represents a text segment with metadata.

**Attributes:**

- `text` (str): The text content
- `emphasis` (bool | str): Emphasis level (True, "moderate", "strong", "reduced",
  "none")
- `prosody` (ProsodyAttrs | None): Volume, rate, pitch
- `language` (str | None): Language code (e.g., "fr-FR")
- `voice` (VoiceAttrs | None): Inline voice settings
- `say_as` (SayAsAttrs | None): Say-as interpretation
- `substitution` (str | None): Substitution text
- `phoneme` (PhonemeAttrs | None): Phonetic pronunciation (with `ph` and `alphabet`
  attributes)
- `audio` (AudioAttrs | None): Audio file info
- `extension` (str | None): Platform-specific extension name
- `breaks_before` (list[BreakAttrs]): Pauses before this segment
- `breaks_after` (list[BreakAttrs]): Pauses after this segment
- `marks_before` (list[str]): Marker names before this segment
- `marks_after` (list[str]): Marker names after this segment

#### `VoiceAttrs`

Voice configuration attributes.

**Attributes:**

- `name` (str | None): Voice name (e.g., "sarah", "en-US-Wavenet-A")
- `language` (str | None): Language code (e.g., "en-US")
- `gender` (str | None): Gender ("male", "female", "neutral")
- `variant` (int | None): Voice variant number

#### `ProsodyAttrs`

Prosody (volume, rate, pitch) attributes.

**Attributes:**

- `volume` (str | None): Volume level (e.g., "x-loud", "+10dB")
- `rate` (str | None): Speech rate (e.g., "fast", "120%")
- `pitch` (str | None): Pitch level (e.g., "high", "+20%")

#### `BreakAttrs`

Pause/break attributes.

**Attributes:**

- `time` (str | None): Break duration (e.g., "500ms", "2s")
- `strength` (str | None): Break strength (e.g., "weak", "strong")

#### `SayAsAttrs`

Say-as interpretation attributes.

**Attributes:**

- `interpret_as` (str): Interpretation type (e.g., "telephone", "date")
- `format` (str | None): Format string (e.g., "mdy" for dates)
- `detail` (int | None): Verbosity level (1-2, platform-specific)

#### `AudioAttrs`

Audio file attributes.

**Attributes:**

- `src` (str): Audio file URL
- `alt_text` (str | None): Alternative text if audio fails
- `clip_begin` (str | None): Start time for audio clip (e.g., "5s")
- `clip_end` (str | None): End time for audio clip (e.g., "30s")
- `speed` (str | None): Playback speed (e.g., "150%")
- `repeat_count` (int | None): Number of times to repeat
- `repeat_dur` (str | None): Duration to repeat (e.g., "10s")
- `sound_level` (str | None): Volume adjustment (e.g., "+6dB", "-3dB")

#### `parse_spans(text, **options)` → `ParseSpansResult`

Parse SSMD text into clean text with annotation spans. This is the recommended API for
downstream integration when you need reliable character offsets for text processing.

**Parameters:**

- `text` (str): SSMD text to parse
- `normalize` (bool): Normalize whitespace between segments (default: True)
- `default_lang` (str | None): Optional language to apply to the entire output

**Returns:** `ParseSpansResult` with the following attributes:

- `clean_text` (str): Rendered text with all markup removed
- `annotations` (list[AnnotationSpan]): List of annotation spans
- `warnings` (list[str]): Parse warnings (if any)

**AnnotationSpan attributes:**

- `char_start` (int): Start offset in clean_text (0-based, inclusive)
- `char_end` (int): End offset in clean_text (0-based, exclusive)
- `attrs` (dict[str, str]): Annotation attributes (e.g.,
  `{"lang": "fr", "tag": "lang"}`)
- `kind` (str | None): Annotation kind (e.g., "inline", "div", "language")

**Offset Convention:**

All offsets are **0-based, half-open intervals** `[start, end)` referring to
`clean_text`. This means `clean_text[span.char_start:span.char_end]` extracts the exact
text for the span.

**Example:**

```python
from ssmd import parse_spans

# Basic usage
result = parse_spans("Hello [world]{lang='fr'}!")
print(result.clean_text)  # "Hello world!"
print(result.annotations[0].attrs)  # {"lang": "fr", "tag": "lang"}

# Verify offset invariants
span = result.annotations[0]
text = result.clean_text[span.char_start:span.char_end]
print(text)  # "world"

# Multiple attributes with mixed quotes
result = parse_spans('[this]{lang="en" ph=\'ðɪs\' rate="0.9"}')
print(result.clean_text)  # "this"
print(result.annotations[0].attrs)
# {"lang": "en", "ph": "ðɪs", "rate": "0.9", "tag": "phoneme"}

# Div blocks
result = parse_spans("""
<div lang=fr>
Bonjour le monde
</div>
""")
print(result.clean_text)  # "Bonjour le monde"
div_span = next(s for s in result.annotations if s.kind == 'div')
print(div_span.attrs)  # {"lang": "fr", "tag": "div"}

# Preserve input whitespace
result = parse_spans("Wait,[what]{ipa=\"wʌt\"}?!", normalize=False)
print(result.clean_text)  # "Wait,what?!"
```

**Supported Grammar:**

- **Inline annotations:** `[text]{key="value"}` or `[text]{key='value'}`
- **Multiple attributes:** `[text]{key1="val1" key2='val2'}`
- **Unquoted values:** `<div lang=fr>...</div>` (simple tokens only)
- **Escaping:** `{text="hello \"world\""}` (backslash escapes within quotes)

**Warning Policy:**

`parse_spans` prefers warnings over exceptions for user-input parse problems:

- `UNTERMINATED_ANNOTATION` - Unbalanced brackets or braces
- `ATTR_PARSE_FAILED` - Malformed attribute syntax
- `UNTERMINATED_DIV` - Unclosed `<div>` blocks
- `UNEXPECTED_DIV_CLOSE` - `</div>` without matching `<div>`
- `UNSUPPORTED_NESTING` - Nested markup not supported in current context

Warnings are returned in `result.warnings` and do not raise exceptions. Only programmer
errors (e.g., internal invariants broken) raise exceptions.

### Complete Example

See `examples/parser_demo.py` for a comprehensive demonstration of all parser features:

```bash
python examples/parser_demo.py
```

The demo shows:

- Basic segment parsing
- Text transformations (say-as, substitution, phoneme)
- Voice block handling
- Complete TTS workflow with sentence assembly
- Prosody and language annotations
- Advanced sentence parsing options
- Mock TTS integration

## API Reference

### Module Functions

#### `ssmd.to_ssml(ssmd_text, **config)` → `str`

Convert SSMD markup to SSML.

**Parameters:**

- `ssmd_text` (str): SSMD markdown text
- `**config`: Optional configuration parameters

**Returns:** SSML string

#### `ssmd.to_text(ssmd_text, **config)` → `str`

Convert SSMD to plain text (strips all markup).

**Parameters:**

- `ssmd_text` (str): SSMD markdown text
- `**config`: Optional configuration parameters

**Returns:** Plain text string

#### `ssmd.from_ssml(ssml_text, *, capabilities=None, complete_document=True, **config)` → `str`

Convert SSML to SSMD 0.9. By default, the result is a complete versioned document; pass
`complete_document=False` to return only the body fragment. Unrepresentable semantics raise
`SSMLConversionError` by default. Use `SSMLParser` and inspect its `diagnostics` property when
opting into warning or drop policies.

**Parameters:**

- `ssml_text` (str): SSML XML string
- `capabilities` (TTSCapabilities | str | None): Optional renderer capability profile
- `complete_document` (bool): Include the SSMD 0.9 version header (default: `True`)
- `**config`: Optional parser configuration, including `loss_policy`

**Returns:** Complete SSMD 0.9 document or body fragment

### Document Class

#### `Document(content="", config=None, capabilities=None)`

Main document container for building and managing TTS content.

**Parameters:**

- `content` (str): Optional initial SSMD content
- `config` (dict): Configuration options
- `capabilities` (TTSCapabilities | str): TTS capabilities preset or object

**Building Methods:**

- `add(text)` → Add text without separator (returns self for chaining)
- `add_sentence(text)` → Add text with `\n` separator
- `add_paragraph(text)` → Add text with `\n\n` separator

**Export Methods:**

- `to_ssml()` → Export to SSML string
- `to_ssmd()` → Export to SSMD string
- `to_text()` → Export to plain text

**Class Methods:**

- `Document.from_ssml(ssml, **config)` → Create from SSML
- `Document.from_text(text, **config)` → Create from text

**Properties:**

- `ssmd` → Raw SSMD content
- `config` → Configuration dict
- `capabilities` → TTS capabilities

**List-like Interface:**

- `len(doc)` → Number of sentences
- `doc[i]` → Get sentence by index (SSML)
- `doc[i] = text` → Replace sentence
- `del doc[i]` → Delete sentence
- `doc += text` → Append content

**Iteration:**

- `sentences()` → Iterator yielding SSML sentences
- `sentences(as_documents=True)` → Iterator yielding Document objects
- `paragraphs()` → Iterator yielding SSML paragraphs

**Editing Methods:**

- `insert(index, text, separator="")` → Insert text at index
- `remove(index)` → Remove sentence
- `clear()` → Remove all content
- `replace(old, new, count=-1)` → Replace text

**Advanced Methods:**

- `merge(other_doc, separator="\n\n")` → Merge another document
- `split()` → Split into sentence Documents
- `get_fragment(index)` → Get raw fragment by index

## Real-World TTS Example

```python
import asyncio
from ssmd import Document

# Your TTS engine (example with pyttsx3, kokoro-tts, etc.)
class TTSEngine:
    async def speak(self, ssml: str):
        """Speak SSML text."""
        # Implementation depends on your TTS engine
        pass

    async def wait_until_done(self):
        """Wait for speech to complete."""
        pass

async def read_document(content: str, tts: TTSEngine):
    """Read an SSMD document sentence by sentence."""
    doc = Document(content, config={'auto_sentence_tags': True})

    sentence_count = len(doc)
    print(f"Reading document with {sentence_count} sentences...")

    for i in range(sentence_count):
        sentence = doc[i]
        print(f"[{i+1}/{sentence_count}] Speaking...")
        await tts.speak(sentence)
        await tts.wait_until_done()

    print("Done!")

# Usage
document = """
# Welcome
Hello and *welcome* to our presentation!
Today we'll discuss some exciting topics.

# Topic 1
First ...500ms let's talk about SSMD.
It makes writing TTS content [much easier]{v="4" p="4"}!

# Conclusion
Thank you for listening @end_marker!
"""

# Run async
# await read_document(document, tts_engine)
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=ssmd --cov-report=html

# Run specific test file
pytest tests/test_basic.py -v
```

### Code Quality

```bash
# Format with ruff
ruff format ssmd/ tests/

# Lint
ruff check ssmd/ tests/

# Type check
mypy ssmd/
```

## Specification

This implementation follows the [SSMD Specification](SPECIFICATION.md) with additional
features inspired by the
[original Ruby SSMD specification](https://github.com/machisuji/ssmd/blob/master/SPECIFICATION.md).

### Implemented Features
- Canonical 0.9 text, paragraphs, headings, marks, timed/strength breaks, and moderate, strong, and reduced emphasis.
- Inline annotations for language, voice selection, pronunciation, say-as, substitution, prosody, and audio.
- Fenced `:::` directives for scoped voice, language, and prosody.
- Version-aware front matter and migration from legacy/unversioned input with semantic-equivalence checks.
- Generic SSML, SSML 1.1, and provider-adapted targets with explicit loss policies. Unsupported SSML elements are not silently claimed as fully supported.

## Semantic language vs pronunciation language

Inline `lang` annotations are semantic by default:

```ssmd
[Bonjour]{lang="fr"}
```

A pronunciation-only annotation uses an explicit scope:

```ssmd
[File]{lang="en" scope="pronunciation"}
[Manpower]{lang="en" scope="pronunciation"}diskussion
ge[cancel]{lang="en" scope="pronunciation"}t
[download]{lang="en" scope="pronunciation"}en
```

Consumers may use `scope="pronunciation"` to select a G2P frontend without changing text
normalization, voice, or acoustic-model context. SSMD exposes this metadata but does not
perform language detection or G2P. The span APIs preserve clean-text adjacency and exact
offsets for these sub-token examples.

Portable routing may be declared in front matter:

```yaml
language_detection:
  mode: auto
  languages: [de, en]
```

This is a consumer hint only. SSMD validates and exposes it; it does not infer language
spans or automatically detect languages.

## Related Projects

- **[SSMD (Ruby)](https://github.com/machisuji/ssmd)** - Original reference
  implementation
- **[SSMD (JavaScript)](https://github.com/fabien88/ssmd)** - JavaScript implementation
- **[Speech Markdown](https://www.speechmarkdown.org/)** - Alternative specification

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Original SSMD specification by [machisuji](https://github.com/machisuji)
- JavaScript implementation by [fabien88](https://github.com/fabien88)
- X-SAMPA to IPA conversion table from the Ruby implementation

## Links

- **Homepage:** https://github.com/buchwandler/ssmd
- **PyPI:** https://pypi.org/project/ssmd/
- **Issues:** https://github.com/buchwandler/ssmd/issues
- **Documentation:** https://ssmd.readthedocs.io/

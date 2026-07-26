[![PyPI - Version](https://img.shields.io/pypi/v/ssmd)](https://pypi.org/project/ssmd/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ssmd)
![PyPI - Downloads](https://img.shields.io/pypi/dm/ssmd)
[![codecov](https://codecov.io/gh/holgern/ssmd/graph/badge.svg?token=lLTHC8zKO3)](https://codecov.io/gh/holgern/ssmd)

# SSMD - Speech Synthesis Markdown

**SSMD** (Speech Synthesis Markdown) is a lightweight Python library that provides a
human-friendly markdown-like syntax for creating SSML (Speech Synthesis Markup Language)
documents. It's designed to make TTS (Text-to-Speech) content more readable and
maintainable.

## Features

✨ **Markdown-like syntax** - More intuitive than raw SSML 🎯 **Full SSML support** -
All major SSML features covered 🔄 **Bidirectional** - Convert SSMD↔SSML or strip to
plain text 📝 **Document-centric** - Build, edit, and export TTS documents 🎛️ **TTS
capabilities** - Auto-filter features based on engine support 🎨 **Extensible** - Custom
extensions for platform-specific features 🧪 **Spec-driven** - Follows the official SSMD
specification

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
git clone https://github.com/holgern/ssmd.git
cd ssmd
pip install -e .
```

## Quick Start

### Basic Usage

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
# Output: *Hello*
```

## Command Line Interface

```bash
# Validate SSMD syntax and profile compatibility
ssmd lint story.ssmd

# Validate with a target capability profile (kokoro, google-ssml, ...)
ssmd lint story.ssmd --profile kokoro

# CI: fail on warnings too
ssmd lint story.ssmd --fail-on-warn

# Machine-readable JSON output
ssmd lint story.ssmd --format json

# Atomically create a formatted, validated SSMD file
ssmd create draft.ssmd -o story.ssmd --fail-on-warn

# Convert SSMD to SSML
ssmd to-ssml story.ssmd -o story.ssml

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
ssmd profiles --json

# Inspect parsed spans, sentences, or paragraphs
ssmd inspect story.ssmd --spans
ssmd inspect story.ssmd --sentences
```

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
- `google` / `azure` / `microsoft` - Full SSML support
- `polly` / `amazon` - Full support + Amazon extensions (whisper, DRC)
- `full` - All features enabled

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

```python
from ssmd import Document

# Create document for specific TTS engine
doc = Document(capabilities='espeak')

# Build content with various features
doc.add_paragraph("# Welcome")
doc.add_sentence("*Hello* world!")
doc.add_sentence("[Bonjour]{lang=\"fr\"} everyone!")

# All sentences are filtered for eSpeak compatibility
for sentence in doc.sentences():
    # Features eSpeak doesn't support are automatically removed
    tts_engine.speak(sentence)
```

**Comparison of Engine Outputs:**

Same input: `*Hello* world... [this is loud]{v="5"}!`

| Engine  | Output                                                                                                                   |
| ------- | ------------------------------------------------------------------------------------------------------------------------ |
| minimal | `<speak>Hello world... this is loud!</speak>`                                                                            |
| pyttsx3 | `<speak>Hello world... <prosody volume="x-loud">this is loud</prosody>!</speak>`                                         |
| espeak  | `<speak>Hello world<break time="1000ms"/> <prosody volume="x-loud">this is loud</prosody>!</speak>`                      |
| google  | `<speak><emphasis>Hello</emphasis> world<break time="1000ms"/> <prosody volume="x-loud">this is loud</prosody>!</speak>` |

See `examples/tts_with_capabilities.py` for a complete demonstration.

## SSMD Syntax Reference

### Text & Emphasis

SSMD supports all four SSML emphasis levels:

```python
# Moderate emphasis (default)
ssmd.to_ssml("*emphasized text*")
# → <speak><emphasis>emphasized text</emphasis></speak>

# Strong emphasis
ssmd.to_ssml("**very important**")
# → <speak><emphasis level="strong">very important</emphasis></speak>

# Reduced emphasis (subtle)
ssmd.to_ssml("~~less important~~")
# → <speak><emphasis level="reduced">less important</emphasis></speak>

# No emphasis (explicit, rarely used)
ssmd.to_ssml("[monotone]{emphasis=\"none\"}")
# → <speak><emphasis level="none">monotone</emphasis></speak>
```

### Breaks & Pauses

```python
# Specific time (required - bare ... is preserved as ellipsis)
ssmd.to_ssml("Hello ...500ms world")
ssmd.to_ssml("Hello ...2s world")
ssmd.to_ssml("Hello ...1s world")

# Strength-based
ssmd.to_ssml("Hello ...n world")  # none
ssmd.to_ssml("Hello ...w world")  # weak (x-weak)
ssmd.to_ssml("Hello ...c world")  # comma (medium)
ssmd.to_ssml("Hello ...s world")  # sentence (strong)
ssmd.to_ssml("Hello ...p world")  # paragraph (x-strong)
```

### Paragraphs

```python
text = """First paragraph here.
Second line of first paragraph.

Second paragraph starts here."""

ssmd.to_ssml(text)
# → <speak>First paragraph here.
#    Second line of first paragraph.
#    Second paragraph starts here.</speak>
```

### Language

```python
# Auto-complete language codes
ssmd.to_ssml('[Bonjour]{lang="fr"} world')
# → <speak><lang xml:lang="fr-FR">Bonjour</lang> world</speak>

# Explicit locale
ssmd.to_ssml('[Cheerio]{lang="en-GB"}')
# → <speak><lang xml:lang="en-GB">Cheerio</lang></speak>
```

### Voice Selection

SSMD supports two ways to specify voices: **inline annotations** for short phrases and
**block directives** for longer passages (ideal for dialogue and scripts).

#### Inline Voice Annotations

Perfect for short voice changes within a sentence:

```python
# Simple voice name
ssmd.to_ssml('[Hello]{voice="Joanna"}')
# → <speak><voice name="Joanna">Hello</voice></speak>

# Cloud TTS voice name (e.g., Google Wavenet, AWS Polly)
ssmd.to_ssml('[Hello]{voice="en-US-Wavenet-A"}')
# → <speak><voice name="en-US-Wavenet-A">Hello</voice></speak>

# Language and gender
ssmd.to_ssml('[Bonjour]{voice-lang="fr-FR" gender="female"}')
# → <speak><voice language="fr-FR" gender="female">Bonjour</voice></speak>

# All attributes (language, gender, variant)
ssmd.to_ssml('[Text]{voice-lang="en-GB" gender="male" variant="1"}')
# → <speak><voice language="en-GB" gender="male" variant="1">Text</voice></speak>
```

#### Voice Directives (Block Syntax)

Perfect for dialogue, podcasts, and scripts with multiple speakers:

```python
script = """
<div voice="af_sarah">
Welcome to Tech Talk! I'm Sarah, and today we're diving into the fascinating
world of text-to-speech technology.
</div>
...s

<div voice="am_michael">
And I'm Michael! We've got an amazing episode lined up. The advances in neural
TTS have been incredible lately.
</div>
...s

<div voice="af_sarah">
So what are we covering today?
</div>
"""

ssmd.to_ssml(script)
# Each voice directive creates a separate voice block in SSML
```

**Voice directives support all voice attributes:**

```python
# Language and gender
multilingual = """
<div voice-lang="fr-FR" gender="female">
Bonjour! Comment allez-vous aujourd'hui?
</div>

<div voice-lang="en-GB" gender="male">
Hello there! Lovely weather we're having.
</div>

<div voice-lang="es-ES" gender="female" variant="1">
¡Hola! ¿Cómo estás?
</div>
"""
```

**Voice directive features:**

- Supports all attributes: language, gender, variant
- Applies to all text until the next directive or paragraph break
- Automatically detected on SSML→SSMD conversion for long voice blocks
- Much more readable than inline annotations for dialogue

**Mixing both styles:**

```python
# Block directive for main speaker, inline for interruptions
text = """
<div voice="sarah">
Hello everyone, [but wait!]{voice="michael"} Michael interrupts...
</div>

<div voice="michael">
Sorry, I had to jump in there!
</div>
"""
```

### Phonetic Pronunciation

```python
# X-SAMPA notation (converted to IPA automatically)
ssmd.to_ssml('[tomato]{sampa="t@meItoU"}')

# Direct IPA
ssmd.to_ssml('[tomato]{ipa="təˈmeɪtoʊ"}')

# Output: <speak><phoneme alphabet="ipa" ph="təˈmeɪtoʊ">tomato</phoneme></speak>
```

### Prosody (Volume, Rate, Pitch)

```python
# Combined (volume, rate, pitch)
ssmd.to_ssml('[loud and fast]{vrp="555"}')
# → <prosody volume="x-loud" rate="x-fast" pitch="x-high">loud and fast</prosody>

# Individual attributes
ssmd.to_ssml('[text]{v="5" r="3" p="1"}')
# → <prosody volume="x-loud" rate="medium" pitch="x-low">text</prosody>

# Relative values
ssmd.to_ssml('[louder]{v="+10dB"}')
ssmd.to_ssml('[higher]{p="+20%"}')
```

### Substitution (Aliases)

```python
ssmd.to_ssml('[H2O]{sub="water"}')
# → <speak><sub alias="water">H2O</sub></speak>

ssmd.to_ssml('[AWS]{sub="Amazon Web Services"}')
# → <speak><sub alias="Amazon Web Services">AWS</sub></speak>
```

### Say-As

```python
# Telephone numbers
ssmd.to_ssml('[+1-555-0123]{as="telephone"}')

# Dates with format
ssmd.to_ssml('[31.12.2024]{as="date" format="dd.mm.yyyy"}')

# Say-as with detail attribute (for verbosity control)
ssmd.to_ssml('[123]{as="cardinal" detail="2"}')
# → <speak><say-as interpret-as="cardinal" detail="2">123</say-as></speak>

ssmd.to_ssml('[12/31/2024]{as="date" format="mdy" detail="1"}')
# → <speak><say-as interpret-as="date" format="mdy" detail="1">12/31/2024</say-as></speak>

# Spell out
ssmd.to_ssml('[NASA]{as="character"}')

# Numbers
ssmd.to_ssml('[123]{as="cardinal"}')
ssmd.to_ssml('[1st]{as="ordinal"}')

# Expletives (beeped)
ssmd.to_ssml('[damn]{as="expletive"}')
```

### Audio Files

```python
# Basic audio with description
ssmd.to_ssml('[doorbell]{src="https://example.com/sounds/bell.mp3"}')
# → <audio src="https://example.com/sounds/bell.mp3"><desc>doorbell</desc></audio>

# With fallback text
ssmd.to_ssml('[cat purring]{src="cat.ogg" desc="Sound file not loaded"}')
# → <audio src="cat.ogg"><desc>cat purring</desc>Sound file not loaded</audio>

# No description
ssmd.to_ssml('[]{src="beep.mp3"}')
# → <audio src="beep.mp3"></audio>

# Advanced audio attributes
# Clip audio (play from 5s to 30s)
ssmd.to_ssml('[music]{src="song.mp3" clip="5s-30s"}')
# → <audio src="song.mp3" clipBegin="5s" clipEnd="30s"><desc>music</desc></audio>

# Speed control
ssmd.to_ssml('[announcement]{src="speech.mp3" speed="150%"}')
# → <audio src="speech.mp3" speed="150%"><desc>announcement</desc></audio>

# Repeat count
ssmd.to_ssml('[jingle]{src="ad.mp3" repeat="3"}')
# → <audio src="ad.mp3" repeatCount="3"><desc>jingle</desc></audio>

# Volume level
ssmd.to_ssml('[alarm]{src="alert.mp3" level="+6dB"}')
# → <audio src="alert.mp3" soundLevel="+6dB"><desc>alarm</desc></audio>

# Combine multiple attributes with fallback text
ssmd.to_ssml('[background]{src="music.mp3" clip="0s-10s" speed="120%" level="-3dB" desc="Fallback text"}')
# → <audio src="music.mp3" clipBegin="0s" clipEnd="10s" speed="120%" soundLevel="-3dB">
#    <desc>background</desc>Fallback text</audio>
```

### Markers

```python
ssmd.to_ssml('I always wanted a @animal cat as a pet.')
# → <speak>I always wanted a <mark name="animal"/> cat as a pet.</speak>

# Markers are removed in plain text (with smart whitespace handling)
ssmd.to_text('word @marker word')
# → "word word" (not "word  word")
```

### Headings

```python
doc = Document(config={
    'heading_levels': {
        1: [('pause_before', '300ms'), ('emphasis', 'strong'), ('pause', '300ms')],
        2: [('pause_before', '75ms'), ('emphasis', 'moderate'), ('pause', '75ms')],
        3: [('pause_before', '50ms'), ('prosody', {'rate': 'slow'}), ('pause', '50ms')],
    }
})

doc.add("""
# Chapter 1
## Section 1.1
### Subsection
""")

ssml = doc.to_ssml()
```

### Extensions (Platform-Specific)

```python
# Amazon Polly whisper effect
ssmd.to_ssml('[whispered text]{ext="whisper"}')
# → <speak><amazon:effect name="whispered">whispered text</amazon:effect></speak>

# Custom extensions
doc = Document(config={
    'extensions': {
        'custom': lambda text: f'<custom-tag>{text}</custom-tag>'
    }
})
```

#### Google Cloud TTS Speaking Styles

Google Cloud TTS supports speaking styles via the `google:style` extension. You can use
SSMD's extension system to add these styles:

```python
from ssmd import Document

# Configure Google TTS styles
doc = Document(config={
    'extensions': {
        'cheerful': lambda text: f'<google:style name="cheerful">{text}</google:style>',
        'calm': lambda text: f'<google:style name="calm">{text}</google:style>',
        'empathetic': lambda text: f'<google:style name="empathetic">{text}</google:style>',
        'apologetic': lambda text: f'<google:style name="apologetic">{text}</google:style>',
        'firm': lambda text: f'<google:style name="firm">{text}</google:style>',
    }
})

# Use styles in your content
doc.add_sentence("[Welcome to our service!]{ext=\"cheerful\"}")
doc.add_sentence("[We apologize for the inconvenience.]{ext=\"apologetic\"}")
doc.add_sentence("[Please remain calm.]{ext=\"calm\"}")

ssml = doc.to_ssml()
# → <speak>
#    <google:style name="cheerful">Welcome to our service!</google:style>
#    <google:style name="apologetic">We apologize for the inconvenience.</google:style>
#    <google:style name="calm">Please remain calm.</google:style>
#    </speak>
```

**Available Google TTS Styles:**

- `cheerful` - Upbeat and positive tone
- `calm` - Relaxed and soothing tone
- `empathetic` - Understanding and compassionate tone
- `apologetic` - Sorry and regretful tone
- `firm` - Confident and authoritative tone
- `news` - Professional news anchor tone
- `conversational` - Natural conversation tone

**Note:** These styles are only supported by specific Google Cloud TTS voices (typically
Neural2 and Studio voices). See the
[Google Cloud TTS documentation](https://cloud.google.com/text-to-speech/docs/speaking-styles)
for voice compatibility.

For a complete example, see `examples/google_tts_styles.py`:

```bash
python examples/google_tts_styles.py
```

## Parser API - Extract Structured Data

The SSMD parser provides an alternative to SSML generation by extracting structured
segments from SSMD text. This is useful when you need programmatic control over SSMD
features or want to build custom TTS pipelines.

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
- `model_size` (str): spaCy model size - "sm", "md", "lg", "trf" (default: "sm")
- `spacy_model` (str): Deprecated alias; size is inferred from the model name
- `use_spacy` (bool): If False, use fast regex splitting instead of spaCy (default:
  True)

**Returns:** List of `Sentence` objects (alias: `SSMDSentence`). Each sentence includes
`paragraph_index` and `sentence_index` for document ordering.

**Example:**

```python
from ssmd import parse_sentences

# Default: uses small spaCy models (en_core_web_sm)
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

# Deprecated alias (size inferred from name)
sentences = parse_sentences("Medical text.", spacy_model="en_core_web_lg")
```

**Sentence Detection Configuration:**

SSMD supports flexible sentence detection with quality/speed tradeoffs:

- **Fast mode** (`use_spacy=False`): Regex-based splitting, no dependencies, ~60x faster
- **Auto-detect** (default): Uses phrasplit's configured model and falls back to regex
- **Small models** (`model_size="sm"`): Best balance of speed and accuracy
- **Medium models** (`model_size="md"`): Better accuracy for complex text
- **Large models** (`model_size="lg"`): Best accuracy, slower
- **Transformer models** (`model_size="trf"`): Research-grade accuracy, slowest

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

#### `ssmd.from_ssml(ssml_text, **config)` → `str`

Convert SSML to SSMD format.

**Parameters:**

- `ssml_text` (str): SSML XML string
- `**config`: Optional configuration parameters

**Returns:** SSMD markdown string

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

✅ Text ✅ Emphasis (`*text*`, `**strong**`, `~~reduced~~`, `[text]{emphasis="none"}`)
✅ Break (`...500ms`, `...2s`, `...n/w/c/s/p`) ✅ Language (`[text]{lang="en"}`,
`[text]{lang="en-GB"}`) ✅ Voice inline (`[text]{voice="Joanna"}`,
`[text]{voice-lang="en-GB" gender="female"}`) ✅ Voice directives (`<div voice="name">`)
✅ Mark (`@marker`) ✅ Paragraph (`\n\n`) ✅ Phoneme (`[text]{sampa="xsampa"}`,
`[text]{ipa="ipa"}`) ✅ Prosody shorthand (`++loud++`, `>>fast>>`, `^^high^^`) ✅
Prosody explicit (`[text]{vrp="555"}`, `[text]{v="5"}`) ✅ Substitution
(`[text]{sub="alias"}`) ✅ Say-as (`[text]{as="telephone"}`,
`[text]{as="date" detail="1"}`) ✅ Audio (`[desc]{src="url.mp3" desc="alt"}`,
`[desc]{src="url.mp3" clip="5s-30s" speed="120%"}`) ✅ Headings (`# ## ###`) ✅
Extensions (`[text]{ext="whisper"}`, Google TTS styles) ✅ Auto-sentence tags (`<s>`) ✅
**SSML ↔ SSMD bidirectional conversion**

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

- **Homepage:** https://github.com/holgern/ssmd
- **PyPI:** https://pypi.org/project/ssmd/
- **Issues:** https://github.com/holgern/ssmd/issues
- **Documentation:** https://ssmd.readthedocs.io/

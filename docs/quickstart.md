# Quick Start

This guide will help you get started with SSMD quickly.

## Basic Conversion

For machine-driven authoring, use the root-level JSON interface and check both the
process exit status and command-specific result fields:

```bash
ssmd --json create draft.ssmd -o output.ssmd --fail-on-warn
ssmd --json lint output.ssmd --roundtrip --fail-on-warn
ssmd --json inspect output.ssmd --spans
ssmd --json to-ssml output.ssmd -o output.ssml
ssmd --json text output.ssmd
```

Creation is complete only when `result.created == true`, `bytes_written` is nonzero,
and the output exists; linting is complete only when `result.passed == true`.

The simplest way to use SSMD is with the convenience functions:

### SSMD to SSML

```python
import ssmd

# Convert SSMD markup to SSML
ssml = ssmd.to_ssml("Hello *world*!")
print(ssml)
# Output: <speak>Hello <emphasis>world</emphasis>!</speak>

# More complex example
ssml = ssmd.to_ssml("""
# Welcome
Hello *world*!
This is a ...500ms pause.
[Bonjour]{lang="fr"} everyone!
""")
```

### Strip Markup

Remove all SSMD markup to get plain text:

```python
import ssmd

plain = ssmd.to_text("Hello *world* @marker!")
print(plain)
# Output: Hello world!
```

### SSML to SSMD

Convert SSML back to SSMD format:

```python
import ssmd

ssml = '<speak><emphasis>Hello</emphasis> world</speak>'
ssmd_text = ssmd.from_ssml(ssml)
print(ssmd_text)
# Output: *Hello* world
```

## Using the Document API

For building and managing TTS content, use the Document class:

### Creating Documents

```python
from ssmd import Document

# Create an empty document
doc = Document()

# Create with initial content
doc = Document("Hello *world*!")

# Create with configuration
doc = Document(
    config={'auto_sentence_tags': True},
    capabilities='pyttsx3'
)
```

### Building Documents

```python
from ssmd import Document

# Build incrementally
doc = Document()
doc.add_sentence("Hello and *welcome*!")
doc.add_sentence("This is SSMD.")
doc.add_paragraph("Starting a new paragraph.")

# Method chaining
doc = Document() \
    .add("Hello ") \
    .add("*world*!") \
    .add_sentence("Next sentence.")
```

### Exporting Documents

```python
from ssmd import Document

doc = Document("Hello *world*!")

# Export to different formats
ssml = doc.to_ssml()      # SSML XML
markdown = doc.to_ssmd()  # SSMD markdown
text = doc.to_text()      # Plain text

# Access properties
print(doc.ssmd)           # Raw SSMD content
print(len(doc))           # Number of sentences
print(len(list(doc.paragraphs())))  # Number of paragraphs
```

## TTS Streaming

Iterate through documents sentence-by-sentence for TTS:

```python
from ssmd import Document

# Create document
doc = Document(config={'auto_sentence_tags': True})

# Build content
doc.add_paragraph("# Chapter 1")
doc.add_sentence("Welcome to SSMD!")
doc.add_sentence("This is the first sentence.")
doc.add_sentence("This is the second sentence.")
doc.add_paragraph("# Chapter 2")
doc.add_sentence("Here's another chapter.")

# Iterate through sentences
for i, sentence in enumerate(doc.sentences(), 1):
    print(f"Sentence {i}: {sentence}")
    # Your TTS engine here:
    # tts_engine.speak(sentence)

# Access specific sentences
sentence_count = len(list(doc.sentences()))
print(f"Total sentences: {sentence_count}")
print(f"Total paragraphs: {len(list(doc.paragraphs()))}")
print(f"First: {doc[0]}")
print(f"Last: {doc[-1]}")
```

## Document Editing

Documents are mutable and support list-like operations:

```python
from ssmd import Document

doc = Document("First. Second. Third.")

# Edit sentences
doc[0] = "Modified first sentence."
del doc[1]  # Remove second sentence

# String operations
doc.replace("sentence", "line")

# Insert content
doc.insert(0, "New opening sentence.")

# Clear all content
doc.clear()
```

## Advanced Document Operations

```python
from ssmd import Document

# Load from SSML
doc = Document.from_ssml('<speak><emphasis>Hello</emphasis></speak>')

# Merge documents
doc1 = Document("First document.")
doc2 = Document("Second document.")
doc1.merge(doc2, separator="\n\n")

# Split into sentences
sentences = doc.split()  # Returns list of Document objects

# Iterate with Document objects
for sent_doc in doc.sentences(as_documents=True):
    ssml = sent_doc.to_ssml()
    ssmd = sent_doc.to_ssmd()
```

## Working with TTS Engines

Filter output based on engine capabilities:

### Using Presets

```python
from ssmd import Document

# Use preset for eSpeak (limited SSML support)
doc = Document('*Hello* [world]{lang="fr"}!', capabilities='espeak')
ssml = doc.to_ssml()
# eSpeak doesn't support emphasis or language switching
# Output: <speak>Hello world!</speak>

# Use preset for Google TTS (full support)
doc = Document('*Hello* [world]{lang="fr"}!', capabilities='google')
ssml = doc.to_ssml()
# Output: <speak><emphasis>Hello</emphasis> <lang xml:lang="fr-FR">world</lang>!</speak>
```

Available presets:

- `minimal` - Plain text only
- `pyttsx3` - Basic prosody only
- `espeak` - Moderate support (breaks, prosody, phonemes)
- `google` / `azure` - Full SSML support
- `polly` / `amazon` - Full + Amazon extensions
- `full` - All features enabled

### Custom Capabilities

```python
from ssmd import Document, TTSCapabilities

# Define exactly what your TTS engine supports
caps = TTSCapabilities(
    emphasis=True,
    break_tags=True,
    prosody=False,  # No prosody support
    language=True
)

doc = Document("*Hello* world!", capabilities=caps)
```

## Common Patterns

### Emphasis and Stress

```python
ssmd.to_ssml("This is *important*!")
ssmd.to_ssml("This is **very important**!")
```

### Pauses and Breaks

```python
# Specific duration (required - bare ... is not a break)
ssmd.to_ssml("Hello ...500ms world")
ssmd.to_ssml("Hello ...2s world")
ssmd.to_ssml("Hello ...1s world")  # 1 second

# Strength-based
ssmd.to_ssml("Hello ...c world")  # comma
ssmd.to_ssml("Hello ...s world")  # sentence
ssmd.to_ssml("Hello ...p world")  # paragraph
ssmd.to_ssml("Hello ...n world")  # none/no break
```

### Voice Control

```python
# Volume
ssmd.to_ssml('[loud]{volume="loud"}')
ssmd.to_ssml('[very loud]{volume="x-loud"}')
ssmd.to_ssml('[soft]{volume="soft"}')

# Speed
ssmd.to_ssml('[fast]{rate="fast"}')
ssmd.to_ssml('[very fast]{rate="x-fast"}')
ssmd.to_ssml('[slow]{rate="slow"}')

# Pitch
ssmd.to_ssml('[high]{pitch="high"}')
ssmd.to_ssml('[very high]{pitch="x-high"}')
ssmd.to_ssml('[low]{pitch="low"}')
```

### Language Switching

```python
ssmd.to_ssml('[Bonjour]{lang="fr"} everyone!')
ssmd.to_ssml('[Hola]{lang="es-MX"} amigos!')
ssmd.to_ssml('[Hello]{lang="en-GB"} there!')
```

### Phonetic Pronunciation

```python
ssmd.to_ssml('[tomato]{ph="təˈmeɪtoʊ"}')
ssmd.to_ssml('[hello]{ipa="həˈloʊ"}')
```

## Next Steps

- Read the complete {doc}`syntax` reference
- Learn about {doc}`capabilities` filtering
- Explore {doc}`examples` for real-world use cases
- Check the {doc}`api` documentation for advanced usage

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

For complete documents, prefer the `.ssmd.md` filename convention. Plain `.md` remains a
generic Markdown option, and `.ssmd` remains supported for compatibility. Generic
`ssmd convert` infers plain `.md` as SSMD only when its front matter contains
`ssmd_version`; otherwise pass `--from` explicitly.

Raw `<div>` blocks, `voice-lang`, compact prosody aliases, and symbolic prosody forms
are legacy compatibility syntax. Use `ssmd migrate` to make an explicit, verified
upgrade.

## Installation

```bash
pip install ssmd
```

Legacy sentence-oriented helpers use **phrasplit** for sentence detection; strict 0.9
structural parsing remains sentence-neutral. Runtime dependencies include `phrasplit`
and `pyyaml` (for YAML front matter). Pass `use_spacy=False` to legacy helpers for fast
regex splitting, or enable a spaCy model for higher accuracy.

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

The canonical 0.9 example above is a standalone document. Short conversion strings below
are body fragments for brevity.

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
ssmd lint story.ssmd.md

# Validate with a target capability profile (kokoro, google-ssml, ...)
ssmd lint story.ssmd.md --profile kokoro

# CI: fail on warnings too
ssmd lint story.ssmd.md --fail-on-warn

# Machine-readable JSON output (preferred)
ssmd --json lint story.ssmd.md
ssmd --json profiles
ssmd --json voices list --provider kokoro
ssmd --json inspect story.ssmd.md --spans
# Atomically create a formatted, validated SSMD file
ssmd --json create draft.ssmd.md -o story.ssmd.md --fail-on-warn

# Convert SSMD to SSML
ssmd to-ssml story.ssmd.md -o story.ssml
ssmd to-ssml story.ssmd.md --target ssml-1.1 --language en  # strict target with root language

# Convert SSML to SSMD
ssmd from-ssml story.ssml -o story.ssmd.md

# General conversion. Plain .md requires ssmd_version for automatic SSMD inference.
ssmd convert story.ssmd.md --to ssml -o story.ssml
ssmd convert story.ssml --from ssml --to ssmd -o story.ssmd.md
ssmd convert story.ssmd.md --to text -o story.txt

# Read from stdin
cat story.ssmd.md | ssmd convert - --from ssmd --to ssml

# Plain text with strict target-capability filtering
ssmd text story.ssmd.md --capabilities minimal

# Format SSMD in-place
ssmd fmt story.ssmd.md -w

# Check whether formatting would change (useful in CI)
ssmd fmt story.ssmd.md --check

# List supported lint profiles and capability presets
ssmd profiles
ssmd --json profiles

# Inspect parsed spans, sentences, or paragraphs
ssmd inspect story.ssmd.md --spans
ssmd inspect story.ssmd.md --sentences
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

ssmd --json create draft.ssmd.md -o review.ssmd.md --voice-provider kokoro
ssmd --json lint review.ssmd.md --voice-provider kokoro --roundtrip --fail-on-warn
```

`create` materializes only the bindings used by the document and eligible
`pause_defaults`; `lint`, `inspect`, `text`, `to-ssml`, and `fmt` do not rewrite source
headers. Use `--config PATH` or `SSMD_CONFIG` to select a different authoring config and
`--no-yaml-header` only when leading `---` must be treated as literal content. Portable
`title` metadata is preserved in the header and excluded from plain text and SSML
speech. In JSON mode, treat `result.created` and the output path as mandatory success
checks in addition to the process exit code and top-level `ok`.

### Legacy 0.8 Document API - Build TTS Content Incrementally

These sentence/list examples use unversioned legacy or SSMD 0.8 documents. SSMD 0.9
documents, including `Document.from_ssml()` results, reject sentence-level APIs; use
structural parsing and explicit sentence spans for 0.9 content.

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

### Legacy 0.8 TTS Streaming Integration

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

Given a complete strict 0.9 document, use `parse_structure()` before downstream
normalization and sentence segmentation:

```text
SSMD parse -> semantic preparation/normalization -> sentence splitting -> G2P
```

```python
import ssmd

parsed = ssmd.parse_structure(source, dialect="0.9")
prepared_text = normalize(parsed.clean_text, parsed.annotations)
sentence_spans = split_with_offsets(prepared_text)
ssml = ssmd.to_ssml(source, sentence_spans=sentence_spans)
```

SSMD owns structural markup, clean text, metadata, and offsets. It does not perform
number or abbreviation normalization, generic language detection, Spokenform
integration, or G2P. Remap annotation offsets after normalization and protect explicit
`ph` and `ipa` ranges. Strict 0.9 rendering uses caller-owned sentence spans; sentence
detection is confined to legacy sentence-oriented helpers and unversioned compatibility
conversion.

### Legacy 0.8 Document Editing

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
doc = Document(
    "*Hello* [world]{lang=\"en\"}!",
    config={"dialect": "0.9"},
    capabilities="pyttsx3",
)
ssml = doc.to_ssml()

# pyttsx3 doesn't support emphasis or language tags, so they're stripped:
# <speak>Hello world!</speak>
```

**Available Presets:**

- `minimal` - Plain text only (no SSML)
- `pyttsx3` - Minimal support (basic prosody only)
- `espeak` - Moderate support (breaks, language, prosody, phonemes)
- `google` / `azure` / `microsoft` - Provider-specific capability adaptation; support
  varies by feature
- `polly` / `amazon` - Provider-specific features, including configured Amazon
  extensions
- `full` - Enable all features implemented by the SSMD renderer; this is not a claim of
  universal SSML support

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

doc = Document("*Hello* world!", config={"dialect": "0.9"}, capabilities=caps)
```

#### Capability-Aware Rendering (Strict 0.9)

Capability profiles describe SSMD renderer mappings, not universal provider behavior.
Render the complete strict document and inspect any reported losses; do not call
sentence-level `Document` APIs with 0.9 input.

```python
import ssmd
from ssmd import Document

source = """\
---
ssmd_version: '0.9'
---
# Welcome
*Hello* world! [Bonjour]{lang="fr"} everyone ...300ms.
"""
structure = ssmd.parse_structure(source, dialect="0.9")
document = Document(source, capabilities="espeak", config={"dialect": "0.9"})

print(structure.clean_text)
print(document.to_ssml(target="provider", loss_policy="warn"))
```

Provider presets describe SSMD renderer mappings, not universal service support. See
[`docs/capabilities.md`](docs/capabilities.md) for target and loss-policy guidance.

Built-in presets can produce different SSML for the same source. Select
`target="provider"` and an explicit loss policy, then inspect conversion diagnostics.
Presets do not guarantee that a specific endpoint or voice accepts every generated
feature.

See [`docs/capabilities.md`](docs/capabilities.md) for supported preset details and
examples.

## SSMD Syntax Reference

New documents should declare `ssmd_version: "0.9"` and use the canonical forms below.
The `ssmd_version` front-matter field selects strict 0.9 parsing; migration is the
explicit way to upgrade legacy input.

### Document structure and front matter

```yaml
---
ssmd_version: "0.9"
title: Review podcast
---
```

Front matter is metadata and is not spoken. `title`, voice bindings, pause defaults,
language-detection hints, and voice defaults are validated portable metadata. Local
provider inventories and executable extension handlers belong in trusted user
configuration, not the document header.

### Text, emphasis, paragraphs, and breaks

```ssmd
Ordinary text uses Markdown-style paragraphs.

*moderate emphasis*, **strong emphasis**, and ~~reduced emphasis~~.
A bare ... is literal ellipsis; use ...500ms, ...2s, ...w, ...c, ...s, or ...p for a break.

@chapter
```

Blank lines separate paragraphs. Headings use `#` through `######`. Escape SSMD
metacharacters when they should be spoken literally.

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
`scope="pronunciation"` only when language metadata should affect pronunciation
processing without changing semantic language context.

### Voice selection

`voice` identifies a logical or concrete voice. Feature-based selectors use the
canonical `voice-name`, `voice-languages`, `gender`, `age`, and `variant` attributes:

```ssmd
[Hello]{voice="host"}
[Bonjour]{voice-languages="fr-FR" gender="female"}
[Hello]{voice-name="en-US-Wavenet-A" voice-languages="en-US"}

:::{voice="host"}
A sustained passage spoken by the host.
:::
```

Use front-matter `voice_bindings` to map logical references to provider voices. For
dialogue, fenced directive blocks keep each speaker's scope visible. Raw `<div>` blocks
are legacy compatibility syntax, not canonical 0.9.

### Prosody

Use explicit named or numeric values for `volume`, `rate`, and `pitch`:

```ssmd
[loud]{volume="loud"}
[fast]{rate="fast"}
[high]{pitch="high"}
[urgent]{volume="x-loud" rate="fast" pitch="high"}
```

Relative numeric values such as `rate="+20%"` are supported. Compact `vrp`, short
`v`/`r`/`p` aliases, punctuation shorthand, and symbolic delimiters are compatibility
forms and MUST NOT be used for new 0.9 documents.

### Audio and extensions

Audio annotations use `src`; `desc` carries description metadata, while annotation
content is spoken fallback text:

```ssmd
[doorbell]{src="https://example.com/bell.mp3" desc="Doorbell"}
[Play this if audio fails]{src="bell.mp3"}
[jingle]{src="ad.mp3" repeat="3"}
```

Extension annotations are interpreted only by configured trusted handlers. Portable
document front matter cannot contain executable extension templates. Provider-specific
output and extension support depend on the selected target and registered handlers.

### Legacy input and migration

Unversioned documents retain legacy compatibility behavior; explicit
`ssmd_version: "0.8"` selects the same legacy dialect. Examples such as raw `<div>`,
`voice-lang`, `_reduced_`, `vrp`, and symbolic prosody are not canonical 0.9. Run
`ssmd migrate FILE --to 0.9` to request a semantic-equivalence-checked conversion.
Review manual actions when the tool cannot prove that the source can be represented
safely.

```bash
ssmd --json migrate legacy.ssmd --to 0.9
```

## Parser API: Strict 0.9 and Legacy 0.8

### Strict 0.9 structural parsing

Use `parse_structure(..., dialect="0.9")` for source-aware, sentence-neutral parsing. It
returns clean text, annotation spans, structural events, front matter, and diagnostics.
It does not run sentence detection.

```python
from ssmd.parser import parse_structure

source = """\
---
ssmd_version: '0.9'
---
:::{voice="host"}
One.
:::
:::{voice="guest"}
Two.
:::
"""
result = parse_structure(source, dialect="0.9")
print(result.clean_text)
print(result.annotations)
print(result.events)
print(result.header)
```

Adjacent sibling directives with no blank line between them belong to the same semantic
paragraph: clean text gets ordinary inline separation and no paragraph event. A blank
line between the directives creates a paragraph boundary. Canonical formatting preserves
that difference; a voice change alone does not create a pause.

For complete examples and offset guidance, see [`docs/parser.md`](docs/parser.md),
[`docs/spans.md`](docs/spans.md), and
[`examples/parser_demo.py`](examples/parser_demo.py).

### Legacy 0.8 sentence and segment APIs

`parse_paragraphs()`, `parse_sentences()`, `parse_segments()`, and
`parse_voice_blocks()` are compatibility helpers for unversioned legacy input and SSMD
0.8. Strict 0.9 documents must use `parse_structure()`; `Document` sentence/list APIs
reject 0.9 input.

This raw `<div>` example is deliberately labeled legacy 0.8 compatibility input; do not
use it as a new-document pattern:

```text
<div voice="sarah">
Hello from Sarah.
</div>
```

Use `ssmd migrate FILE --to 0.9` for semantic-preserving upgrades and review any manual
actions before replacing a source file. The full compatibility API reference is in
[`docs/api.md`](docs/api.md).

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
`complete_document=False` to return only the body fragment. Unrepresentable semantics
raise `SSMLConversionError` by default. Use `SSMLParser` and inspect its `diagnostics`
property when opting into warning or drop policies.

**Parameters:**

- `ssml_text` (str): SSML XML string
- `capabilities` (TTSCapabilities | str | None): Optional renderer capability profile
- `complete_document` (bool): Include the SSMD 0.9 version header (default: `True`)
- `**config`: Optional parser configuration, including `loss_policy`

**Returns:** Complete SSMD 0.9 document or body fragment

### Document Class

#### `Document(content="", config=None, capabilities=None)`

Main document container for building and managing TTS content.

Sentence/list operations are available for unversioned legacy and SSMD 0.8 documents.
SSMD 0.9 documents, including `Document.from_ssml()` results, reject sentence-level
APIs; use structural parsing and explicit sentence spans instead.

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

## Real-World TTS Example: Strict 0.9 Rendering

Strict 0.9 documents are parsed structurally and rendered as complete documents. They do
not use `Document` sentence/list operations; a TTS orchestrator that needs sentence
chunks should supply its own explicit sentence spans.

```python

from ssmd import Document
from ssmd.parser import parse_structure

SOURCE = """\
---
ssmd_version: '0.9'
title: Episode
---
# Welcome
:::{voice="host" voice-languages="en-US"}
Hello and *welcome* to our presentation! Today we'll discuss some ...500ms exciting topics.
:::
:::{voice="guest" voice-languages="en-US"}
Thanks for joining us.
:::
# Conclusion
Thank you for listening @end and goodbye!
"""

async def read_document(source: str, tts_engine) -> None:
    structure = parse_structure(source, dialect="0.9")
    document = Document(source, config={"dialect": "0.9"})
    print(structure.clean_text)
    await tts_engine.speak(document.to_ssml())

# await read_document(SOURCE, tts_engine)
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

- Canonical 0.9 text, paragraphs, headings, marks, timed/strength breaks, and moderate,
  strong, and reduced emphasis.
- Inline annotations for language, voice selection, pronunciation, say-as, substitution,
  prosody, and audio.
- Fenced `:::` directives for scoped voice, language, and prosody.
- Version-aware front matter and migration from legacy/unversioned input with
  semantic-equivalence checks.
- Generic SSML, SSML 1.1, and provider-adapted targets with explicit loss policies.
  Unsupported SSML elements are not silently claimed as fully supported.

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

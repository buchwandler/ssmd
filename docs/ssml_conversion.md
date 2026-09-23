# SSML to SSMD Conversion

SSMD supports bidirectional conversion: you can convert SSML back to SSMD format. This
is useful for editing existing SSML, migrating from other tools, or creating round-trip
workflows.

`ssmd.from_ssml()` returns a complete document with `ssmd_version: "0.9"` by default.
Set `complete_document=False` when a body fragment is required. Unrepresentable SSML
semantics raise `SSMLConversionError` by default. Use `SSMLParser` with
`loss_policy="warn"` or `"drop"` to opt into conversion losses and inspect its
`diagnostics` property. The feature examples below request fragments where their
expected output shows only the body.

## TTS pipeline integration

Use structural parsing when sentence boundaries must be computed after semantic
preparation:

```text
SSMD parse -> semantic preparation/normalization -> sentence splitting -> G2P
```

```python
parsed = ssmd.parse_spans(source)
# Normalize parsed.clean_text and remap annotations before splitting.
ssml = ssmd.to_ssml(source, sentence_spans=sentence_spans)
```

`sentence_spans` accepts objects exposing `char_start` and `char_end` offsets, or the
three-item tuples returned by `iter_sentences_spans()`. These offsets must refer to the
structural clean-text coordinate space. SSMD does not normalize numbers or
abbreviations, infer a primary language, or integrate Spokenform/G2P. Protect explicit
`ph` and `ipa` ranges during downstream normalization.

## Basic Conversion

### Using the Convenience Function

```python
import ssmd

# Convert SSML to SSMD
ssml = '<speak><emphasis>Hello</emphasis> world</speak>'
ssmd_text = ssmd.from_ssml(ssml)
print(ssmd_text)
# Complete SSMD 0.9 document beginning with:
# ---
# ssmd_version: '0.9'
# ---
# *Hello* world
```

### Using the Document Class

```python
from ssmd import Document

ssml = '<speak><emphasis>Hello</emphasis> world</speak>'
doc = Document.from_ssml(ssml)
ssmd_text = doc.to_ssmd()
print(ssmd_text)
# Output: *Hello* world
```

## Commonly Representable SSML Elements

### Emphasis

```python
# Moderate emphasis
ssmd.from_ssml('<emphasis>text</emphasis>', complete_document=False)
# → *text*

# Strong emphasis
ssmd.from_ssml('<emphasis level="strong">text</emphasis>', complete_document=False)
# → **text**
```

### Breaks

```python
# Time-based breaks
ssmd.from_ssml('<break time="500ms"/>', complete_document=False)
# → ...500ms

ssmd.from_ssml('<break time="2s"/>', complete_document=False)
# → ...2s

# Strength-based breaks
ssmd.from_ssml('<break strength="weak"/>', complete_document=False)
# → ...w

ssmd.from_ssml('<break strength="medium"/>', complete_document=False)
# → ...c

ssmd.from_ssml('<break strength="strong"/>', complete_document=False)
# → ...s
```

### Language

```python
# Full locale
ssmd.from_ssml('<lang xml:lang="fr-FR">Bonjour</lang>', complete_document=False)
# → [Bonjour]{lang="fr"}

# Non-standard locales preserved
ssmd.from_ssml('<lang xml:lang="en-GB">Hello</lang>', complete_document=False)
# → [Hello]{lang="en-GB"}
```

SSMD's pronunciation scope is richer than generic SSML:

```text
[File]{lang="en" scope="pronunciation"}
```

`Segment.to_ssml()` retains the closest standard mapping, `<lang xml:lang="...">`,
because SSML has no portable attribute meaning "pronunciation language only". Generic
engines may therefore change voice or model behavior. Consumers that need the stronger
contract should use `parse_spans()` or `parse_structure()` and honor
`scope="pronunciation"` themselves.

### Phonemes

```python
# IPA notation
ssmd.from_ssml(
    '<phoneme alphabet="ipa" ph="təˈmeɪtoʊ">tomato</phoneme>', complete_document=False
)
# → [tomato]{ph="təˈmeɪtoʊ" alphabet="ipa"}

# X-SAMPA notation
ssmd.from_ssml(
    '<phoneme alphabet="x-sampa" ph="t@meIt@U">tomato</phoneme>', complete_document=False
)
# → [tomato]{ph="t@meIt@U" alphabet="x-sampa"}
```

### Prosody

```python
# Volume
ssmd.from_ssml('<prosody volume="loud">text</prosody>', complete_document=False)
# → [text]{volume="loud"}

ssmd.from_ssml('<prosody volume="x-loud">text</prosody>', complete_document=False)
# → [text]{volume="x-loud"}

# Rate
ssmd.from_ssml('<prosody rate="fast">text</prosody>', complete_document=False)
# → [text]{rate="fast"}

# Pitch
ssmd.from_ssml('<prosody pitch="high">text</prosody>', complete_document=False)
# → [text]{pitch="high"}

# Multiple attributes
ssmd.from_ssml(
    '<prosody volume="loud" rate="fast" pitch="high">text</prosody>',
    complete_document=False,
)
# → [text]{volume="loud" rate="fast" pitch="high"}
```

Symbolic shorthand and compact `vrp` are compatibility-only SSMD input forms. Strict 0.9
documents use named `volume`, `rate`, and `pitch` attributes; migration converts legacy
values when their semantics can be verified.

### Say-As

```python
# Basic say-as
ssmd.from_ssml(
    '<say-as interpret-as="telephone">+1-555-1234</say-as>', complete_document=False
)
# → [+1-555-1234]{as="telephone"}

# With format attribute
ssmd.from_ssml(
    '<say-as interpret-as="date" format="mdy">12/31/2024</say-as>', complete_document=False
)
# → [12/31/2024]{as="date" format="mdy"}
```

### Substitution

```python
ssmd.from_ssml('<sub alias="World Wide Web">WWW</sub>', complete_document=False)
# → [WWW]{sub="World Wide Web"}
```

### Audio

```python
# With description
ssmd.from_ssml('<audio src="sound.mp3">Alternative text</audio>', complete_document=False)
# → [Alternative text]{src="sound.mp3"}

# With desc tag
ssmd.from_ssml('<audio src="bell.mp3"><desc>doorbell</desc></audio>', complete_document=False)
# → [doorbell]{src="bell.mp3"}

# No description
ssmd.from_ssml('<audio src="beep.mp3"></audio>', complete_document=False)
# → []{src="beep.mp3"}
```

### Marks

```python
ssmd.from_ssml('Text <mark name="here"/> more text', complete_document=False)
# → Text @here more text
```

### Paragraphs

```python
ssml = '''<speak>
<p>First paragraph.</p>
<p>Second paragraph.</p>
</speak>'''

ssmd_text = ssmd.from_ssml(ssml, complete_document=False)
# Output:
# First paragraph.
#
# Second paragraph.
```

### Platform Extensions

```python
# Amazon whisper effect
ssml = (
    '<speak xmlns:amazon="https://amazon.com/ssml">'
    '<amazon:effect name="whispered">secret</amazon:effect></speak>'
)
ssmd.from_ssml(ssml, complete_document=False)
# → [secret]{ext="whisper"}
```

## Default Value Filtering

SSMD automatically removes default/medium values to keep output clean:

```python
# Medium values are filtered out
ssml = '<prosody volume="medium" rate="medium" pitch="medium">text</prosody>'
ssmd.from_ssml(ssml, complete_document=False)
# → text  (not [text]{volume="medium" rate="medium" pitch="medium"})

# Only non-default values are included
ssml = '<prosody volume="loud" rate="medium" pitch="medium">text</prosody>'
ssmd.from_ssml(ssml, complete_document=False)
# → [text]{volume="loud"}
```

## Round-Trip Conversion

Convert SSMD → SSML → SSMD preserving semantics:

```python
import ssmd

# Original SSMD
original = '*Hello* [world]{lang="fr"} ...500ms [loud]{volume="loud"}'

# Convert to SSML
ssml = ssmd.to_ssml(original)
print(ssml)
# <speak><emphasis>Hello</emphasis> <lang xml:lang="fr-FR">world</lang>
#  <break time="500ms"/> <prosody volume="loud">loud</prosody></speak>

# Convert back to SSMD
restored = ssmd.from_ssml(ssml, complete_document=False)
print(restored)
# *Hello* [world]{lang="fr"} ...500ms [loud]{volume="loud"}

# Semantically equivalent, even if syntax differs slightly
```

Voice block boundaries are preserved across this conversion. Canonical 0.9 source uses
fenced `:::` directives. Raw `<div voice="...">` forms are accepted only for legacy
compatibility. Nested emphasis or other supported SSMD markup is reconstructed in a
block form when inline annotation syntax would make it literal text. Round-trip checks
compare semantic text, voice context, annotations, breaks, marks, paragraph structure,
and front matter; formatting-only whitespace changes are allowed.

For paragraph-crossing legacy `<div>` scopes, migration keeps paragraph boundaries
outside inline annotations. A scope may become separate paragraph-local annotations
rather than a fenced directive when that preserves legacy paragraph structure. Before
writing, migration verifies clean text, effective annotation coverage, structural
events, and front matter, and writes only when equivalence is established.

## Complex Examples

### Nested Elements

```python
ssml = '''<speak>
<p>
  <emphasis>Important:</emphasis>
  <lang xml:lang="fr-FR">
    <prosody volume="loud">Bonjour</prosody>
  </lang>
</p>
</speak>'''

ssmd_text = ssmd.from_ssml(ssml, complete_document=False)
# Output: *Important:* [Bonjour]{lang="fr" volume="loud"}
```

### Mixed Content

```python
ssml = '''<speak>
<p><emphasis>Hello</emphasis> world</p>
<p>This is <prosody volume="loud">important</prosody></p>
<break time="500ms"/>
<p>Goodbye</p>
</speak>'''

ssmd_text = ssmd.from_ssml(ssml, complete_document=False)
# Output:
# *Hello* world
#
# This is [important]{volume="loud"}
#
# ...500ms
#
# Goodbye
```

## Whitespace Handling

SSMD normalizes whitespace during conversion:

```python
# Extra whitespace is normalized
ssml = '''<speak>
  <emphasis>
    Hello
  </emphasis>
  world
</speak>'''

ssmd_text = ssmd.from_ssml(ssml, complete_document=False)
# → *Hello* world  (whitespace normalized)
```

## Error Handling

### Unsupported SSML semantics

Unrepresentable elements raise `SSMLConversionError` by default. Callers can opt into
warnings or dropping the unsupported wrapper, and must inspect the diagnostics:

```python
import ssmd

ssml = '<speak>Hello <custom>there</custom></speak>'
try:
    ssmd.from_ssml(ssml, complete_document=False)
except ssmd.SSMLConversionError as exc:
    print(exc.diagnostics)

parser = ssmd.SSMLParser({"loss_policy": "warn"})
fragment = parser.to_ssmd(ssml, complete_document=False)
diagnostics = parser.diagnostics  # warning-severity conversion loss
```

`loss_policy="drop"` also flattens unsupported wrapper elements while retaining child
text; its diagnostics have informational severity. Neither policy silently hides the
conversion loss.

### Malformed XML

```python
try:
    ssmd.from_ssml('<speak><emphasis>unclosed</speak>')
except ValueError as exc:
    print(f"XML parse error: {exc}")
```

## Configuration Options

Pass a capability profile to `Document.from_ssml()` only when the conversion should be
adapted to that renderer's feature subset. Without a profile, recognized SSML semantics
are preserved where SSMD can represent them. See the [capability guide](capabilities.md)
for target-specific rendering

```python
from ssmd import Document

ssml = '<speak><emphasis>Hello</emphasis></speak>'
doc = Document.from_ssml(ssml, capabilities='espeak')
ssmd_text = doc.to_ssmd()  # the eSpeak profile omits unsupported emphasis
```

## Use Cases

### Migration from Raw SSML

```python
from ssmd import Document

# You have existing SSML files
with open('old_ssml.xml') as f:
    ssml = f.read()

# Convert to SSMD for easier editing
doc = Document.from_ssml(ssml)
ssmd_text = doc.to_ssmd()

with open('new_ssmd.ssmd.md', 'w') as f:
    f.write(ssmd_text)
```

### SSML Editor Backend

```python
from ssmd import Document

# Load SSML for editing
def load_document(ssml_file):
    with open(ssml_file) as f:
        ssml = f.read()
    return Document.from_ssml(ssml)

# Save as SSML
def save_document(doc, ssml_file):
    ssml = doc.to_ssml()
    with open(ssml_file, 'w') as f:
        f.write(ssml)
```

### Testing and Validation

```python
from ssmd import Document

# Validate SSML by round-trip conversion
def validate_ssml(ssml_text):
    try:
        doc = Document.from_ssml(ssml_text)
        restored_ssml = doc.to_ssml()
        return True
    except Exception as e:
        print(f"Validation failed: {e}")
        return False
```

## Limitations

1. **Syntax differences**: Round-trip conversion is semantically equivalent but may
   normalize attribute order or quoting in annotations
2. **Comments lost**: XML comments are not preserved
3. **Unknown elements**: Conversion rejects unrepresentable semantics by default;
   explicit `warn` or `drop` policies return diagnostics
4. **Attribute order**: Attribute order may change but semantics are preserved
5. **Whitespace**: Whitespace is normalized for readability

## Voice Defaults and Transition Metadata

`Document.to_ssml()` resolves `voice_defaults` before rendering. For example:

```yaml
---
ssmd_version: "0.9"
voice_defaults:
  guest:
    pitch: high
---
```

```text
:::{voice="guest"}
Hello.
:::
```

renders the effective pitch as a numeric SSML value such as `<prosody pitch="+12%">`.
The SSMD source remains concise because inherited values are not written back into the
block. `Document.to_ssmd(include_header=True)` preserves the header and declared body
attributes.

Natural rate and pitch names are deterministic SSMD authoring levels. They compile to
numeric percentages: rate `very-slow` through `very-fast` maps to `65%`, `80%`, `90%`,
`100%`, `110%`, `125%`, `150%`; pitch `very-low` through `very-high` maps to `-20%`,
`-12%`, `-6%`, `+0%`, `+6%`, `+12%`, `+20%`. Explicit numeric values continue to pass
through.

`prosody_transitions` is preserved as document metadata and is available through
`Document.prosody_transitions`. It is not emitted as an invented SSML rate-ramp element.
Standard SSML has no portable speaking-rate contour, so a downstream renderer must apply
any requested transition using its own capabilities.

# SSML to SSMD Conversion

SSMD supports bidirectional conversion: you can convert SSML back to SSMD format. This
is useful for editing existing SSML, migrating from other tools, or creating round-trip
workflows.

## Basic Conversion

### Using the Convenience Function

```python
import ssmd

# Convert SSML to SSMD
ssml = '<speak><emphasis>Hello</emphasis> world</speak>'
ssmd_text = ssmd.from_ssml(ssml)
print(ssmd_text)
# Output: *Hello* world
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

## Supported SSML Elements

### Emphasis

```python
# Moderate emphasis
ssmd.from_ssml('<emphasis>text</emphasis>')
# → *text*

# Strong emphasis
ssmd.from_ssml('<emphasis level="strong">text</emphasis>')
# → **text**
```

### Breaks

```python
# Time-based breaks
ssmd.from_ssml('<break time="500ms"/>')
# → ...500ms

ssmd.from_ssml('<break time="2s"/>')
# → ...2s

# Strength-based breaks
ssmd.from_ssml('<break strength="weak"/>')
# → ...w

ssmd.from_ssml('<break strength="medium"/>')
# → ...c

ssmd.from_ssml('<break strength="strong"/>')
# → ...s
```

### Language

```python
# Full locale
ssmd.from_ssml('<lang xml:lang="fr-FR">Bonjour</lang>')
# → [Bonjour]{lang="fr"}

# Non-standard locales preserved
ssmd.from_ssml('<lang xml:lang="en-GB">Hello</lang>')
# → [Hello]{lang="en-GB"}
```

### Phonemes

```python
# IPA notation
ssmd.from_ssml('<phoneme alphabet="ipa" ph="təˈmeɪtoʊ">tomato</phoneme>')
# → [tomato]{ph="təˈmeɪtoʊ" alphabet="ipa"}

# X-SAMPA notation
ssmd.from_ssml('<phoneme alphabet="x-sampa" ph="t@meIt@U">tomato</phoneme>')
# → [tomato]{ph="t@meIt@U" alphabet="x-sampa"}
```

### Prosody

```python
# Volume
ssmd.from_ssml('<prosody volume="loud">text</prosody>')
# → [text]{volume="loud"}

ssmd.from_ssml('<prosody volume="x-loud">text</prosody>')
# → [text]{volume="x-loud"}

# Rate
ssmd.from_ssml('<prosody rate="fast">text</prosody>')
# → [text]{rate="fast"}

# Pitch
ssmd.from_ssml('<prosody pitch="high">text</prosody>')
# → [text]{pitch="high"}

# Multiple attributes
ssmd.from_ssml('<prosody volume="loud" rate="fast" pitch="high">text</prosody>')
# → [text]{volume="loud" rate="fast" pitch="high"}
```

### Say-As

```python
# Basic say-as
ssmd.from_ssml('<say-as interpret-as="telephone">+1-555-1234</say-as>')
# → [+1-555-1234]{as="telephone"}

# With format attribute
ssmd.from_ssml('<say-as interpret-as="date" format="mdy">12/31/2024</say-as>')
# → [12/31/2024]{as="date" format="mdy"}
```

### Substitution

```python
ssmd.from_ssml('<sub alias="World Wide Web">WWW</sub>')
# → [WWW]{sub="World Wide Web"}
```

### Audio

```python
# With description
ssmd.from_ssml('<audio src="sound.mp3">Alternative text</audio>')
# → [Alternative text]{src="sound.mp3"}

# With desc tag
ssmd.from_ssml('<audio src="bell.mp3"><desc>doorbell</desc></audio>')
# → [doorbell]{src="bell.mp3"}

# No description
ssmd.from_ssml('<audio src="beep.mp3"></audio>')
# → []{src="beep.mp3"}
```

### Marks

```python
ssmd.from_ssml('Text <mark name="here"/> more text')
# → Text @here more text
```

### Paragraphs

```python
ssml = '''<speak>
<p>First paragraph.</p>
<p>Second paragraph.</p>
</speak>'''

ssmd_text = ssmd.from_ssml(ssml)
# Output:
# First paragraph.
#
# Second paragraph.
```

### Platform Extensions

```python
# Amazon whisper effect
ssml = '<amazon:effect name="whispered">secret</amazon:effect>'
ssmd.from_ssml(ssml)
# → [secret]{ext="whisper"}
```

## Default Value Filtering

SSMD automatically removes default/medium values to keep output clean:

```python
# Medium values are filtered out
ssml = '<prosody volume="medium" rate="medium" pitch="medium">text</prosody>'
ssmd.from_ssml(ssml)
# → text  (not [text]{volume="medium" rate="medium" pitch="medium"})

# Only non-default values are included
ssml = '<prosody volume="loud" rate="medium" pitch="medium">text</prosody>'
ssmd.from_ssml(ssml)
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
restored = ssmd.from_ssml(ssml)
print(restored)
# *Hello* [world]{lang="fr"} ...500ms [loud]{volume="loud"}

# Semantically equivalent, even if syntax differs slightly
```

Voice block boundaries are preserved across this conversion. Single-line and multiline
`<div voice="...">` forms are equivalent, and nested emphasis or other supported SSMD
markup is reconstructed in a block form when inline annotation syntax would make it
literal text. Round-trip checks compare semantic text, voice context, annotations,
breaks, marks, paragraph structure, and front matter; formatting-only whitespace changes
are allowed.

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

ssmd_text = ssmd.from_ssml(ssml)
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

ssmd_text = ssmd.from_ssml(ssml)
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

ssmd_text = ssmd.from_ssml(ssml)
# → *Hello* world  (whitespace normalized)
```

## Error Handling

### Invalid SSML

```python
import ssmd

try:
    ssmd.from_ssml('<speak><invalid>text</invalid></speak>')
except ValueError as e:
    print(f"Error: {e}")

# Invalid/unknown tags are treated as plain text
```

### Malformed XML

```python
try:
    ssmd.from_ssml('<speak><emphasis>unclosed</speak>')
except ValueError as e:
    print(f"XML Parse Error: {e}")
```

## Configuration Options

```python
from ssmd import Document

parser = Document(capabilities='espeak')

# SSML features not supported by eSpeak will be simplified
ssml = '<speak><emphasis>Hello</emphasis></speak>'
doc = Document.from_ssml(ssml, capabilities='espeak')
ssmd_text = doc.to_ssmd()
# eSpeak doesn't support emphasis, so output is just: Hello
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

with open('new_ssmd.txt', 'w') as f:
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
3. **Unknown elements**: Custom SSML elements are converted to plain text
4. **Attribute order**: Attribute order may change but semantics are preserved
5. **Whitespace**: Whitespace is normalized for readability

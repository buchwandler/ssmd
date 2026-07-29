# TTS Engine Capabilities

SSMD can automatically filter SSML features based on your TTS engine's capabilities.
This ensures compatibility by converting unsupported features to plain text.

## Why Capabilities Matter

Different TTS engines support different SSML features:

- **Basic engines** (pyttsx3, eSpeak) support limited SSML
- **Cloud services** (Google, Azure, Amazon Polly) support full SSML
- **Custom engines** may have unique limitations

Without capability filtering, unsupported SSML tags could:

- Be ignored silently
- Cause errors
- Be spoken as literal text
- Break TTS playback

SSMD solves this by automatically stripping unsupported features.

## Using Capability Presets

The easiest way is to use a built-in preset:

```python
from ssmd import Document

# Configure for your TTS engine
doc = Document('*Hello* [world]{lang="fr"}!', capabilities='espeak')

# Unsupported features are automatically removed
ssml = doc.to_ssml()
# eSpeak doesn't support emphasis or language
# Output: <speak>Hello world!</speak>
```

### Available Presets

#### minimal

Plain text only, no SSML features:

```python
doc = Document(capabilities='minimal')
```

**Supported:** None (all stripped to text)

#### pyttsx3

For the pyttsx3 library (offline TTS):

```python
doc = Document(capabilities='pyttsx3')
```

**Supported:**

- Prosody (volume, rate, pitch) - limited
- Paragraphs

**Not supported:**

- Emphasis
- Breaks
- Language switching
- Phonemes
- Say-as
- Audio
- Marks

#### espeak

For eSpeak/eSpeak-NG:

```python
doc = Document(capabilities='espeak')
```

**Supported:**

- Breaks (pauses)
- Language switching
- Prosody (volume, rate, pitch)
- Phonemes (IPA and X-SAMPA)
- Paragraphs

**Not supported:**

- Emphasis
- Say-as
- Audio files
- Marks
- Substitution

#### google / azure / microsoft

For cloud TTS services with full SSML support:

```python
doc = Document(capabilities='google')
# or
doc = Document(capabilities='azure')
```

**Supported:** All standard SSML features

- Emphasis
- Breaks
- Language switching
- Prosody
- Phonemes
- Say-as
- Paragraphs
- Marks
- Substitution

**Not supported:**

- Audio files (varies by service)
- Platform-specific extensions

#### polly / amazon

For Amazon Polly with extensions:

```python
doc = Document(capabilities='polly')
```

**Supported:** All features including:

- All standard SSML
- Amazon extensions (whisper, DRC)
- Audio files

#### full

All features enabled (no filtering):

```python
doc = Document(capabilities='full')
```

Use this when you know your engine supports everything or want to test.

## Capability Profiles and Linting

Profiles describe which SSMD tags and attributes are supported without mutating output.
Use them to validate input before conversion:

```python
from ssmd import get_profile, list_profiles, lint

profiles = list_profiles()
profile = get_profile("ssmd-core")
issues = lint("[Hello]{ext='whisper'}", profile="kokoro")
```

Profiles are separate from runtime `TTSCapabilities` presets.

## Custom Capabilities

Define exactly what your TTS engine supports:

### Basic Example

```python
from ssmd import Document, TTSCapabilities

# Create custom capability profile
caps = TTSCapabilities(
    emphasis=False,      # No <emphasis> support
    break_tags=True,     # Supports <break>
    paragraph=True,      # Supports <p>
    language=False,      # No language switching
    prosody=True,        # Supports volume/rate/pitch
    say_as=False,        # No <say-as>
    audio=False,         # No audio files
    mark=False,          # No markers
    phoneme=False,       # No phonetic notation
    substitution=False,  # No substitution
)

doc = Document(capabilities=caps)
```

### Partial Prosody Support

Some engines support only certain prosody attributes:

```python
from ssmd import TTSCapabilities, ProsodySupport, Document

caps = TTSCapabilities(
    prosody=ProsodySupport(
        volume=True,     # Supports volume
        rate=True,       # Supports rate
        pitch=False,     # Does NOT support pitch
    )
)

doc = Document(capabilities=caps)

# Pitch will be stripped, but volume and rate preserved
ssml = doc.to_ssml('[text]{volume="5" rate="4" pitch="5"}')
# → <prosody volume="x-loud" rate="fast">text</prosody>
```

### Extension Support

Control platform-specific extensions:

```python
caps = TTSCapabilities(
    extensions={
        'whisper': True,   # Amazon whisper effect
        'drc': False,      # Dynamic range compression
    }
)

doc = Document(capabilities=caps)

ssml = doc.to_ssml('[secret]{ext="whisper"}')
# → <amazon:effect name="whispered">secret</amazon:effect>
```

## Capability Comparison

Same input with different engines:

### Input

```python
text = '*Hello* world... [this is loud]{volume="5"}!'
```

### Output by Engine

:::{list-table} :header-rows: 1 :widths: 15 85

- - Engine
  - Output SSML
- - minimal
  - `<speak>Hello world... this is loud!</speak>`
- - pyttsx3
  - `<speak>Hello world... <prosody volume="x-loud">this is loud</prosody>!</speak>`
- - espeak
  - `<speak>Hello world<break time="1000ms"/> <prosody volume="x-loud">this is loud</prosody>!</speak>`
- - google
    - `<speak><emphasis>Hello</emphasis> world<break time="1000ms"/> <prosody volume="x-loud">this is loud</prosody>!</speak>`
      :::

## Streaming with Capabilities

Capability filtering works seamlessly with document streaming:

```python
from ssmd import Document

# Create document for specific engine
doc = Document("""
# Welcome
*Hello* world!
[Bonjour]{lang="fr"} everyone!
This is [loud]{volume="loud"}.
""", capabilities='espeak', auto_sentence_tags=True)

# All sentences are pre-filtered for eSpeak
for sentence_doc in doc.sentences(as_documents=True):
    tts_engine.speak(sentence_doc.to_ssml())
    # Emphasis and language are already removed
    # Prosody is preserved
```

## Testing Capabilities

Test what gets filtered:

```python
from ssmd import to_ssml

engines = ['minimal', 'pyttsx3', 'espeak', 'google', 'polly']
text = '*Emphasis* ...500ms [language]{lang="fr"} [loud]{volume="loud"}'

for engine in engines:
    ssml = to_ssml(text, capabilities=engine)
    print(f"{engine:10} → {ssml}")
```

Output:

```text
minimal    → <speak>Emphasis language loud</speak>
pyttsx3    → <speak>Emphasis language <prosody volume="loud">loud</prosody></speak>
espeak     → <speak>Emphasis <break time="500ms"/> <lang xml:lang="fr-FR">language</lang> <prosody volume="loud">loud</prosody></speak>
google     → <speak><emphasis>Emphasis</emphasis> <break time="500ms"/> <lang xml:lang="fr-FR">language</lang> <prosody volume="loud">loud</prosody></speak>
polly      → <speak><emphasis>Emphasis</emphasis> <break time="500ms"/> <lang xml:lang="fr-FR">language</lang> <prosody volume="loud">loud</prosody></speak>
```

## Fallback Behavior

When a feature is unsupported:

1. **Text content is preserved** - Never lost
2. **Markup is stripped** - Clean removal
3. **Whitespace is normalized** - No extra spaces
4. **Nesting is handled** - Inner content preserved

Example:

```python
# With emphasis support disabled
from ssmd import to_ssml

# Emphasis markup is removed, text preserved
ssml = to_ssml("This is *very important* info", capabilities='minimal')
# → <speak>This is very important info</speak>
```

## Best Practices

1. **Match your engine**: Use the appropriate preset or create custom capabilities
2. **Test with your engine**: Verify output works as expected
3. **Graceful degradation**: Write content that works even when features are stripped
4. **Document requirements**: Note which TTS engines your content supports
5. **Use capability detection**: Check engine capabilities at runtime if possible

Example:

```python
# Good: Works with any engine
text = "Hello world! This is important."

# Better: Adds features for engines that support them
text = "Hello world! *This is important*."

# Best: Provides alternatives
text = """
Hello world!
*This is important.*
[This is very important.]{volume="5" rate="2"}
"""
```

## Integration Example

Complete example with capability detection:

```python
from ssmd import Document

class TTSHandler:
    def __init__(self, engine_name):
        self.engine_name = engine_name

    def speak(self, ssmd_text):
        # Convert with automatic filtering
        doc = Document(ssmd_text, capabilities=self.engine_name)
        ssml = doc.to_ssml()

        # Send to TTS engine
        self.engine.speak(ssml)

# Usage
tts = TTSHandler('espeak')
tts.speak('*Hello* [world]{lang="fr"}!')
# Automatically filtered for eSpeak compatibility
```

# SSMD Syntax Reference

This page provides a complete reference for SSMD markup syntax.

## YAML front matter

An SSMD document may begin with a YAML front matter block. The opening delimiter must be
exactly `---` on the first line; the closing delimiter is exactly `---` or `...`. Four
hyphens are ordinary content. Front matter is metadata, not spoken text, and the YAML
root must be a mapping.

```yaml
---
voice_bindings:
  kokoro:
    moderator: af_sarah
pause_defaults:
  enabled: true
  sentence: 250ms
  paragraph: 700ms
---
```

The optional `title` front-matter key is portable document metadata. It must be a
string and is preserved by formatting and authoring commands, but it is never spoken
or included in plain-text or SSML speech output.

```yaml
---
title: Review podcast
---
Hello world.
```

`voice` values in body directives and annotations are stable references. A reference can
be logical and resolved through `voice_bindings`, or direct when it is a concrete
provider voice ID. Effective precedence is built-in defaults, user config, document
header, then explicit CLI/API overrides. The local config file is an authoring facility
and is not part of the portable document.

`pause_defaults` accepts non-negative `ms` or `s` durations. Explicit body break markers
take precedence; defaults do not insert visible pause markers into SSMD source. PyYAML
serialization is deterministic but does not preserve YAML comments.

## Text and Emphasis

SSMD supports all four SSML emphasis levels for fine-grained control over speech
emphasis.

### Moderate Emphasis

Use single asterisks for moderate (default) emphasis:

```python
ssmd.to_ssml("This is *important*")
# → <speak>This is <emphasis>important</emphasis></speak>
```

### Strong Emphasis

Use double asterisks for strong emphasis:

```python
ssmd.to_ssml("This is **very important**")
# → <speak>This is <emphasis level="strong">very important</emphasis></speak>
```

### Reduced Emphasis

Use single underscores for reduced (subtle) emphasis:

```python
ssmd.to_ssml("This is _less important_")
# → <speak>This is <emphasis level="reduced">less important</emphasis></speak>
```

### No Emphasis

Use explicit annotation syntax for no emphasis (rarely used):

```python
ssmd.to_ssml('[monotone reading]{emphasis="none"}')
# → <speak><emphasis level="none">monotone reading</emphasis></speak>
```

:::{note} The "none" emphasis level is rarely needed in practice. It explicitly
instructs the TTS engine to speak without any emphasis, which can be useful for robotic
or monotone speech effects. :::

## Breaks and Pauses

### Time-Based Breaks

Specify duration in milliseconds or seconds using `...` followed by a time value:

```python
ssmd.to_ssml("Wait ...500ms please")
# → <speak>Wait <break time="500ms"/> please</speak>

ssmd.to_ssml("Wait ...2s please")
# → <speak>Wait <break time="2s"/> please</speak>
```

:::{note} Bare `...` (without a time or strength code) is NOT treated as a break. It
will be preserved as literal ellipsis in your text. :::

### Strength-Based Breaks

Use strength codes for semantic pauses:

```python
ssmd.to_ssml("Hello ...n world")   # none
ssmd.to_ssml("Hello ...w world")   # weak (x-weak)
ssmd.to_ssml("Hello ...c world")   # comma (medium)
ssmd.to_ssml("Hello ...s world")   # sentence (strong)
ssmd.to_ssml("Hello ...p world")   # paragraph (x-strong)
```

Strength codes:

- `n` - none
- `w` - weak (x-weak)
- `c` - comma (medium)
- `s` - sentence (strong)
- `p` - paragraph (x-strong)

## Paragraphs

Blank lines separate paragraphs:

```python
text = """
This is the first paragraph.
Still in first paragraph.

This is the second paragraph.
"""

ssmd.to_ssml(text)
# → <speak>This is the first paragraph.
#    Still in first paragraph.
#    This is the second paragraph.</speak>
```

## Headings

Use hash marks for headings (configurable):

```python
from ssmd import Document

text = """
# Main Title
Content here.

## Subtitle
More content.
"""

doc = Document(text, config={
   'heading_levels': {
      1: [('emphasis', 'strong'), ('pause', '500ms')],
      2: [('emphasis', 'moderate')]
   }
})


ssml = doc.to_ssml()
```

## Annotations

Annotations use the format `[text]{key="value"}` where annotations can be:

### Language Codes

Specify language with ISO codes:

```python
# Auto-complete to full locale
ssmd.to_ssml('[Bonjour]{lang="fr"}')
# → <speak><lang xml:lang="fr-FR">Bonjour</lang></speak>

# Explicit locale
ssmd.to_ssml('[Hello]{lang="en-GB"}')
# → <speak><lang xml:lang="en-GB">Hello</lang></speak>
```

Common language codes:

- `en` → en-US
- `fr` → fr-FR
- `de` → de-DE
- `es` → es-ES
- `it` → it-IT
- `ja` → ja-JP
- `zh` → zh-CN
- `ru` → ru-RU

### Voice Selection

SSMD supports two ways to specify voices: **inline annotations** for short phrases and
**block directives** for longer passages (ideal for dialogue and scripts).

#### Inline Voice Annotations

Perfect for short voice changes within a sentence:

```python
# Simple voice name
ssmd.to_ssml('[Hello]{voice="Joanna"}')
# → <speak><voice name="Joanna">Hello</voice></speak>

# Cloud TTS voice (e.g., Google Wavenet, AWS Polly)
ssmd.to_ssml('[Hello]{voice="en-US-Wavenet-A"}')
# → <speak><voice name="en-US-Wavenet-A">Hello</voice></speak>

# Language and gender attributes
ssmd.to_ssml('[Bonjour]{voice-lang="fr-FR" gender="female"}')
# → <speak><voice language="fr-FR" gender="female">Bonjour</voice></speak>

# All attributes (language, gender, variant)
ssmd.to_ssml('[Text]{voice-lang="en-GB" gender="male" variant="1"}')
# → <speak><voice language="en-GB" gender="male" variant="1">Text</voice></speak>
```

Voice attributes:

- `voice="NAME"` - Voice name (e.g., Joanna, en-US-Wavenet-A)
- `voice-lang="LANG"` - Language code (e.g., en-GB)
- `gender="GENDER"` - male, female, or neutral
- `variant="NUMBER"` - Variant number for tiebreaking

#### Voice Directives (Block Syntax)

Perfect for dialogue, podcasts, and scripts with multiple speakers:

> ```python
> script = """
> <div voice="af_sarah">
> Welcome to Tech Talk! I'm Sarah, and today we're diving into the
> fascinating world of text-to-speech technology.
> ...s
> </div>
>
> <div voice="am_michael">
> And I'm Michael! We've got an amazing episode lined up. The advances
> in neural TTS have been incredible lately.
> ...s
> </div>
>
> <div voice="af_sarah">
> So what are we covering today?
> </div>
> """
>
> ssmd.to_ssml(script)
> # Each voice directive creates a separate voice block in SSML
> ```

Voice directives support all voice attributes:

> ```python
> # Language and gender
> multilingual = """
> <div voice-lang="fr-FR" gender="female">
> Bonjour! Comment allez-vous aujourd'hui?
> </div>
>
> <div voice-lang="en-GB" gender="male">
> Hello there! Lovely weather we're having.
> </div>
>
> <div voice-lang="es-ES" gender="female" variant="1">
> ¡Hola! ¿Cómo estás?
> </div>
> """
> ```
>
> Voice directive features:
>
> - Use `<div voice="name">` block syntax
> - Supports all attributes: language, gender, variant
> - Applies to all text until the next directive or paragraph break
> - Automatically detected on SSML→SSMD conversion for long voice blocks
> - Much more readable than inline annotations for dialogue
>
> Mixing inline and directive syntax:
>
> ```python
> # Block directive for main speaker, inline for interruptions
> text = """
> <div voice="sarah">
> Hello everyone, [but wait!]{voice="michael"} Michael interrupts...
> </div>
>
> <div voice="michael">
> Sorry, I had to jump in there!
> </div>
> """
> ```

### Phonetic Pronunciation

#### IPA (International Phonetic Alphabet)

```python
ssmd.to_ssml('[tomato]{ph="təˈmeɪtoʊ"}')
# → <speak><phoneme alphabet="ipa" ph="təˈmeɪtoʊ">tomato</phoneme></speak>

ssmd.to_ssml('[hello]{ipa="həˈloʊ"}')
# → <speak><phoneme alphabet="ipa" ph="həˈloʊ">hello</phoneme></speak>
```

#### X-SAMPA (Extended Speech Assessment Methods Phonetic Alphabet)

```python
ssmd.to_ssml('[dictionary]{sampa="dIkS@n@ri"}')
# → <speak><phoneme alphabet="x-sampa" ph="dIkS@n@ri">dictionary</phoneme></speak>
```

### Substitution (Aliases)

Replace text with alternative pronunciation:

```python
ssmd.to_ssml('[H2O]{sub="water"}')
# → <speak><sub alias="water">H2O</sub></speak>

ssmd.to_ssml('[AWS]{sub="Amazon Web Services"}')
# → <speak><sub alias="Amazon Web Services">AWS</sub></speak>

ssmd.to_ssml('[NATO]{sub="North Atlantic Treaty Organization"}')
```

### Say-As Interpretations

Control how text is interpreted:

```python
# Telephone number
ssmd.to_ssml('[+1-555-0123]{as="telephone"}')

# Date with format
ssmd.to_ssml('[31.12.2024]{as="date" format="dd.mm.yyyy"}')

# Say-as with detail attribute (verbosity control)
ssmd.to_ssml('[123]{as="cardinal" detail="2"}')
# → <speak><say-as interpret-as="cardinal" detail="2">123</say-as></speak>

ssmd.to_ssml('[12/31/2024]{as="date" format="mdy" detail="1"}')
# → <speak><say-as interpret-as="date" format="mdy" detail="1">12/31/2024</say-as></speak>

# Spell out characters
ssmd.to_ssml('[NASA]{as="character"}')

# Number types
ssmd.to_ssml('[123]{as="cardinal"}')     # one hundred twenty-three
ssmd.to_ssml('[1st]{as="ordinal"}')      # first
ssmd.to_ssml('[123]{as="digits"}')       # one two three
ssmd.to_ssml('[3.14]{as="fraction"}')    # three point one four

# Time
ssmd.to_ssml('[14:30]{as="time"}')

# Expletive (censored/beeped)
ssmd.to_ssml('[damn]{as="expletive"}')
```

Supported interpret-as values:

- `character` - Spell out
- `cardinal` - Number
- `ordinal` - First, second, etc.
- `digits` - Individual digits
- `fraction` - Decimal numbers
- `unit` - Measurements
- `date` - Dates
- `time` - Time values
- `telephone` - Phone numbers
- `address` - Street addresses
- `expletive` - Censored words

The `detail` attribute (1-2) controls verbosity level and is platform-specific. Higher
values generally provide more detailed pronunciation.

## Prosody (Voice Control)

Use prosody annotations with explicit key/value pairs:

```python
ssmd.to_ssml('[loud]{volume="loud"}')
ssmd.to_ssml('[slow]{rate="slow"}')
ssmd.to_ssml('[high]{pitch="high"}')
ssmd.to_ssml('[loud and fast]{volume="loud" rate="fast"}')
```

### Scale-Based Values (1-5)

```python
ssmd.to_ssml('[extra loud]{volume="5"}')
ssmd.to_ssml('[extra fast]{rate="5"}')
ssmd.to_ssml('[extra high]{pitch="5"}')
```

Scale mapping:

- Volume: 0=silent, 1=x-soft, 2=soft, 3=medium, 4=loud, 5=x-loud
- Rate: 1=x-slow, 2=slow, 3=medium, 4=fast, 5=x-fast
- Pitch: 1=x-low, 2=low, 3=medium, 4=high, 5=x-high

### Relative Values

```python
# Decibels for volume
ssmd.to_ssml('[louder]{volume="+6dB"}')
ssmd.to_ssml('[quieter]{volume="-3dB"}')

# Percentages for rate and pitch
ssmd.to_ssml('[faster]{rate="+20%"}')
ssmd.to_ssml('[slower]{rate="-10%"}')
ssmd.to_ssml('[higher]{pitch="+15%"}')
ssmd.to_ssml('[lower]{pitch="-5%"}')
```

## Audio Files

### Basic Audio

```python
# With description
ssmd.to_ssml('[doorbell]{src="https://example.com/sounds/bell.mp3"}')
# → <audio src="https://example.com/sounds/bell.mp3"><desc>doorbell</desc></audio>

# No description
ssmd.to_ssml('[]{src="beep.mp3"}')
# → <audio src="beep.mp3"></audio>
```

### Audio with Fallback

```python
ssmd.to_ssml('[cat purring]{src="cat.ogg" alt="Sound file not loaded"}')
# → <audio src="cat.ogg"><desc>cat purring</desc>Sound file not loaded</audio>
```

The fallback text is spoken if the audio file can't be played.

### Advanced Audio Attributes

SSMD supports advanced audio control through SSML attributes:

#### Audio Clipping

Play a portion of an audio file by specifying start and end times:

```python
ssmd.to_ssml('[music]{src="song.mp3" clip="5s-30s"}')
# → <audio src="song.mp3" clipBegin="5s" clipEnd="30s"><desc>music</desc></audio>

ssmd.to_ssml('[intro]{src="podcast.mp3" clip="0s-10s"}')
# → <audio src="podcast.mp3" clipBegin="0s" clipEnd="10s"><desc>intro</desc></audio>
```

#### Speed Control

Adjust playback speed using percentages:

```python
ssmd.to_ssml('[announcement]{src="speech.mp3" speed="150%"}')
# → <audio src="speech.mp3" speed="150%"><desc>announcement</desc></audio>

ssmd.to_ssml('[slow]{src="message.mp3" speed="80%"}')
# → <audio src="message.mp3" speed="80%"><desc>slow</desc></audio>
```

#### Repeat Audio

Repeat audio playback a specific number of times:

```python
ssmd.to_ssml('[jingle]{src="ad.mp3" repeat="3"}')
# → <audio src="ad.mp3" repeatCount="3"><desc>jingle</desc></audio>

ssmd.to_ssml('[beep]{src="alert.mp3" repeat="5"}')
# → <audio src="alert.mp3" repeatCount="5"><desc>beep</desc></audio>
```

#### Volume Adjustment

Control audio volume using decibel adjustment:

```python
ssmd.to_ssml('[alarm]{src="alert.mp3" level="+6dB"}')
# → <audio src="alert.mp3" soundLevel="+6dB"><desc>alarm</desc></audio>

ssmd.to_ssml('[background]{src="music.mp3" level="-3dB"}')
# → <audio src="music.mp3" soundLevel="-3dB"><desc>background</desc></audio>
```

#### Combining Attributes

Multiple audio attributes can be combined with fallback text:

```python
ssmd.to_ssml('[bg music]{src="music.mp3" clip="0s-10s" speed="120%" level="-3dB" alt="Fallback text"}')
# → <audio src="music.mp3" clipBegin="0s" clipEnd="10s" speed="120%" soundLevel="-3dB">
#    <desc>bg music</desc>Fallback text</audio>

ssmd.to_ssml('[effect]{src="sound.mp3" clip="2s-5s" repeat="2" alt="Sound unavailable"}')
# → <audio src="sound.mp3" clipBegin="2s" clipEnd="5s" repeatCount="2">
#    <desc>effect</desc>Sound unavailable</audio>
```

:::{note} Audio attribute support varies by TTS platform. Amazon Polly and Google Cloud
TTS support most of these features. Always test with your specific TTS engine. :::

## Markers

Markers create synchronization points for events:

```python
ssmd.to_ssml('I always wanted a @animal cat as a pet.')
# → <speak>I always wanted a <mark name="animal"/> cat as a pet.</speak>

ssmd.to_ssml('Click @here to continue.')
# → <speak>Click <mark name="here"/> to continue.</speak>
```

Markers are removed when stripping to plain text:

```python
ssmd.to_text('Click @here now')
# → Click now
```

## Extensions

Platform-specific extensions allow you to use TTS features beyond standard SSML.

### Amazon Polly Extensions

Amazon Polly provides effects like whispering and dynamic range compression:

```python
# Whisper effect
ssmd.to_ssml('[secret message]{ext="whisper"}')
# → <amazon:effect name="whispered">secret message</amazon:effect>

# Dynamic range compression (for voice over music)
ssmd.to_ssml('[announcement]{ext="drc"}')
# → <amazon:effect name="drc">announcement</amazon:effect>
```

### Google Cloud TTS Speaking Styles

Google Cloud TTS supports speaking styles for Neural2 and Studio voices. You can
configure these using SSMD's extension system:

```python
from ssmd import Document

# Configure Google TTS styles as extensions
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

Available Google TTS speaking styles:

- `cheerful` - Upbeat and positive tone
- `calm` - Relaxed and soothing tone
- `empathetic` - Understanding and compassionate tone
- `apologetic` - Sorry and regretful tone
- `firm` - Confident and authoritative tone
- `news` - Professional news anchor tone (some voices)
- `conversational` - Natural conversation tone (some voices)

:::{note} Google TTS speaking styles are only supported by specific Neural2 and Studio
voices. See the
[Google Cloud TTS documentation](https://cloud.google.com/text-to-speech/docs/speaking-styles)
for voice compatibility. :::

### Custom Extensions

You can define your own extensions for any custom SSML tags your TTS platform supports:

```python
from ssmd import Document

doc = Document(config={
    'extensions': {
        'robotic': lambda text: f'<voice-transformation type="robot">{text}</voice-transformation>',
        'echo': lambda text: f'<audio-effect type="echo">{text}</audio-effect>',
    }
})

doc.add_sentence("[Hello]{ext=\"robotic\"}")
doc.add_sentence("[world]{ext=\"echo\"}")
```

For a complete Google TTS styles example, see `examples/google_tts_styles.py`.

## Combining Multiple Annotations

Multiple annotations can be space-separated inside the braces:

```python
ssmd.to_ssml('[Bonjour]{lang="fr" volume="5" rate="2"}')
# → <lang xml:lang="fr-FR"><prosody volume="x-loud" rate="slow">Bonjour</prosody></lang>

ssmd.to_ssml('[important]{volume="5" as="character"}')
# → <prosody volume="x-loud"><say-as interpret-as="character">important</say-as></prosody>
```

## Escaping

### XML Special Characters

XML special characters are automatically escaped:

```python
ssmd.to_ssml('5 < 10 & 10 > 5')
# → <speak>5 &lt; 10 &amp; 10 &gt; 5</speak>
```

### Security

All user input is automatically sanitized to prevent XML injection attacks. Special
characters in both text content and annotation parameters are properly escaped:

```python
# Malicious input is safely escaped
ssmd.to_ssml('[text]{sub="value<script>alert(1)</script>"}')
# → <speak><sub alias="value&lt;script&gt;alert(1)&lt;/script&gt;">text</sub></speak>
```

The library ensures:

- **XML validity**: Output is always valid, well-formed XML
- **Injection prevention**: User input cannot break out of attribute values or inject
  tags
- **Automatic escaping**: All special characters (`<`, `>`, `&`, `"`, `'`) are escaped

You can safely use SSMD with untrusted user input in TTS applications.

### Literal Asterisks

To include literal asterisks without emphasis, escape them or use different patterns:

```python
# These won't be treated as emphasis
ssmd.to_ssml('2 * 3 = 6')
# → <speak>2 * 3 = 6</speak>

ssmd.to_ssml('* list item')
# → <speak>* list item</speak>
```

# SSMD Syntax Reference

This page provides a complete reference for SSMD markup syntax.

## YAML front matter

An SSMD document may begin with a YAML front matter block. The opening delimiter must be
exactly `---` on the first line; the closing delimiter is exactly `---` or `...`. Four
hyphens are ordinary content. Front matter is metadata, not spoken text, and the YAML
root must be a mapping.

```yaml
---
ssmd_version: "0.9"
voice_bindings:
  kokoro:
    moderator: af_sarah
pause_defaults:
  enabled: true
  sentence: 250ms
  paragraph: 700ms
---
```

The optional `title` front-matter key is portable document metadata. It must be a string
and is preserved by formatting and authoring commands, but it is never spoken or
included in plain-text or SSML speech output.

```yaml
---
ssmd_version: "0.9"
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

## Document versions and dialects

An optional `ssmd_version` front-matter field selects the document dialect. Unversioned
documents retain the legacy compatibility behavior; `"0.8"` identifies the legacy
dialect, and `"0.9"` selects the strict SSMD 0.9 grammar and canonical structure.
Version values are preserved by formatting and migration writes `"0.9"` only after
checking semantic equivalence.

```yaml
---
ssmd_version: "0.9"
---
Hello [world]{lang="en"}.
```

The CLI accepts `--dialect auto|0.8|0.9` on lint and SSMD-to-SSML conversion commands.
`auto` uses the declared version and preserves the unversioned compatibility default.
Rendering targets are selected separately: `generic` for portable SSML, `ssml-1.1` for
standard SSML 1.1, or `provider` for capability-specific adaptation.
`--loss-policy error|warn|drop` makes losses explicit: reject them, report them, or
allow them with informational diagnostics.

## Semantic language vs pronunciation language

Language annotations are semantic by default:

```text
[Bonjour]{lang="fr"}
```

Use `scope="pronunciation"` when the language should affect only pronunciation/G2P:

```text
[File]{lang="en" scope="pronunciation"}
[Manpower]{lang="en" scope="pronunciation"}diskussion
ge[cancel]{lang="en" scope="pronunciation"}t
[download]{lang="en" scope="pronunciation"}en
```

The canonical 0.9 spelling is `lang`; legacy `language` and `voice-lang` aliases are
compatibility-only and should be converted with `ssmd migrate`. Omitted scope means `semantic`,
and the valid scopes are `semantic` and `pronunciation`. SSMD validates BCP-47 tags but does
not infer a document language.

### Portable language-detection hint

A document may carry a consumer-facing routing hint in front matter:

```yaml
---
language_detection:
  mode: auto
  languages: [de, en]
---
```

`mode` is `off` or `auto`; `auto` requires at least two distinct language entries. SSMD
validates and exposes this metadata, excludes it from clean text, and does not run
detection itself. It is not a local authoring-config default.

## Text and Emphasis

SSMD 0.9 supports moderate, strong, and reduced emphasis. A separate `emphasis="none"`
annotation is also available for explicit no-emphasis instructions.

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
Use double tildes for reduced (subtle) emphasis:
```python
ssmd.to_ssml("This is ~~less important~~")
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

Use inline annotations for short selections and fenced directives for sustained dialogue. `voice`
names a logical or concrete voice; feature selectors use `voice-name`, `voice-languages`,
`gender`, `age`, and `variant`.

    [Hello]{voice="host"}
    [Bonjour]{voice-languages="fr-FR" gender="female"}
    [Hello]{voice-name="en-US-Wavenet-A" voice-languages="en-US"}

    :::{voice="host"}
    Welcome to Tech Talk. This entire block uses the host voice.
    :::

    :::{voice="guest"}
    Thanks for having me.
    :::

Logical references may be resolved through the portable `voice_bindings` front-matter key or
local trusted configuration. Voice selectors are independent of provider inventory data.
Supported feature selectors are preserved when rendering or reported as losses if the selected
target cannot represent them.

Raw `<div>` voice blocks and `voice-lang` are compatibility-only 0.8 syntax. New 0.9
documents use canonical `:::` directives and `voice-languages`.


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

### Compatibility-only prosody aliases

The following forms are accepted only in legacy/unversioned compatibility mode and are not
canonical SSMD 0.9 syntax: compact `vrp`, short `v`/`r`/`p` keys, punctuation prosody, and
symbolic delimiters such as `++text++`. Strict 0.9 parsing diagnoses these forms. Use explicit
`volume`, `rate`, and `pitch` attributes in new documents. Run `ssmd migrate FILE --to 0.9`
for a semantics-checked conversion of legacy input.

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

## Voice Defaults and Natural Prosody

Use front matter to keep identity-defining prosody with a logical voice:

```yaml
---
ssmd_version: "0.9"
voice_defaults:
  guest:
    pitch: high
    rate: normal
prosody_transitions:
  enabled: true
  same_voice_only: true
  rate: 450ms
  pitch: 300ms
---
```

A block or inline voice reference inherits these values without changing the formatted
source:

```text
:::{voice="guest"}
Hello.
:::
```

A local attribute overrides only that field. For example, `rate="slow"` keeps the guest
pitch default. Inline annotations and voice blocks use the same logical voice lookup.
Provider bindings do not change the key used by `voice_defaults`.

The natural rate values are `very-slow`, `slow`, `moderate`, `normal`, `brisk`, `fast`,
and `very-fast`, mapped respectively to `65%`, `80%`, `90%`, `100%`, `110%`, `125%`, and
`150%`. Natural pitch values are `very-low`, `low`, `moderate-low`, `normal`,
`moderate-high`, `high`, and `very-high`, mapped to `-20%`, `-12%`, `-6%`, `+0%`, `+6%`,
`+12%`, and `+20%`. Explicit percentages are supported; compact `vrp` is compatibility-only.

Formatting preserves declared attributes and does not materialize inherited defaults.
Use inspection to view both forms:

```bash
ssmd --json inspect episode.ssmd --sentences
```

The JSON sentence view includes `declared_prosody`, `effective_prosody`, and per-field
`sources`.

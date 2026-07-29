# SSMD Specification

Here we specify how Speech Synthesis Markdown (SSMD) works.

SSMD is a lightweight, human-friendly markdown-like syntax for creating SSML (Speech
Synthesis Markup Language) documents. It provides an easier-to-write and more
maintainable alternative to raw XML-based SSML for Text-to-Speech (TTS) applications.

This Python implementation is based on the
[original Ruby SSMD specification](https://github.com/machisuji/ssmd/blob/master/SPECIFICATION.md)
with additional features and enhancements.

## Syntax

SSMD is mapped to SSML using the following rules.

- [Document Header](#document-header)
- [Text](#text)
- [Emphasis](#emphasis)
- [Break](#break)
- [Language](#language)
- [Voice](#voice)
- [Mark](#mark)
- [Paragraph](#paragraph)
- [Heading](#heading)
- [Phoneme](#phoneme)
- [Prosody](#prosody)
- [Say-as](#say-as)
- [Substitution](#substitution)
- [Audio](#audio)
- [Extensions](#extensions)

### Short Taxonomy

| Category   | Meaning                                          |
| ---------- | ------------------------------------------------ |
| Semantic   | Meaning-based hints (say-as, lang, phoneme, sub) |
| Structural | p, s, headings                                   |
| Rendering  | prosody, voice, style                            |
| Control    | breaks, marks                                    |
| Extension  | vendor-specific                                  |

---

### Document Header

An SSMD document MAY begin with YAML front matter. The front matter carries portable
document metadata and rendering defaults that are not spoken as document text.

The opening delimiter MUST be exactly three hyphens on the first line:

```text
---
```

The closing delimiter MUST be either exactly three hyphens or exactly three dots:

```text
---
```

```text
...
```

A line containing four or more hyphens is not an SSMD front-matter delimiter.

Example:

```yaml
---
title: Review podcast

voice_bindings:
  kokoro:
    moderator: af_sarah
    positive: af_bella

pause_defaults:
  enabled: true
  sentence: 250ms
  paragraph: 700ms
  voice_change: 350ms
---
```

The document body begins after the closing delimiter. Processors MUST NOT speak,
convert, or expose front-matter source text as document text.

The YAML root MUST be a mapping. Unknown keys MAY be preserved for applications, but
processors SHOULD report unknown keys as warnings when strict validation is requested.

`title` is a portable document metadata key. When present, it MUST be a string,
including when the value is an empty string. Processors MUST preserve it when formatting
or materializing a document header and MUST NOT include it in spoken text, plain-text
output, or generated SSML speech content.

#### Header precedence

For authoring tools that combine defaults from several sources, effective values use the
following precedence from lowest to highest:

1. processor defaults;
2. user authoring configuration;
3. document header;
4. explicit command-line or API overrides.

A document header is portable document data. A user configuration such as
`~/.config/ssmd/config.yaml` is an authoring facility and is not part of the SSMD
document format.

#### Voice bindings

The optional `voice_bindings` mapping binds logical voice references used in the
document to concrete voice identifiers for one or more providers.

```yaml
---
voice_bindings:
  kokoro:
    moderator: af_sarah
    positive: af_bella
    negative: am_adam
---
```

Its shape is:

```text
voice_bindings:
  PROVIDER:
    VOICE_REFERENCE: CONCRETE_VOICE_ID
```

Provider names, voice references, and concrete voice IDs MUST be non-empty strings.
Matching is case-sensitive.

Only bindings needed by the document SHOULD be embedded. A full local voice inventory
SHOULD remain in user or renderer configuration rather than being copied into every SSMD
document.

A processor that targets provider `P` resolves a `voice` reference `R` as follows:

1. use the explicit command or API binding for `P.R`, when supplied;
2. otherwise use `voice_bindings[P][R]` from the document header;
3. otherwise treat `R` as a concrete provider voice ID;
4. otherwise apply the processor's documented missing-voice policy.

A processor MUST NOT silently change an explicit document binding.

#### Pause defaults

The optional `pause_defaults` mapping defines document-level timing defaults for
renderers:

```yaml
---
pause_defaults:
  enabled: true
  sentence: 250ms
  paragraph: 700ms
  voice_change: 350ms
---
```

Allowed fields:

- `enabled`: Boolean switch for the defaults.
- `sentence`: Default pause after an ordinary sentence boundary.
- `paragraph`: Default pause after a paragraph boundary.
- `voice_change`: Default pause when adjacent spoken content changes voice reference.

Durations use a non-negative number followed by `ms` or `s`:

```text
0ms
250ms
1.5s
2s
```

Negative values and other units are invalid.

Explicit break markers in the SSMD body take precedence over `pause_defaults`. When
several default pause types apply at the same boundary, a renderer SHOULD use the
longest applicable duration rather than adding the durations together.

`pause_defaults` do not insert visible break markers into the SSMD source. A renderer
MAY apply them directly. An SSMD-to-SSML converter MAY materialize them as `<break>`
elements when that behavior is explicitly enabled.

When `enabled` is false, a renderer MUST ignore the timing values.

---

### Text

Any text written is implicitly wrapped in a `<speak>` root element. This will be omitted
in the rest of the examples shown in this section.

Special XML characters (`<`, `>`, `&`, `"`, `'`) are automatically escaped to prevent
XML injection and ensure valid SSML output.

SSMD:

```
text & more
```

SSML:

```xml
<speak>text &amp; more</speak>
```

---

### Emphasis

SSMD supports three levels of emphasis using markdown-like syntax.

SSMD:

```
*moderate emphasis*
**strong emphasis**
~~reduced emphasis~~
[moderate]{emphasis="moderate"}
[strong]{emphasis="strong"}
[reduced]{emphasis="reduced"}
[no emphasis]{emphasis="none"}
```

SSML:

```xml
<emphasis>moderate emphasis</emphasis>
<emphasis level="strong">strong emphasis</emphasis>
<emphasis level="reduced">reduced emphasis</emphasis>
<emphasis level="moderate">moderate emphasis</emphasis>
<emphasis level="strong">strong emphasis</emphasis>
<emphasis level="reduced">reduced emphasis</emphasis>
<emphasis level="none">no emphasis</emphasis>
```

---

### Break

Pauses can be indicated by using `...` followed by a modifier. Several modifications to
the duration are allowed as shown below.

SSMD:

```
Hello ...n     world    (none - no break)
Hello ...w     world    (weak/x-weak break)
Hello ...c     world    (medium break like after a comma)
Hello ...s     world    (strong break like after a sentence)
Hello ...p     world    (extra strong break like after a paragraph)
Hello ...5s    world    (5 second break)
Hello ...100ms world    (100 millisecond break)
Hello ...      world    (literal ellipsis, no break)
```

SSML:

```xml
Hello <break strength="none"/>     world    (none - no break)
Hello <break strength="x-weak"/>     world    (weak/x-weak break)
Hello <break strength="medium"/>     world    (medium break like after a comma)
Hello <break strength="strong"/>     world    (strong break like after a sentence)
Hello <break strength="x-strong"/>     world    (extra strong break like after a paragraph)
Hello <break time="5s"/>    world    (5 second break)
Hello <break time="100ms"/> world    (100 millisecond break)
Hello ...      world    (literal ellipsis, no break)
```

**Important:** Bare `...` without a modifier is preserved as literal ellipsis text, not
converted to a break.

**Break Strength Modifiers:**

- `n` → `strength="none"`
- `w` → `strength="x-weak"`
- `c` → `strength="medium"` (comma)
- `s` → `strength="strong"` (sentence)
- `p` → `strength="x-strong"` (paragraph)

---

### Language

Text passages can be annotated with ISO 639-1 language codes. SSML expects a full BCP-47
code including a country. While you can provide those too, SSMD will use a sensible
default where this is omitted.

SSMD:

```
Ich sah [Guardians of the Galaxy]{lang="en"} im Kino.
Ich sah [Guardians of the Galaxy]{lang="en-GB"} im Kino.
I saw ["Die Häschenschule"]{lang="de"} in the cinema.
[Bonjour]{lang="fr"} tout le monde!

:::{lang="en"}
Hello There!
:::
```

SSML:

```xml
Ich sah <lang xml:lang="en-US">Guardians of the Galaxy</lang> im Kino.
Ich sah <lang xml:lang="en-GB">Guardians of the Galaxy</lang> im Kino.
I saw <lang xml:lang="de-DE">"Die Häschenschule"</lang> in the cinema.
<lang xml:lang="fr-FR">Bonjour</lang> tout le monde!

<lang xml:lang="en-US">Hello There!</lang>
```

**Language Code Expansion:**

- `en` → `en-US`
- `fr` → `fr-FR`
- `de` → `de-DE`
- `es` → `es-ES`
- `it` → `it-IT`
- `ja` → `ja-JP`
- `zh` → `zh-CN`
- `ru` → `ru-RU`

#### Lang Directives (Block Syntax)

For multi language documents:

```
<div lang="en-us">
Welcome to the show! I'm Sarah.
</div>

<div lang="en-gb">
Thanks Sarah! Great to be here.
</div>
```

SSML:

```xml
<lang xml:lang="en-US">
<p>Welcome to the show! I'm Sarah.</p>
</lang>

<lang xml:lang="en-GB">
<p>Thanks Sarah! Great to be here.</p>
</lang>
```

**Directive Syntax Options:**

- `<div lang="language-code">`

Voice directives apply to all text until the next directive or paragraph break.

NOTE: The processor MUST emit a <lang> tag when language is explicitly specified. The
processor MAY omit the tag when targeting engines that do not support language
switching.

Google Cloud TTS ignores nested <lang> changes within a sentence. Processors targeting
Google Cloud SHOULD flatten language scopes.

---

### Voice

SSMD supports two voice syntax styles: inline annotations for short phrases and block
directives for dialogue and multi-speaker scripts.

The value of `voice` is a **voice reference**. A voice reference may be:

- a logical role such as `moderator`, resolved through document `voice_bindings`; or
- a concrete provider voice ID such as `af_sarah` or `en-US-Wavenet-A`.

This interpretation preserves portable logical speaker names while remaining compatible
with existing documents that already use concrete voice IDs.

#### Inline Voice Annotations

For short phrases within a sentence:

SSMD:

```ssmd
[Hello]{voice="moderator"}
[Hello]{voice="en-US-Wavenet-A"}
[Bonjour]{voice-lang="fr-FR" gender="female"}
[Text]{voice-lang="en-GB" gender="male" variant="1"}
```

With this header:

```yaml
---
voice_bindings:
  kokoro:
    moderator: af_sarah
---
```

A Kokoro renderer resolves `moderator` to `af_sarah`. A processor converting to generic
SSML MAY preserve the original reference as the SSML voice name when no provider binding
is selected.

Generic SSML representation:

```xml
<voice name="moderator">Hello</voice>
<voice name="en-US-Wavenet-A">Hello</voice>
<voice language="fr-FR" gender="female">Bonjour</voice>
<voice language="en-GB" gender="male" variant="1">Text</voice>
```

**Voice Attributes:**

- `voice: REFERENCE` - Logical or concrete voice reference.
- `voice-lang: LANG` - Language code, for example `en-US` or `fr-FR`.
- `gender: GENDER` - `male`, `female`, or `neutral`.
- `variant: NUMBER` - Variant number for processor-specific disambiguation.

`voice-lang`, `gender`, and `variant` are selection hints. A processor MAY use them to
select a compatible concrete voice when no explicit `voice` reference is present. A
processor MUST document whether it supports such selection.

#### Voice Directives (Block Syntax)

For dialogue and multi-speaker scripts:

SSMD:

```ssmd
<div voice="moderator">
Welcome to the show.
</div>

<div voice="guest">
Thanks for having me.
</div>

<div voice="narrator" voice-lang="en-GB">
This story takes place in London.
</div>

<div voice-lang="fr-FR" gender="female">
Bonjour tout le monde!
</div>
```

Portable binding header:

```yaml
---
voice_bindings:
  kokoro:
    moderator: af_sarah
    guest: am_adam
    narrator: bf_emma
---
```

Generic SSML representation:

```xml
<voice name="moderator">
<p>Welcome to the show.</p>
</voice>

<voice name="guest">
<p>Thanks for having me.</p>
</voice>

<voice name="narrator" language="en-GB">
<p>This story takes place in London.</p>
</voice>

<voice language="fr-FR" gender="female">
<p>Bonjour tout le monde!</p>
</voice>
```

**Directive Syntax Options:**

- `<div key=value>...</div>`
- supported keys: `voice`, `voice-lang`, `gender`, and `variant`

Voice directives apply to the content enclosed by the directive block.

#### Binding conformance

A binding-aware processor SHOULD report:

- an unresolved logical voice reference;
- a binding target unavailable in the selected provider inventory;
- a disabled target voice;
- a document binding that conflicts with an explicit command override;
- unused bindings, as a warning.

A structural SSMD validator that has no provider inventory MAY validate the binding
shape without verifying that concrete target IDs are installed.

---

### Mark

Sections of text can be tagged using marks. They do not affect the synthesis but can be
returned by SSML processing engines as meta information and to emit events during
processing based on these marks.

SSMD:

```
I always wanted a @animal cat as a pet.
Click @here to continue.
```

SSML:

```xml
I always wanted a <mark name="animal"/> cat as a pet.
Click <mark name="here"/> to continue.
```

---

### Paragraph

Empty lines (two or more consecutive newlines) indicate paragraph boundaries.

SSMD:

```
First prepare the ingredients.
Don't forget to wash them first.

Lastly mix them all together.

Don't forget to do the dishes after!
```

SSML:

```xml
<p>First prepare the ingredients.
Don't forget to wash them first.</p>
<p>Lastly mix them all together.</p>
<p>Don't forget to do the dishes after!</p>
```

---

### Formatting Conventions

SSMD files should follow these formatting rules for readability and consistency.

#### Sentence Boundaries

Each sentence should start on a new line. Sentences end with terminal punctuation (`.`,
`?`, `!`):

```ssmd
First sentence here.
Second sentence here.
Third sentence here?
```

#### Break Markers

Break markers (e.g., `...s`, `...w`, `...p`) indicate pause duration and are **not**
sentence boundaries.

**Mid-sentence breaks** stay inline between text:

```ssmd
I like ...s to sleep.
The meeting ...w lasted ...w three hours.
```

**Sentence-boundary breaks** appear at the end of the line:

```ssmd
First sentence. ...s
Second sentence starts here.
```

**Important:** Break markers like `...s`, `...w`, `...p`, `...500ms` are pause lengths,
not sentence indicators. A sentence ends only with `.`, `?`, or `!`.

#### Paragraphs

Paragraphs are separated by blank lines (double newlines):

```ssmd
First paragraph with multiple sentences.
Another sentence in first paragraph.

Second paragraph starts here.
Still in second paragraph.

Third paragraph.
```

#### Voice Directives

Voice directives appear on their own line with a blank line after:

```ssmd
<div voice="sarah">

Hello! How are you today?
I'm doing great.
</div>

<div voice="michael">
Thanks for asking!
</div>
```

#### Headings

Headings have blank lines before and after:

```ssmd
Previous content here.

# Main Heading

Content after heading starts here.
```

#### Quoted Sentences

When quotes contain multiple sentences, each sentence remains on its own line:

```ssmd
"First quoted sentence.
Second quoted sentence here."
```

---

### Heading

Headings use markdown-style hash marks and can be configured with custom effects.

SSMD:

```
# Main Heading
## Subheading
### Sub-subheading
```

SSML (with default configuration):

```xml
<break time="300ms"/><emphasis level="strong">Main Heading</emphasis><break time="300ms"/>
<break time="75ms"/><emphasis>Subheading</emphasis><break time="75ms"/>
<break time="50ms"/>Sub-subheading<break time="50ms"/>
```

**Configurable Heading Levels:**

Heading effects can be customized in the YAML header:

```yaml
---
heading:
  - level_1:
      pause_before: 300ms
      emphasis: strong
      pause: 300ms
  - level_2:
      pause_before: 75ms
      emphasis: moderate
      pause: 75ms
  - level_3:
      pause_before: 50ms
      rate: slow
      pause: 50ms
---
```

Available effect types:

- `pause_before`: Adds a pause before the heading text is spoken
- `emphasis`: Sets the emphasis level for the heading text
- `pause`: Adds a pause after the heading text is spoken
- `volume`: Adjusts volume for the heading text
- `rate`: Adjusts rate for the heading text
- `pitch`: Adjusts pitch for the heading text

---

### Phoneme

Sometimes the speech synthesis engine needs to be told how exactly to pronounce a word.
This can be done via phonemes using IPA (International Phonetic Alphabet) or X-SAMPA
notation.

SSMD:

```
[tomato]{ph="təˈmeɪtoʊ"}
[tomato]{ipa="təˈmeɪtoʊ"}
The German word ["dich"]{sampa="dIC"} does not sound like dick.
```

SSML:

```xml
<phoneme alphabet="ipa" ph="təˈmeɪtoʊ">tomato</phoneme>
<phoneme alphabet="ipa" ph="təˈmeɪtoʊ">tomato</phoneme>
The German word <phoneme alphabet="ipa" ph="dɪç">"dich"</phoneme> does not sound like dick.
```

**Supported Notations:**

- `ph:` or `ipa:` - IPA notation (recommended)
- `sampa:` - X-SAMPA notation (automatically converted to IPA)

---

### Prosody

The prosody or rhythm depends on the volume, rate, and pitch of the delivered text.

Each of those values can be defined by a number between 0 and 5 (for volume) or 1 and 5
(for rate and pitch) where those mean:

| Number | Volume | Rate   | Pitch  |
| ------ | ------ | ------ | ------ |
| 0      | silent |        |        |
| 1      | x-soft | x-slow | x-low  |
| 2      | soft   | slow   | low    |
| 3      | medium | medium | medium |
| 4      | loud   | fast   | high   |
| 5      | x-loud | x-fast | x-high |

#### Shorthand Notation

SSMD:

```
Volume:

[silent]{volume="silent"}
[silent]{volume="x-soft"}
[silent]{volume="soft"}
[medium]{volume="medium"}
medium
[loud]{volume="loud"}
[x-loud]{volume="x-loud"}

Rate:

[x-slow]{rate="x-slow"}
[slow]{rate="slow"}
[medium]{rate="medium"}
[fast]{rate="fast"}
[x-fast]{rate="xfast"}

Pitch:

[x-low]{pitch="x-low"}
[low]{pitch="low"}
[medium]{pitch="medium"}
[high]{pitch="high"}
[x-high]{pitch="x-high"}
```

SSML:

```xml
Volume:

<prosody volume="silent">silent</prosody>
<prosody volume="x-soft">extra soft</prosody>
<prosody volume="soft">soft</prosody>
<prosody volume="medium">medium</prosody>
medium
<prosody volume="loud">loud</prosody>
<prosody volume="x-loud">extra loud</prosody>

Rate:

<prosody rate="x-slow">extra slow</prosody>
<prosody rate="slow">slow</prosody>
medium
<prosody rate="fast">fast</prosody>
<prosody rate="x-fast">extra fast</prosody>

Pitch:

<prosody pitch="x-low">extra low</prosody>
<prosody pitch="low">low</prosody>
medium
<prosody pitch="high">high</prosody>
<prosody pitch="x-high">extra high</prosody>
```

#### Explicit Notation

SSMD:

```
[extra loud, fast, and high]{vrp="555"}
[extra loud, fast, and high]{v ="5" r="5" p="5"}
[loud and slow]{v="4" r="2"}
```

SSML:

```xml
<prosody volume="x-loud" rate="x-fast" pitch="x-high">extra loud, fast, and high</prosody>
<prosody volume="x-loud" rate="x-fast" pitch="x-high">extra loud, fast, and high</prosody>
<prosody volume="loud" rate="slow">loud and slow</prosody>
```

#### Relative Values

Changes in volume and pitch can also be given explicitly in relative values:

SSMD:

```
[louder]{v="+10dB"}
[quieter]{v="-3dB"}
[faster]{r="+20%"}
[slower]{r="-10%"}
[higher]{p="+15%"}
[lower]{p="-4%"}
```

SSML:

```xml
<prosody volume="+10dB">louder</prosody>
<prosody volume="-3dB">quieter</prosody>
<prosody rate="+20%">faster</prosody>
<prosody rate="-10%">slower</prosody>
<prosody pitch="+15%">higher</prosody>
<prosody pitch="-4%">lower</prosody>
```

#### Directive

SSMD:

```
<div volume="x-loud" rate="x-fast" pitch="x-high">
extra loud, fast, and high
</div>

<div volume="5" rate="5" pitch="5">
extra loud, fast, and high
</div>

<div volume="4" rate="2">
loud and slow
</div>

```

SSML:

```xml
<prosody volume="x-loud" rate="x-fast" pitch="x-high">extra loud, fast, and high</prosody>
<prosody volume="x-loud" rate="x-fast" pitch="x-high">extra loud, fast, and high</prosody>
<prosody volume="loud" rate="slow">loud and slow</prosody>
```

SSMD:

### Say-as

You can give the speech synthesis engine hints as to what it's supposed to read using
`as`.

**Possible values:**

- `character` - spell out each single character, e.g. for KGB
- `cardinal` - cardinal number, e.g. 100
- `ordinal` - ordinal number, e.g. 1st
- `digits` - spell out each single digit, e.g. 123 as 1 - 2 - 3
- `fraction` - pronounce number as fraction, e.g. 3.14
- `unit` - e.g. 1meter
- `date` - read content as a date, must provide format
- `time` - duration in minutes and seconds
- `address` - read as part of an address
- `telephone` - read content as a telephone number
- `expletive` - beeps out the content

SSMD:

```
Today on [31.12.2024]{as="date" format="dd.mm.yyyy"} my
telephone number is [+1-555-0123]{as="telephone"}.
You can't say [damn]{as="expletive"} on television.
[NASA]{as="character"} stands for National Aeronautics and Space Administration.
The [1st]{as="ordinal"} place winner gets a prize.
Call me at [123]{as="digits"} for more info.
```

SSML:

```xml
Today on <say-as interpret-as="date" format="dd.mm.yyyy">31.12.2024</say-as> my
telephone number is <say-as interpret-as="telephone">+1-555-0123</say-as>.
You can't say <say-as interpret-as="expletive">damn</say-as> on television.
<say-as interpret-as="character">NASA</say-as> stands for National Aeronautics and Space Administration.
The <say-as interpret-as="ordinal">1st</say-as> place winner gets a prize.
Call me at <say-as interpret-as="digits">123</say-as> for more info.
```

**Optional Detail Attribute:**

SSMD:

```
[123]{as="cardinal" detail="2"}
[12/31/2024]{as="date" format="mdy" detail="1"}
```

SSML:

```xml
<say-as interpret-as="cardinal" detail="2">123</say-as>
<say-as interpret-as="date" format="mdy" detail="1">12/31/2024</say-as>
```

---

### Substitution

Allows to substitute the pronunciation of a word, such as an acronym, with an alias.

SSMD:

```
I'd like to drink some [H2O]{sub="water"} now.
[AWS]{sub="Amazon Web Services"} provides cloud computing.
[NATO]{sub="North Atlantic Treaty Organization"} was founded in 1949.
```

SSML:

```xml
I'd like to drink some <sub alias="water">H2O</sub> now.
<sub alias="Amazon Web Services">AWS</sub> provides cloud computing.
<sub alias="North Atlantic Treaty Organization">NATO</sub> was founded in 1949.
```

---

### Audio

Audio files can be embedded with optional fallback text and advanced attributes.

#### Basic Audio

SSMD:

```
[doorbell]{src="https://example.com/sounds/bell.mp3"}
[]{src="beep.mp3"}
[cat purring]{src="cat.ogg" alt="Sound file not loaded"}
```

SSML:

```xml
<audio src="https://example.com/sounds/bell.mp3"><desc>doorbell</desc></audio>
<audio src="beep.mp3"></audio>
<audio src="cat.ogg"><desc>cat purring</desc>Sound file not loaded</audio>
```

#### Advanced Audio Attributes

SSMD supports advanced audio control features:

**Clip Audio (Start/End Times):**

```
[music]{src="song.mp3" clip="5s-30s"}
```

**Speed Control:**

```
[announcement]{src="speech.mp3" speed="150%"}
```

**Repeat Count:**

```
[jingle]{src="ad.mp3" repeat="3"}
```

**Volume Adjustment:**

```
[alarm]{src="alert.mp3" level="+6dB"}
```

**Combined Attributes:**

```
[bg music]{src="music.mp3" clip="0s-10s" speed="120%" level="-3dB" alt="Fallback text"}
```

SSML:

```xml
<audio src="song.mp3" clipBegin="5s" clipEnd="30s"><desc>music</desc></audio>
<audio src="speech.mp3" speed="150%"><desc>announcement</desc></audio>
<audio src="ad.mp3" repeatCount="3"><desc>jingle</desc></audio>
<audio src="alert.mp3" soundLevel="+6dB"><desc>alarm</desc></audio>
<audio src="music.mp3" clipBegin="0s" clipEnd="10s" speed="120%" soundLevel="-3dB"><desc>bg music</desc>Fallback text</audio>
```

**Audio Attributes:**

- `clip: START-END` - Clip audio segment (e.g., `5s-30s`)
- `speed: PERCENT` - Playback speed (e.g., `120%`)
- `repeat: COUNT` - Number of repetitions
- `level: DB` - Volume adjustment in decibels (e.g., `+6dB`, `-3dB`)
- `repeatDur: TIME` - Total duration for repetitions (alternative to `repeat`)

---

### Extensions

It must be possible to extend SSML with constructs specific to certain speech synthesis
engines. Registered extensions must have a unique name and can take parameters.

#### Amazon Polly Extensions

SSMD supports Amazon Polly-specific features:

SSMD:

```
[whispered text]{ext="whisper"}
[announcement with dynamic range compression]{ext="drc"}
```

SSML:

```xml
<amazon:effect name="whispered">whispered text</amazon:effect>
<amazon:effect name="drc">announcement with dynamic range compression</amazon:effect>
```

#### Google Cloud TTS Extensions

Speaking styles for Google Cloud TTS can be configured in the YAML-Header:

```yaml
---
extensions:
  - cheerful:
      value: '<google:style name="cheerful">{text}</google:style>'
  - calm:
      value: '<google:style name="calm">{text}</google:style>'
  - empathetic:
      value: '<google:style name="empathetic">{text}</google:style>'
---
```

SSMD:

```
[Welcome!]{ext="cheerful"}
[I understand.]{ext="empathetic"}
```

SSML:

```xml
<google:style name="cheerful">Welcome!</google:style>
<google:style name="empathetic">I understand.</google:style>
```

**Available Google TTS Styles:**

- `cheerful` - Upbeat and positive
- `calm` - Relaxed and soothing
- `empathetic` - Understanding and compassionate
- `apologetic` - Sorry and regretful
- `firm` - Confident and authoritative
- `news` - Professional news anchor
- `conversational` - Natural conversation

#### Custom Extensions

Extensions can be registered via YAML configuration:

```yaml
---
extensions:
  - whisper:
      value: '<amazon:effect name="whispered">{text}</amazon:effect>'
  - robotic:
      value: '<voice-transformation type="robot">{text}</voice-transformation>'
---
```

---

### Annotation Attributes

Attribute values can be wrapped in single or double quotes. Multiple attributes are
space-separated inside `{}` blocks. Keys may contain letters, digits, underscores,
hyphens, and colons.

Offsets returned by `parse_spans()` are computed against the final clean text with
markup removed.

### Combining Annotations

Multiple annotations can be comma-separated to combine effects:

SSMD:

```
[Bonjour]{lang="fr" v="5" r="2"}
[important]{v="5" as="character"}
[Hello]{voice="Joanna", v="4" r="3"}
```

SSML:

```xml
<lang xml:lang="fr-FR"><prosody volume="x-loud" rate="slow">Bonjour</prosody></lang>
<prosody volume="x-loud"><say-as interpret-as="character">important</say-as></prosody>
<voice name="Joanna"><prosody volume="loud" rate="medium">Hello</prosody></voice>
```

---

### Nesting and Duplicate Annotations

Formats can be nested. Duplicate annotations of the same type use the first occurrence
(leftmost takes precedence).

SSMD:

```
Der Film [Guardians of the *Galaxy*]{lang="en-GB"} ist ganz
[okay]{lang="en-US"}.
[*very* **important**]{v="5"}
```

SSML:

```xml
Der Film <lang xml:lang="en-GB">Guardians of the <emphasis>Galaxy</emphasis></lang> ist ganz <lang xml:lang="en-US">okay</lang>.
<prosody volume="x-loud"><emphasis>very</emphasis> <emphasis level="strong">important</emphasis></prosody>
```

In the second example, both emphasis styles are preserved within the volume prosody.

---

## Additional Features

### TTS Engine Capabilities

SSMD supports automatic feature filtering based on TTS engine capabilities. This ensures
that only supported features are included in the generated SSML.

**Available Capability Presets:**

- `minimal` - Plain text only (no SSML features)
- `pyttsx3` - Basic prosody only (volume, rate)
- `espeak` - Breaks, language, prosody, phonemes
- `google` / `azure` / `microsoft` - Full SSML support
- `polly` / `amazon` - Full support + Amazon extensions
- `full` - All features enabled (default)

**Usage:**

```python
from ssmd import Document

doc = Document("*Hello* [world]{lang='fr'}!", capabilities='espeak')
ssml = doc.to_ssml()
# eSpeak doesn't support emphasis or language
# Output: <speak>Hello world!</speak>
```

**Custom Capabilities:**

```python
from ssmd import TTSCapabilities

caps = TTSCapabilities(
    emphasis=False,
    break_tags=True,
    paragraph=True,
    language=False,
    prosody=True,
    prosody_volume=True,
    prosody_rate=True,
    prosody_pitch=False,
    say_as=False,
    audio=False,
    mark=False,
)

doc = Document("*Hello* world!", capabilities=caps)
```

### Sentence Detection

SSMD provides two modes for sentence detection:

1. **Regex Mode (Default):** Fast pattern-based splitting (~60x faster, works
   out-of-the-box)
2. **spaCy Mode (Optional):** ML-powered detection (~95-99% accuracy, requires
   `pip install ssmd[nlp]`)

**Usage:**

```python
from ssmd import parse_sentences

# Fast regex mode (default)
sentences = parse_sentences(text, use_spacy=False)

# ML-powered mode (higher accuracy)
sentences = parse_sentences(text, use_spacy=True, model_size='md')
```

### Bidirectional Conversion

SSMD supports conversion in both directions:

**SSMD → SSML:**

```python
import ssmd
ssml = ssmd.to_ssml("Hello *world*!")
```

**SSML → SSMD:**

```python
ssmd_text = ssmd.from_ssml('<speak><emphasis>Hello</emphasis></speak>')
# Output: "*Hello*"
```

**Strip to Plain Text:**

```python
text = ssmd.to_text("Hello *world* @marker!")
# Output: "Hello world!"
```

### Document API

The Document API provides incremental building and streaming:

```python
from ssmd import Document

doc = Document()
doc.add_sentence("Hello *world*!")
doc.add_sentence("This is great.")
doc.add_paragraph("New paragraph.")

# Export
ssml = doc.to_ssml()
text = doc.to_text()

# Stream sentences for real-time TTS
for sentence in doc.sentences():
    tts_engine.speak(sentence)
```

### Parser API

Extract structured data without generating SSML:

```python
from ssmd import parse_sentences

sentences = parse_sentences("Hello *world*!")
for sent in sentences:
    for seg in sent.segments:
        print(f"Text: {seg.text}")
        print(f"Emphasis: {seg.emphasis}")
        print(f"Prosody: {seg.prosody}")
```

**Available Data Structures:**

- `SSMDSegment` - Individual text segments with markup
- `SSMDSentence` - Sentences containing segments
- `VoiceAttrs` - Voice configuration
- `ProsodyAttrs` - Volume, rate, pitch settings
- `BreakAttrs` - Pause configuration
- `SayAsAttrs` - Text interpretation hints
- `AudioAttrs` - Audio file metadata

---

## Processing Rules

### Processing Pipeline Order

The converter applies processors in this order:

1. **XML Escaping** - Escape special characters
2. **Directives** - Process `<div>` blocks
3. **Emphasis** - Process `*`, `**`, `_` markers
4. **Annotations** - Process `[text]{key=value}` patterns
5. **Marks** - Process `@marker` patterns
6. **Headings** - Process `#` markers
7. **Paragraphs** - Process blank line separators
8. **Sentences** - Optionally wrap in `<s>` tags
9. **Breaks** - Process `...` patterns
10. **Output Formatting** - Wrap in `<speak>`, optional pretty-print

### Annotation Priority

When processing `[text]{key=value}` patterns, annotations are detected in this priority
order:

1. Audio (URL patterns)
2. Extensions (`ext: name`)
3. Emphasis (`emphasis: level`)
4. Voice (`voice: ...`)
5. Say-As (`as: type`)
6. Phonemes (`ph:`, `ipa:`, `sampa:`)
7. Prosody (`vrp:`, `v:`, `r:`, `p:`)
8. Substitution (`sub: alias`)
9. Language (ISO codes)

### Security

All user input is automatically sanitized to prevent XML injection:

- Special characters in text and attributes are escaped
- Output is always valid, well-formed XML
- Safe to use with untrusted input

---

## Differences from Standard Markdown

5. **Markers** - `@marker` syntax for event synchronization

---

## Implementation Notes

- **Language:** Python 3.10+
- **Dependencies:** `phrasplit>=0.3.3` (required), `phrasplit[nlp]>=0.3.3` (optional for
  spaCy)
- **Type Safety:** Full mypy type checking support
- **Performance:** Regex mode is ~60x faster than spaCy; spaCy provides ~95-99% accuracy
- **License:** MIT (Apache for some components)

---

## Document Metadata Conformance

A conforming SSMD parser:

1. recognizes valid YAML front matter at the start of a document;
2. excludes front matter from spoken and clean document text;
3. exposes the parsed mapping to applications;
4. preserves unknown metadata when rewriting a document where practical;
5. validates `voice_bindings` and `pause_defaults` when strict validation is requested.

A conforming binding-aware renderer:

1. selects the provider mapping matching its backend;
2. resolves logical voice references according to the precedence in this specification;
3. reports unresolved references according to an explicit missing-voice policy;
4. applies enabled pause defaults without adding duplicate pauses;
5. gives explicit source break markers precedence over header defaults.

A processor that does not implement voice binding or pause defaults MAY preserve those
header fields unchanged, but MUST NOT speak them as text.

## Related Projects

- [SSMD (Ruby)](https://github.com/machisuji/ssmd) - Original reference implementation
- [SSMD (JavaScript)](https://github.com/fabien88/ssmd) - JavaScript implementation
- [Speech Markdown](https://www.speechmarkdown.org/) - Alternative specification

---

## Version

This specification describes the Python SSMD implementation and is based on the original
Ruby SSMD specification with additional features including:

- Heading support
- Advanced audio attributes
- TTS engine capability filtering
- Bidirectional SSMD ↔ SSML conversion
- Parser API for structured data extraction
- Document API for incremental building
- Sentence detection with spaCy integration

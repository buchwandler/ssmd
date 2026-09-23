# TTS Engine Capabilities

Capability presets describe which features SSMD's renderer can emit for a target. They
do not guarantee that a particular service, voice, or endpoint accepts every SSML
feature. For strict 0.9 documents, select `target="provider"` and an explicit
`loss_policy`; unsupported semantics produce diagnostics or fail according to that
policy.

## Why Capabilities Matter

TTS services differ in their supported SSML subsets and provider extensions:

- Basic engines often support only a small subset.
- Cloud services support broader but service- and voice-dependent subsets.
- Custom engines may have unique limitations.

A provider rendering can adapt unsupported features only under a non-error loss policy.
Review `Document.render_diagnostics` before sending output to the engine.

## Using Capability Presets

The preset selects a renderer capability profile. For a strict 0.9 document, pass an
explicit provider target and loss policy, then inspect the reported diagnostics:

```python
from ssmd import Document

source = '''---
ssmd_version: "0.9"
---
*Hello* [world]{lang="fr"}!'''
doc = Document(source, capabilities='espeak')
ssml = doc.to_ssml(target="provider", loss_policy="warn")
diagnostics = doc.render_diagnostics
```

### Available Presets

The lists describe built-in preset flags, not universal service guarantees. They affect
output only when the `provider` target is selected; generic rendering uses portable
mappings. Use an explicit loss policy and inspect diagnostics when provider adaptation
is requested.

#### minimal

No optional renderer feature flags are enabled:

```python
doc = Document(capabilities='minimal')
```

**Supported:** No optional feature flags. With the default `loss_policy="error"`,
unsupported semantics fail conversion; explicit `warn` or `drop` policies are required
for lossy reduction.

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

The built-in cloud presets cover common features. Actual service, endpoint, region, and
voice support varies, so check the vendor's SSML documentation:

```python
doc = Document(capabilities='google')
# or
doc = Document(capabilities='azure')
```

**Enabled by these built-in presets:** commonly supported standard SSML features. This
is not a guarantee that every service or voice supports every mapping.

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

The `polly` preset enables the renderer's configured Amazon mappings and extensions.
Verify actual support against the selected Polly engine and voice; this preset is not a
universal feature guarantee.

#### full

All renderer capability flags are enabled, so this preset performs no capability
filtering. It does not imply that an external TTS engine supports every emitted feature:

```python
doc = Document(capabilities='full')
```

Use this only when the target is known to support all emitted features or for testing.

## Capability Profiles and Linting

Profiles describe which SSMD tags and attributes are supported without mutating output.
Use them to validate input before conversion:

```python
from ssmd import get_profile, list_profiles, lint

profiles = list_profiles()
profile = get_profile("ssmd-core")
source = '''---
ssmd_version: "0.9"
---
[Hello]{volume="loud"}'''
issues = lint(source, profile="ssmd-core")
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

source = '''---
ssmd_version: "0.9"
---
[text]{volume="loud" rate="fast" pitch="high"}'''
doc = Document(source, capabilities=caps)
ssml = doc.to_ssml(target="provider", loss_policy="warn")
diagnostics = doc.render_diagnostics
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

source = '''---
ssmd_version: "0.9"
---
[secret]{ext="whisper"}'''
doc = Document(source, capabilities=caps)
ssml = doc.to_ssml(target="provider", loss_policy="error")
```

## Provider Adaptation

Use `target="provider"` to apply a capability preset. Provider adaptation is explicit;
unsupported semantics fail by default. Choose `warn` or `drop` only when lossy output is
acceptable, and inspect the returned diagnostics.

```python
from ssmd import Document

source = '''---
ssmd_version: "0.9"
---
# Welcome
*Hello* world! ...500ms
[Bonjour]{lang="fr"} everyone!
This is [loud]{volume="loud"}.'''
doc = Document(source, capabilities="espeak")
ssml = doc.to_ssml(target="provider", loss_policy="warn")
diagnostics = doc.render_diagnostics
```

`target="generic"` emits portable SSML and does not apply provider-specific capability
adaptation. It may still reject semantics that cannot be represented by the selected
rendering contract.

## Streaming with Capabilities

Apply the target and loss policy to each streamed document, then inspect its diagnostics
before sending it to the TTS engine:

```python
for sentence_doc in doc.sentences(as_documents=True):
    ssml = sentence_doc.to_ssml(target="provider", loss_policy="warn")
    diagnostics = sentence_doc.render_diagnostics
    tts_engine.speak(ssml)
```

## Comparing Capability Presets

```python
for preset in ("minimal", "pyttsx3", "espeak", "google", "polly"):
    doc = Document(source, capabilities=preset)
    ssml = doc.to_ssml(target="provider", loss_policy="warn")
    print(preset, ssml, doc.render_diagnostics)
```

The output and diagnostics depend on the preset. Check them against the selected
service, region, and voice; a preset is not a guarantee that the external endpoint
accepts every feature.

## Loss Policies

- `error` (the default) refuses a conversion when provider adaptation would lose
  semantics.
- `warn` returns adapted SSML with warning diagnostics.
- `drop` returns adapted SSML with informational diagnostics.

Text and nested markup are handled according to the selected policy. Do not treat
stripped markup as a successful conversion unless the associated diagnostics are
reviewed.

## Best Practices

1. Select the SSML target explicitly when its contract matters.
2. Use the capability preset for the intended provider and inspect diagnostics.
3. Verify generated SSML against the actual service and voice.
4. Use `error` unless the application explicitly accepts lossy adaptation.
5. Keep a generic rendering path when portable SSML is required.

## Integration Example

```python
from ssmd import Document

def render_for_provider(source: str, provider: str) -> tuple[str, list]:
    doc = Document(source, capabilities=provider)
    ssml = doc.to_ssml(target="provider", loss_policy="error")
    return ssml, doc.render_diagnostics
```

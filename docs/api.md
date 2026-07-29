# API Reference

This page documents the public API of the SSMD library.

## Core Classes

### Document

The primary class for creating and managing SSMD/SSML documents.

:::{autoclass} ssmd.Document :members: :undoc-members: :show-inheritance: :::

**Construction Methods:**

:::{automethod} ssmd.Document.**init** :::

:::{automethod} ssmd.Document.from_ssml :::

:::{automethod} ssmd.Document.from_text :::

**Building Methods:**

:::{automethod} ssmd.Document.add :::

:::{automethod} ssmd.Document.add_sentence :::

:::{automethod} ssmd.Document.add_paragraph :::

**Export Methods:**

:::{automethod} ssmd.Document.to_ssml :::

:::{automethod} ssmd.Document.to_ssmd :::

:::{automethod} ssmd.Document.to_text :::

**Properties:**

:::{autoproperty} ssmd.Document.ssmd :::

:::{autoproperty} ssmd.Document.config :::

:::{autoproperty} ssmd.Document.capabilities :::

:::{autoproperty} ssmd.Document.source :::

:::{autoproperty} ssmd.Document.voice_bindings :::

:::{autoproperty} ssmd.Document.pause_defaults :::

`Document` parses YAML front matter by default. `doc.ssmd` is the body-only SSMD;
`doc.source` and `doc.to_ssmd(include_header=True)` include a deterministic header when
one was present. Pass `parse_yaml_header=False` when literal leading front matter syntax
is required.

**Iteration:**

:::{automethod} ssmd.Document.sentences :::

:::{automethod} ssmd.Document.**iter** :::

:::{automethod} ssmd.Document.**len** :::

**List-like Interface:**

:::{automethod} ssmd.Document.**getitem** :::

:::{automethod} ssmd.Document.**setitem** :::

:::{automethod} ssmd.Document.**delitem** :::

:::{automethod} ssmd.Document.**iadd** :::

**Editing Methods:**

:::{automethod} ssmd.Document.insert :::

:::{automethod} ssmd.Document.remove :::

:::{automethod} ssmd.Document.clear :::

:::{automethod} ssmd.Document.replace :::

**Advanced Methods:**

:::{automethod} ssmd.Document.merge :::

:::{automethod} ssmd.Document.split :::

:::{automethod} ssmd.Document.get_fragment :::

### TTSCapabilities

Define TTS engine capabilities for automatic feature filtering.

:::{autoclass} ssmd.TTSCapabilities :members: :undoc-members: :show-inheritance: :::

### SSMLParser

Parse SSML and convert to SSMD format.

:::{autoclass} ssmd.SSMLParser :members: :undoc-members: :show-inheritance: :::

## Convenience Functions

### Parser Functions

Extract structured data from SSMD text.

:::{autofunction} ssmd.parse_paragraphs :::

:::{autofunction} ssmd.parse_sentences :::

:::{autofunction} ssmd.parse_segments :::

:::{autofunction} ssmd.parse_voice_blocks :::

:::{autofunction} ssmd.parse_spans :::

:::{autofunction} ssmd.iter_sentences_spans :::

:::{autofunction} ssmd.lint :::

### Conversion Functions

Convert between SSMD, SSML, and plain text.

#### to_ssml

Convert SSMD markup to SSML.

:::{autofunction} ssmd.to_ssml :::

#### to_text

Convert SSMD to plain text (strips all markup).

:::{autofunction} ssmd.to_text :::

#### from_ssml

Convert SSML back to SSMD format.

:::{autofunction} ssmd.from_ssml :::

## Parser Data Structures

### Sentence (alias: SSMDSentence)

Represents a sentence with voice context and segments.

:::{autoclass} ssmd.Sentence :members: :undoc-members: :show-inheritance: :::

### Segment (alias: SSMDSegment)

Represents a text segment with metadata.

:::{autoclass} ssmd.Segment :members: :undoc-members: :show-inheritance: :::

### VoiceAttrs

Voice configuration attributes.

:::{autoclass} ssmd.VoiceAttrs :members: :undoc-members: :show-inheritance: :::

### ProsodyAttrs

Prosody (volume, rate, pitch) attributes.

:::{autoclass} ssmd.ProsodyAttrs :members: :undoc-members: :show-inheritance: :::

### BreakAttrs

Pause/break attributes.

:::{autoclass} ssmd.BreakAttrs :members: :undoc-members: :show-inheritance: :::

### SayAsAttrs

Say-as interpretation attributes.

:::{autoclass} ssmd.SayAsAttrs :members: :undoc-members: :show-inheritance: :::

### PhonemeAttrs

Phonetic pronunciation attributes.

:::{autoclass} ssmd.PhonemeAttrs :members: :undoc-members: :show-inheritance: :::

### AudioAttrs

Audio file attributes.

:::{autoclass} ssmd.AudioAttrs :members: :undoc-members: :show-inheritance: :::

## Capability Presets

Pre-configured capability sets for common TTS engines.

:::{autodata} ssmd.MINIMAL_CAPABILITIES :::

:::{autodata} ssmd.PYTTSX3_CAPABILITIES :::

:::{autodata} ssmd.ESPEAK_CAPABILITIES :::

:::{autodata} ssmd.GOOGLE_TTS_CAPABILITIES :::

:::{autodata} ssmd.AZURE_TTS_CAPABILITIES :::

:::{autodata} ssmd.AMAZON_POLLY_CAPABILITIES :::

:::{autodata} ssmd.FULL_CAPABILITIES :::

:::{autofunction} ssmd.get_preset :::

## Internal Modules

### SSML Parser

Internal SSML to SSMD parsing engine.

:::{automodule} ssmd.ssml_parser :members: :undoc-members: :show-inheritance: :::

### Document Module

Document container implementation.

:::{automodule} ssmd.document :members: :undoc-members: :show-inheritance: :::

### Parser Module

SSMD parsing functions for extracting structured data.

:::{automodule} ssmd.parser :members: :undoc-members: :show-inheritance: :::

### Segment Module

Segment class for representing text portions with attributes.

:::{automodule} ssmd.segment :members: :undoc-members: :show-inheritance: :::

### Sentence Module

Sentence class for representing collections of segments.

:::{automodule} ssmd.sentence :members: :undoc-members: :show-inheritance: :::

### Types Module

Data types used throughout the SSMD library.

:::{automodule} ssmd.types :members: :undoc-members: :show-inheritance: :::

### Utilities

Helper functions for SSML processing.

:::{automodule} ssmd.utils :members: :undoc-members: :show-inheritance: :::

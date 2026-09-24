# Parser API

SSMD exposes two parser surfaces for different input dialects. Use the sentence-neutral
structural parser for strict 0.9 documents. Sentence- and segment-oriented convenience
helpers are retained for unversioned legacy input and SSMD 0.8 compatibility; they are
not a strict 0.9 API.

## Strict SSMD 0.9 structural parser

`parse_structure()` is the native parser for strict 0.9. It parses document structure
without sentence detection and returns clean text, annotations, structural events, front
matter, and source-aware diagnostics.

```python
from ssmd.parser import parse_structure

source = """\
---
ssmd_version: '0.9'
---
:::{voice="host" voice-languages="en-US"}
One.
:::
:::{voice="guest" voice-languages="en-US"}
Two.
:::
"""
structure = parse_structure(source, dialect="0.9")

assert structure.clean_text == "One. Two."
assert not any(event.kind == "paragraph" for event in structure.events)
print(structure.annotations)
print(structure.events)
print(structure.header)
print(structure.diagnostics)
```

The adjacent voice directives above are tight siblings: their scopes remain separate,
but the speaker change does not create a paragraph boundary or pause. Put a blank line
between sibling directives to create a paragraph event. This rule applies only to
adjacent directive siblings; blank-line behavior for other block-node pairs is
unchanged. The canonical formatter preserves tight and loose spacing, including inside
nested directives.

`ParseStructureResult` exposes:

- `clean_text`: text with SSMD markup removed.
- `annotations`: `AnnotationSpan` values with half-open offsets into `clean_text`.
- `effective_annotations`: annotations after supported inherited defaults are resolved.
- `events`: zero-width break, mark, heading, and paragraph events. Their positions are
  clean-text boundary coordinates.
- `header`: parsed YAML front matter, excluded from `clean_text`.
- `diagnostics` and `warnings`: source-aware syntax and metadata feedback.

Paragraph events describe structure; they do not assign a pause duration. Break events
expose a `time` or semantic `strength`; mark events expose their stable `name`.
Clean-text offsets and source offsets are separate coordinate systems.

Use the strict dialect explicitly in API code, or declare `ssmd_version: '0.9'` and
allow `auto` to select it:

```python
parsed = parse_structure(source, dialect="0.9")
for span in parsed.annotations:
    annotated_text = parsed.clean_text[span.char_start : span.char_end]
    print(annotated_text, span.attrs)
```

The parser does not detect languages, normalize written text into spoken form,
phonemize, or split sentences. A downstream pipeline can normalize `clean_text`, remap
annotation offsets, and then perform its own sentence segmentation. `ssmd.to_ssml()`
accepts explicit sentence spans when that caller-owned segmentation should determine
rendering boundaries.

`parse_spans()` is a lighter-weight API for clean text and annotation ranges when
structural events and front matter are not needed. See [Span API](spans.md) for details.

### Strict lint

Use `lint()` or the CLI to validate strict syntax and profile compatibility:

```python
from ssmd.parser import lint

issues = lint(source, dialect="0.9")
for issue in issues:
    print(issue.severity, issue.code, issue.message)
```

## Legacy 0.8 sentence and segment APIs

`parse_paragraphs()`, `parse_sentences()`, `parse_segments()`, and
`parse_voice_blocks()` are compatibility helpers for unversioned legacy input and the
explicit 0.8 dialect. They produce sentence/segment model objects and may invoke
sentence detection. Do not pass a strict 0.9 document to these APIs; use
`parse_structure()` instead. Strict 0.9 `Document` objects also reject sentence/list
operations such as `len(document)`, indexing, and `.sentences()`.

The following raw `<div>` example is intentionally legacy 0.8 compatibility input, not
recommended 0.9 authoring syntax:

```text
<div voice="sarah">
Hello from Sarah.
</div>

<div voice="michael">
Hello from Michael.
</div>
```

A legacy consumer may process that input with the compatibility sentence API:

```python
from ssmd import parse_sentences

for sentence in parse_sentences(legacy_source):
    voice = sentence.voice.name if sentence.voice else "default"
    text = "".join(segment.text for segment in sentence.segments)
    print(f"[{voice}] {text}")
```

### Legacy function reference

```{autofunction} ssmd.parse_paragraphs

```

```{autofunction} ssmd.parse_sentences

```

```{autofunction} ssmd.parse_segments

```

```{autofunction} ssmd.parse_voice_blocks

```

Sentence detection options such as `use_spacy`, `model_size`, and `spacy_model` apply to
the legacy sentence-oriented helpers. `use_spacy=False` selects the fast regex splitter;
default selection uses the configured phrasplit behavior. These options do not change
the structural 0.9 grammar or make strict 0.9 parsing sentence-based.

See [API Reference](api.md) for legacy `Paragraph`, `Sentence`, `Segment`, and attribute
data structures, and [Examples](examples.md) for a clearly labeled compatibility
snippet.

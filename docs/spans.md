# Spans

SSMD spans report offsets in the cleaned text returned by `parse_spans`. The coordinate
system matches `ParseSpansResult.clean_text` after markup is removed and placeholders
are unescaped.

## TTS pipeline integration

Use `parse_spans()` as the primary integration boundary when another TTS pipeline
prepares and segments text:

```text
SSMD parse -> semantic preparation/normalization -> sentence splitting -> G2P
```

```python
parsed = ssmd.parse_spans(source)
# Pass parsed.clean_text and parsed.annotations to the downstream normalizer.
```

`parse_spans()` performs structural parsing only. It does not expand numbers or
abbreviations, infer a document language, phonemize text, or run sentence detection.
Annotation offsets refer to structural `clean_text`; after normalization changes text
length, the orchestrator remaps those offsets. Phoneme (`ph`/`ipa`) annotations expose
exact source ranges that can be passed to the normalizer as protected spans.

## Structure-only parsing

`parse_structure()` is the sentence-neutral companion to `parse_spans()`. It returns the
same clean-text and annotation concepts plus zero-width `StructuralEvent` values for
breaks, marks, and paragraph boundaries:

```python
parsed = ssmd.parse_structure("Hello ...500ms @chapter world")
assert parsed.clean_text == "Hello world"
assert parsed.events[0].pos == 5  # a boundary, not the last character index
```

Events and annotations are calculated in the returned clean-text coordinate system.
Events use `anchor="before"` for content that follows the boundary and `anchor="after"`
for content that precedes it. Break attributes use `time` or semantic `strength`; mark
attributes use `name`. Final breaks and marks are flushed rather than discarded.
Paragraph events are structural and carry no pause duration.

The result also exposes YAML front matter as `header`, separately from `clean_text`.
`parse_structure()` does not detect language, normalize written language into spoken
language, phonemize, or invoke sentence detection. Those operations remain owned by the
downstream consumer.

## Coordinate system

- Offsets refer to character indices in `clean_text` only.
- Markup like `*`, `[text]{...}`, and `<div ...>` is removed before offsets are
  computed.
- Escaping via `escape_ssmd_syntax()` is reversible but not length-preserving; do not
  use offsets from escaped text.

## Examples

```python
import ssmd

result = ssmd.parse_spans("Hello [world]{lang='en'}")
print(result.clean_text)  # "Hello world"
print(result.annotations[0])
```

## Sentence offsets

Use `iter_sentences_spans()` to align sentence text with `clean_text`:

```python
for sentence, start, end in ssmd.iter_sentences_spans("Hello *world*. Next."):
    print(sentence, start, end)
```

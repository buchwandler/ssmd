# Spans

SSMD spans report offsets in the cleaned text returned by `parse_spans`. The coordinate
system matches `ParseSpansResult.clean_text` after markup is removed and placeholders
are unescaped.

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

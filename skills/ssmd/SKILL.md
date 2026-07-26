---
name: ssmd
description: Create, validate, format, inspect, and convert Speech Synthesis Markdown files with the ssmd CLI. Use this skill for narrated documents, TTS scripts, multi-speaker podcasts, and SSMD-to-SSML delivery.
---

# SSMD Skill

Use this skill when the requested deliverable is an SSMD document, a narrated script,
a multi-speaker podcast, or an SSML conversion produced from SSMD.

The `skills/` directory is repository tooling. It is deliberately outside the Python
package and must not be moved under `ssmd/` or added to package-data configuration.

## Required shipping gate

An SSMD file is complete only after the installed CLI has created it and a second lint
pass has succeeded.

1. Draft the content in a temporary `.ssmd` file.
2. Run `ssmd create` to format, validate, round-trip check, and atomically write the
   requested output.
3. Run `ssmd lint --roundtrip --fail-on-warn` against the written output.
4. When SSML is requested, run `ssmd to-ssml` only after the SSMD gate passes.
5. Report the exact output path and validation commands used.

Do not claim validity based on visual inspection alone.

## Standard workflow

Set the requested output path and keep the draft separate from the final file.

```bash
output="output.ssmd"
draft="$(mktemp "${TMPDIR:-/tmp}/ssmd-draft.XXXXXX.ssmd")"

cat > "$draft" <<'SSMD'
# Title

Hello *world*!
SSMD

ssmd create "$draft" -o "$output" --fail-on-warn
ssmd lint "$output" --roundtrip --fail-on-warn
```

When replacing an existing output intentionally, add `--force` to `ssmd create`.
Never delete or truncate an existing target before validation.

For YAML front matter, pass `--parse-yaml-header` to both commands:

```bash
ssmd create "$draft" -o "$output" --parse-yaml-header --fail-on-warn
ssmd lint "$output" --parse-yaml-header --roundtrip --fail-on-warn
```

For a known TTS target, use the same capability preset during creation, validation, and
conversion:

```bash
ssmd create "$draft" -o "$output"   --capabilities google --fail-on-warn
ssmd lint "$output"   --capabilities google --roundtrip --fail-on-warn
ssmd to-ssml "$output"   --capabilities google -o output.ssml
```

Use `ssmd profiles` to discover valid profile and capability names. Do not guess a
preset name.

## Authoring rules

Prefer `.ssmd` for standalone documents. Use UTF-8 and ordinary LF line endings.

Use simple, explicit SSMD syntax:

```text
*moderate emphasis*
**strong emphasis**
~~reduced emphasis~~
...500ms
...2s
[Bonjour]{lang="fr"}
[H2O]{sub="water"}
[123]{as="cardinal"}
[term]{ipa="tɜːm"}
@marker
```

A bare `...` is ordinary ellipsis text. Timed pauses need a unit such as `...500ms` or
`...2s`.

Keep annotation braces balanced. Quote attribute values. Avoid inventing unsupported
keys; validate any unfamiliar syntax against `SPECIFICATION.md` and the CLI.

## Multi-speaker podcast pattern

Use voice directives for sustained dialogue. Give every speaker a stable voice name.

```ssmd
# Episode title

<div voice="moderator">
Welcome to the discussion.
</div>

<div voice="positive">
The strongest benefit is easier validation.
</div>

<div voice="critical">
The tradeoff is another command and more tests to maintain.
</div>
```

For the common three-speaker review format:

- `moderator` introduces the topic, asks questions, and summarizes.
- `positive` argues for the benefits and practical value.
- `critical` challenges assumptions, identifies costs, and proposes safeguards.

Alternate speakers frequently enough to sound conversational. Keep each block focused
on one argument. For the current SSML→SSMD round-trip implementation, keep **one sentence
per voice directive**; long multi-sentence voice blocks may be rewritten into mixed
inline/directive syntax and fail the semantic round-trip gate. Use pauses sparingly;
speaker boundaries already provide structure.

## Length-controlled documents

For a requested word count, measure rendered plain text rather than SSMD markup:

```bash
ssmd text output.ssmd | python -c   'import sys; print(len(sys.stdin.read().split()))'
```

Treat “around 1000 words” as approximately 900–1100 rendered words unless the user
specifies a tighter range.

## Inspection and debugging

Use JSON diagnostics when a document fails:

```bash
ssmd lint draft.ssmd --roundtrip --fail-on-warn --format json
ssmd inspect draft.ssmd --spans
ssmd inspect draft.ssmd --sentences
ssmd inspect draft.ssmd --paragraphs
```

Correct the source, then rerun `ssmd create`. Do not bypass a syntax error with
`--no-roundtrip`. That option is only for workflows that intentionally accept a known
conversion normalization and still pass normal lint/XML validation.

To check formatting without modifying a file:

```bash
ssmd fmt draft.ssmd --check
```

`--write` and `--check` are mutually exclusive.

## Conversion outputs

Generate derivative formats from the validated SSMD source:

```bash
ssmd to-ssml output.ssmd -o output.ssml
ssmd text output.ssmd -o output.txt
```

For capability-filtered plain text:

```bash
ssmd text output.ssmd --capabilities minimal -o output.txt
```

Keep the validated `.ssmd` file as the source of truth unless the user requests only a
different format.

## Failure handling

Exit code `1` means validation failed. Exit code `2` means invalid usage, input/output
failure, or an unknown profile/preset. Exit code `3` means an unexpected conversion or
parser failure.

On any nonzero exit:

1. Do not present the target file as complete.
2. Preserve the draft and diagnostics.
3. Fix the reported issue.
4. Repeat the complete shipping gate.

If the CLI executable is unavailable, try `python -m ssmd` with the same subcommand.
Do not replace CLI validation with ad hoc Python parsing.

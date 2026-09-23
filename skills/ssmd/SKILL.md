---
name: ssmd
description:
  Create, validate, format, inspect, and convert Speech Synthesis Markdown files with a
  JSON-capable SSMD CLI
license: MIT
compatibility: opencode
metadata:
  audience: coding-agents
  workflow: speech-synthesis-authoring
---

# SSMD Skill

Use this skill when the requested deliverable is an SSMD document, a narrated script, a
multi-speaker podcast, or an SSML conversion produced from SSMD.

The `skills/` directory is repository tooling. It is deliberately outside the Python
package and must not be moved under `ssmd/` or added to package-data configuration.

## Core agent command path

```text
profiles -> voices list -> create -> lint -> inspect -> to-ssml/text
```

Use canonical commands with root-level `--json`:

```bash
ssmd --json profiles
ssmd --json voices list --provider kokoro
ssmd --json create "$draft" -o "$output" --voice-provider kokoro --fail-on-warn
ssmd --json lint "$output" --voice-provider kokoro --roundtrip --fail-on-warn
ssmd --json inspect "$output" --spans
ssmd --json to-ssml "$output" -o "$ssml_output"
ssmd --json text "$output"
```

**Important:**

- Require `schema == "ssmd.cli.v1"` before reading the JSON payload
- `--json` is root-level (before the command)
- Correct: `ssmd --json lint file.ssmd`
- Incorrect: `ssmd lint file.ssmd --json`
- Always check both process exit code and top-level `ok`
- For `create`, completion additionally requires `result.created == true`,
  `result.bytes_written > 0`, and the requested output path to exist
- For lint/format reports, also inspect `result.passed` or `result.clean`
- Read machine fields, not prose
- Use `result.files[].issues[]` for corrections
- Do not parse human output with regex
- Do not present a file as complete until `create` and the second `lint` pass both
  succeed
- `inspect` is diagnostic and does not replace lint
- Output derivatives only after the SSMD source passes the shipping gate
- Preserve drafts when creation fails
- Never bypass round-trip or warnings merely to obtain exit `0`
- `--no-roundtrip` remains an explicit exception, not a normal agent path

## JSON failure protocol

| Condition                           | Agent action                                                         |
| ----------------------------------- | -------------------------------------------------------------------- |
| exit `1`, lint report returned      | inspect issues, edit draft, rerun create and lint                    |
| exit `2`, `USAGE_ERROR`             | fix command/options; do not modify content yet                       |
| exit `2`, I/O error                 | correct path/permissions; preserve source                            |
| exit `3`, internal/conversion error | retain draft and JSON error; retry only after correcting root cause  |
| warnings with `--fail-on-warn`      | treat as incomplete                                                  |
| output exists                       | use a new path or add `--force` only when replacement is intentional |

`ok == true` means the command produced a domain result; it does not mean that the
domain operation passed. For example, a warning-blocked `create` can return `ok == true`
with `result.created == false` and exit `1`.

## Agent discovery

```bash
ssmd --json commands --agent-path
```

The skill may use the built-in path as a consistency check, but the documented shipping
gate remains authoritative.

## Required shipping gate

An SSMD file is complete only after the installed CLI has created it and a second lint
pass has succeeded.

1. Draft the content in a temporary `.ssmd` file.
2. Run `ssmd create` to format, validate, round-trip check, and atomically write the
   requested output.
3. Run `ssmd lint --roundtrip --fail-on-warn` against the written output and require
   `result.passed == true`.
4. When SSML is requested, run `ssmd to-ssml` only after the SSMD gate passes.
5. Report the exact output path and validation commands used.

Do not claim validity based on visual inspection alone.

## Standard workflow

Set the requested output path and keep the draft separate from the final file.

```bash
output="output.ssmd"
draft="$(mktemp "${TMPDIR:-/tmp}/ssmd-draft.XXXXXX.ssmd")"

cat > "$draft" <<'SSMD'
---
ssmd_version: "0.9"
---
# Title

Hello *world*!
SSMD

ssmd --json create "$draft" -o "$output" --fail-on-warn
ssmd --json lint "$output" --roundtrip --fail-on-warn
```

When replacing an existing output intentionally, add `--force` to `ssmd create`. Never
delete or truncate an existing target before validation.

YAML front matter is parsed by default. Use `--no-yaml-header` only when a caller needs
literal leading `---` content:

```bash
ssmd --json create "$draft" -o "$output" --fail-on-warn
ssmd --json lint "$output" --roundtrip --fail-on-warn
```

For a known TTS target, use the same capability preset during creation, validation, and
conversion:

```bash
ssmd --json create "$draft" -o "$output" --capabilities google --fail-on-warn
ssmd --json lint "$output" --capabilities google --roundtrip --fail-on-warn
ssmd --json to-ssml "$output" --target provider --capabilities google --loss-policy error -o output.ssml
```

Use `ssmd --json profiles` to discover valid profile and capability names. Do not guess
a preset name.

## Authoring rules

Prefer `.ssmd` for standalone documents. Use UTF-8 and ordinary LF line endings.

Use simple, explicit SSMD syntax: The snippets below show body-level syntax. Standalone
documents should begin with the 0.9 version header shown in the workflow examples.

```ssmd
*moderate emphasis*
**strong emphasis**
~~reduced emphasis~~
...500ms
...2s
[Bonjour]{lang="fr"}
[H2O]{sub="water"}
[123]{as="cardinal"}
[term]{ipa="tɜːm"}
[text]{volume="loud" rate="fast" pitch="high"}
[text]{voice="host" voice-name="en-US-Wavenet-A" voice-languages="en-US" gender="female"}
:::{voice="host"}
Hello from the host.
:::
```

A bare `...` is ordinary ellipsis text. Timed pauses need a unit such as `...500ms` or
`...2s`.

Keep annotation braces balanced. Quote attribute values. Avoid inventing unsupported
keys; validate any unfamiliar syntax against `SPECIFICATION.md` and the CLI.

## Multi-speaker podcast pattern

Before authoring multi-speaker content, run `ssmd --json voices list` and choose only
enabled inventory entries. Use stable logical references in the body, configure their
provider bindings with `ssmd voices bind`, and let `create` materialize only the
bindings used by the document. Do not copy the complete local inventory into document
headers.

Use voice directives for sustained dialogue. Give every speaker a stable voice name.

```ssmd
---
ssmd_version: "0.9"
---
# Episode title

:::{voice="moderator"}
Welcome to the show.
:::

:::{voice="positive"}
Thanks for having me.
:::
```

The portable header produced by `create` may contain the required bindings and enabled
`pause_defaults`. Recognized portable metadata such as `title` is preserved and is safe
for the strict shipping gate. Unknown application metadata may be preserved but produces
a warning, so it blocks `--fail-on-warn` unless a future explicit policy allows it.
After creating a document, run a second config-aware lint. On failure, inspect
unresolved references with `ssmd --json inspect "$file" --voices`.

Multi-sentence voice directives preserve their scope across SSMD → SSML → SSMD
conversion. Use a single voice block for a complete multi-sentence passage when that is
the intended scope. Regression coverage includes:

- `tests/test_rendering_targets.py::test_multisentence_voice_scope_survives_ssml_roundtrip`
- `tests/test_rendering_targets.py::test_versioned_multisentence_voice_scope_roundtrips`

## Length and word counting

Use `ssmd --json text "$file"` to get rendered plain text for length checks. Count words
against the rendered output, not the source markup.

## Capability preset consistency

Use the same capability preset for creation, linting, and conversion. Switching presets
can change validation diagnostics and rendered output, so select the output target and
loss policy explicitly. Choose a rendering target explicitly when the output contract
matters with `--target generic|ssml-1.1|provider`: `generic` for portable SSML,
`ssml-1.1` for standards-constrained output, or `provider` for capability-specific
adaptation. `--loss-policy error|warn|drop` controls unsupported semantics: `error`
rejects conversion, `warn` reports losses, and `drop` permits them with informational
diagnostics. Use `--dialect auto|0.8|0.9` when selecting input syntax; `auto` honors a
declared `ssmd_version` and preserves legacy behavior for unversioned documents.

For strict SSML 1.1 output, provide a root language with `--language` or
`--fallback-language`. Do not combine `--target ssml-1.1` with `--no-speak-tag`.
`from-ssml` rejects unrepresentable semantics by default and emits a complete, versioned
0.9 document. Use `--loss-policy warn|drop` to opt into reported losses, or `--fragment`
when a body fragment is specifically required.

## Legacy CLI JSON spellings

The following legacy forms still work but are not preferred:

```bash
# Legacy (still supported)
ssmd lint file.ssmd --format json
ssmd profiles --json

# Preferred (root-level --json)
ssmd --json lint file.ssmd
ssmd --json profiles
```

## Legacy SSMD 0.8 syntax

New documents must use declared SSMD 0.9 syntax. Raw `<div>` blocks, `voice-lang`,
`_reduced_`, compact `vrp`, short prosody aliases, and symbolic prosody forms are
compatibility syntax, not canonical 0.9 authoring. Do not copy those forms into new
files. For an existing unversioned or 0.8 document, read the migration report and use
the explicit `ssmd migrate` command; review any manual actions before replacing source.

## Migrating legacy documents

Use `migrate` only when the user asks to upgrade legacy SSMD. It verifies semantic
equivalence before producing canonical 0.9 content and leaves the source untouched by
default:

```bash
ssmd --json migrate "$source" --to 0.9
ssmd --json migrate "$source" --to 0.9 -o "$output"
ssmd --json migrate "$source" --to 0.9 --write
```

Inspect `result.changed`, `result.written`, and `result.manual_actions`. An error with
`MIGRATION_MANUAL_ACTION_REQUIRED` means the source needs a human semantic decision. Do
not replace it with search-and-replace edits or force an unverified migration. Existing
output files require explicit `--overwrite`.

## Atomic output requirements

When `ssmd create` writes to a filesystem path, it uses an atomic replace. Do not wrap
it in manual move or copy steps. When the output must land at a final location, point
`--output` at that path directly.

## Diagnostics

When lint or conversion fails, use `ssmd --json inspect` for structured diagnostics:

```bash
ssmd --json inspect "$file" --spans
ssmd --json inspect "$file" --sentences
ssmd --json inspect "$file" --paragraphs
```

The inspect command is diagnostic and does not replace the lint shipping gate.

## Voice Defaults and Natural Prosody

When a logical voice has stable identity-defining prosody, put it in YAML front matter
instead of repeating it in every block:

```yaml
voice_defaults:
  guest:
    pitch: high
```

Use the logical SSMD name, not a provider voice identifier. A local `rate`, `pitch`, or
`volume` override changes only that field. The seven natural rate levels run from
`very-slow` to `very-fast`; the seven pitch levels run from `very-low` to `very-high`.
Prefer these readable names or explicit percentages over compact `vrp` for new
authoring. `slow` is a moderate natural slowdown; reserve `very-slow` for an
intentionally strong effect.

If a document uses `prosody_transitions`, treat the section as renderer metadata. It
does not produce a standard SSML rate ramp. Before shipping, inspect both declared and
effective values:

```bash
ssmd --json inspect "$file" --sentences
```

Use `ssmd lint` to find inconsistent repeated voice prosody and large same-voice jumps.
A valid transition policy suppresses the abrupt-change warning; voice changes are not
treated as prosody continuity errors.

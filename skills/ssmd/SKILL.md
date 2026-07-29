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
ssmd --json inspect "$draft" --spans
ssmd --json to-ssml "$output" -o "$ssml_output"
ssmd --json text "$output"
```

**Important:**

- `--json` is root-level (before the command)
- Correct: `ssmd --json lint file.ssmd`
- Incorrect: `ssmd lint file.ssmd --json`
- Always check both process exit code and top-level `ok`
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
ssmd --json to-ssml "$output" --capabilities google -o output.ssml
```

Use `ssmd --json profiles` to discover valid profile and capability names. Do not guess
a preset name.

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

Before authoring multi-speaker content, run `ssmd --json voices list` and choose only
enabled inventory entries. Use stable logical references in the body, configure their
provider bindings with `ssmd voices bind`, and let `create` materialize only the
bindings used by the document. Do not copy the complete local inventory into document
headers.

Use voice directives for sustained dialogue. Give every speaker a stable voice name.

```ssmd
# Episode title

<div voice="moderator">
Welcome to the show.
</div>

<div voice="positive">
Thanks for having me.
</div>
```

The portable header produced by `create` may contain the required bindings and enabled
`pause_defaults`; unknown metadata is preserved. After creating a document, run a second
config-aware lint. On failure, inspect unresolved references with
`ssmd --json inspect "$file" --voices`.

Limit one sentence per voice block while the round-trip limitation exists. When the
round-trip changes or the parser supports multiple sentences per block, update the
guidance and remove this constraint.

## Length and word counting

Use `ssmd --json text "$file"` to get rendered plain text for length checks. Count words
against the rendered output, not the source markup.

## Capability preset consistency

Use the same capability preset for creation, linting, and conversion. Switching presets
between steps may hide warnings or silently drop annotations.

## Legacy compatibility

The following legacy forms still work but are not preferred:

```bash
# Legacy (still supported)
ssmd lint file.ssmd --format json
ssmd profiles --json

# Preferred (root-level --json)
ssmd --json lint file.ssmd
ssmd --json profiles
```

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

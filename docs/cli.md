# Command Line Interface

SSMD ships a command-line tool for creating, validating, converting, and formatting SSMD
files. The CLI uses Typer/Click for command registration and provides a root-level
`--json` option for machine-readable output with stable success/error envelopes.

After installing SSMD, the `ssmd` command is available:

```
pip install ssmd
ssmd --version
```

You can also run it as `python -m ssmd`.

```{contents} Commands
:depth: 1
:local: true
```

## Exit codes

:::{list-table} :widths: 10 90

- - `0`
  - Success. No lint errors (warnings allowed unless `--fail-on-warn`).
- - `1`
  - Lint found one or more errors, or `--fail-on-warn` found warnings.
- - `2`
  - CLI usage error, unreadable input, invalid output path, or invalid profile/preset.
- - `3`
    - Fatal conversion/parse error. :::

## Machine-readable output

Use `--json` at the root level to get JSON output:

```bash
ssmd --json lint story.ssmd
ssmd --json profiles
ssmd --json inspect story.ssmd --spans
ssmd --json voices list
```

The JSON output uses a stable envelope format:

```text
{
  "ok": true,
  "command": "lint",
  "result_type": "lint_report",
  "result": { ... }
}
```

Error envelope:

```json
{
  "ok": false,
  "command": "convert",
  "error": {
    "code": "USAGE_ERROR",
    "message": "...",
    "exit_code": 2
  }
}
```

For lint and format-check reports, `result.passed` or `result.clean` indicates whether
the document passed validation. The outer `ok` indicates whether the CLI operation
itself succeeded.

Agents must check both the process exit code and the command-specific result state:

| Command                | Required success state                                                |
| ---------------------- | --------------------------------------------------------------------- |
| `create`               | exit `0`, `ok == true`, `result.created == true`, output exists       |
| `lint` / `check`       | exit `0`, `ok == true`, `result.passed == true`                       |
| `fmt --check`          | exit `0`, `ok == true`, `result.clean == true`                        |
| conversion with output | exit `0`, `ok == true`, expected output exists or is reported written |
| `config validate`      | exit `0`, `ok == true`, command-specific valid state                  |

`ok == true` only means that a domain result was returned. A warning-blocked
`create --fail-on-warn` can return `ok == true`, `result.created == false`, and exit
`1`; it must not be treated as a successful shipment.

## `config` and `voices`

The local authoring configuration is resolved in this order: root `--config PATH`,
`SSMD_CONFIG`, then Click's platform application directory. On Linux the default is
`~/.config/ssmd/config.yaml`. Read-only commands do not create the file.

```bash
ssmd --json config path
ssmd config init
ssmd --json config show --effective
ssmd --json config validate
ssmd --json voices list --provider kokoro
ssmd voices bind kokoro moderator af_sarah
ssmd --json voices resolve moderator --provider kokoro
```

`voices list` is deterministic and excludes disabled entries unless `--include-disabled`
is supplied. Inventory entries are local authoring data and are not copied into portable
document headers.

## `lint` / `check`

Validate SSMD syntax and profile compatibility:

```
ssmd lint story.ssmd
ssmd check story.ssmd          # alias for lint
```

Options:

`--profile NAME`

: Lint profile to use (default `ssmd-core`). Available profiles: run `ssmd profiles`.

`--capabilities PRESET`

: Validate conversion against a TTS capability preset.

`--format {text,json}`

: Output format (default `text`). JSON emits a machine-readable report.

`--fail-on-warn`

: Exit `1` when warnings are found (useful in CI).

`--quiet`

: Suppress the `path: ok` line on success.

`--no-xml-check`

: Skip checking generated SSML for XML well-formedness.

`--roundtrip`

: Additionally compare canonical SSMD semantics across SSMD→SSML→SSMD. Equivalent
block-level and inline voice representations are treated as the same semantics.

`--parse-yaml-header` / `--no-yaml-header`

: Front matter is parsed by default. Use `--no-yaml-header` for literal leading `---`
content; `--parse-yaml-header` remains a compatibility spelling.

`--voice-provider PROVIDER`

: Resolve voice references against one provider.

`--no-config`

: Perform portable structural lint without requiring local inventory entries.

Text output uses `clean chars` offsets (the clean-text coordinate system), not source
line/column positions:

```
story.ssmd: error: clean chars 0-7: Tag 'inline' is not supported by profile 'ssmd-core'.
story.ssmd: warn: say-as 'currency' not supported, dropping
```

## `create`

Create a formatted and validated SSMD file with an atomic write:

```
ssmd create draft.ssmd -o episode.ssmd
cat draft.ssmd | ssmd create - -o episode.ssmd
ssmd create draft.ssmd -o episode.ssmd --fail-on-warn
ssmd create draft.ssmd -o episode.ssmd --force
```

`create` performs source formatting, syntax/profile validation, SSMD→SSML conversion,
XML well-formedness validation, and a semantic SSMD→SSML→SSMD round-trip check before
writing the output. If validation fails, the output file is not created or replaced. In
JSON mode, successful creation requires `result.created == true`, nonzero
`result.bytes_written`, and the requested output path to exist.

Options:

`--profile NAME`

: Lint profile to enforce (default `ssmd-core`).

`--capabilities PRESET`

: Validate against a target TTS capability preset.

`--fail-on-warn`

: Refuse to write when warnings are present.

`--parse-yaml-header`

: Compatibility spelling; YAML front matter is parsed by default.

`--config PATH`

: Select the local authoring configuration. `SSMD_CONFIG` is used when this option is
absent, followed by Click's platform application directory (`~/.config/ssmd/config.yaml`
on Linux).

`--voice-provider PROVIDER`

: Select the active provider for voice binding materialization.

`--bind REFERENCE=VOICE_ID`

: Add a repeatable explicit binding override for the selected provider.

`--materialize-config/--no-materialize-config`

: Enable or disable create-time config-derived header fields (enabled by default).

`--materialize-voice-bindings/--no-materialize-voice-bindings` and
`--materialize-pause-defaults/--no-materialize-pause-defaults`

: Override individual materialization categories.

`--no-format`

: Preserve source bytes instead of normalizing line endings.

`--no-roundtrip`

: Skip the semantic round-trip check.

`--force`

: Replace an existing output file. Replacement is atomic and preserves existing
permissions.

## `convert`

Convert between SSMD, SSML, and plain text:

```
ssmd convert story.ssmd --to ssml
ssmd convert story.ssml --from ssml --to ssmd
ssmd convert story.ssmd --to text
ssmd convert story.ssmd --to ssml -o story.ssml
```

The input format is inferred from the file extension (`ssmd`, `ssmd.md`, `md` → SSMD;
`ssml`, `xml` → SSML). Use `--from` to override or when reading from stdin:

```
cat story.ssmd | ssmd convert - --from ssmd --to ssml
```

## `to-ssml` / `from-ssml` / `text`

Convenience aliases for common conversions:

```
ssmd to-ssml story.ssmd -o story.ssml
ssmd from-ssml story.ssml -o story.ssmd
ssmd text story.ssmd
```

`to-ssml` accepts the same SSMD-to-SSML options as `convert` (`--pretty`,
`--capabilities`, `--auto-sentence-tags`, etc.).

Sentence detection options on `convert` and `to-ssml` are:

- `--sentence-spacy-model TEXT` for an exact package.
- `--sentence-model-size sm|md|lg|trf` for an exact tier.
- `--sentence-use-spacy` or `--no-sentence-use-spacy` to force the backend.

When neither model nor size is set, SSMD uses phrasplit's highest installed compatible
model for the document language. JSON conversion results and `inspect --header` include
the selected model diagnostics when sentence detection runs.

`text --capabilities PRESET` applies strict capability filtering before plain-text
rendering. For example, unsupported substitutions remain as their source text.

## `fmt`

Normalize source line endings without rewriting semantic SSMD structure. Headings, YAML
front matter, directives, annotations, and literal text are preserved. The final newline
state is preserved and `fmt` is idempotent:

```
ssmd fmt story.ssmd            # formatted output to stdout
ssmd fmt story.ssmd -w         # write normalized result in place, atomically
ssmd fmt story.ssmd --check    # exit 1 if formatting would change
ssmd fmt a.ssmd b.ssmd -w      # format multiple files
```

Without `-w` or `--check`, formatted SSMD is written to stdout. Multiple files require
either `-w` or `--check`; those two modes are mutually exclusive. Stdin cannot be
combined with `-w`, and `-` may appear only once.

## `profiles`

List available lint profiles and capability presets:

```
ssmd profiles
ssmd profiles --json
```

## `inspect` (JSON)

Inspect parsed structure (useful for debugging and TTS integrations):

```
ssmd inspect story.ssmd --spans
ssmd inspect story.ssmd --sentences
ssmd inspect story.ssmd --paragraphs
```

Output is always JSON.

## `version`

Print the installed SSMD version:

```
ssmd version
ssmd --version
```

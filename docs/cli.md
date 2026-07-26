# Command Line Interface

SSMD ships a command-line tool for validating, converting, and formatting SSMD files.
CLI argument handling uses the Python standard library; conversion and parsing use
SSMD's declared runtime dependencies.

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

::::{list-table} :widths: 10 90

- - `0`
  - Success. No lint errors (warnings allowed unless `--fail-on-warn`).
- - `1`
  - Lint found one or more errors, or `--fail-on-warn` found warnings.
- - `2`
  - CLI usage error, unreadable input, invalid output path, or invalid profile/preset.
- - `3`
    - Fatal conversion/parse error. ::::

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

: Additionally check that SSMD→SSML→SSMD does not fail (no byte comparison).

`--parse-yaml-header`

: Parse and apply YAML front matter before validation.

Text output uses `clean chars` offsets (the clean-text coordinate system), not source
line/column positions:

```
story.ssmd: error: clean chars 0-7: Tag 'inline' is not supported by profile 'ssmd-core'.
story.ssmd: warn: say-as 'currency' not supported, dropping
```

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
either `-w` or `--check`. Stdin cannot be combined with `-w`.

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

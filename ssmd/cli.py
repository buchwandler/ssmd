"""Command-line interface for the ssmd package.

Uses Typer/Click for command registration and provides a root-level ``--json``
option for machine-readable output with stable success/error envelopes.

Exit codes:

* ``0`` - success (no lint errors; warnings allowed unless ``--fail-on-warn``).
* ``1`` - lint found errors, or ``--fail-on-warn`` found warnings.
* ``2`` - CLI usage error, unreadable input, invalid output path or profile.
* ``3`` - fatal conversion/parse error.
"""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any

import click.exceptions
import typer

import ssmd
from ssmd.cli_common import (
    CONVERSION_FAILED,
    CONVERSION_UNSUPPORTED,
    EXIT_FATAL,
    EXIT_LINT_FAILED,
    EXIT_USAGE,
    FORMAT_CHECK_FAILED,
    INTERNAL_ERROR,
    INVALID_CAPABILITY_PRESET,
    INVALID_PROFILE,
    IO_READ_FAILED,
    LINT_FAILED,
    OUTPUT_EXISTS,
    STDIN_CONFLICT,
    USAGE_ERROR,
    CLIState,
    SSMDCLIError,
    cli_state_from_context,
    emit_payload,
    render_json,
)
from ssmd.command_inventory import (
    AGENT_GOLDEN_PATH_COMMANDS,
    COMMAND_METADATA,
    commands_inventory_json,
    get_commands_for_audience,
)
from ssmd.formatter import format_source
from ssmd.spans import LintIssue

SSMD_EXTENSIONS = (".ssmd.md", ".ssmd", ".md")
SSML_EXTENSIONS = (".ssml", ".xml")

# ═══════════════════════════════════════════════════════════════════════════
# Typer application
# ═══════════════════════════════════════════════════════════════════════════

app = typer.Typer(
    add_completion=True,
    no_args_is_help=True,
    help="Validate, create, inspect, convert, and format Speech Synthesis Markdown.",
)


# ═══════════════════════════════════════════════════════════════════════════
# Root callback
# ═══════════════════════════════════════════════════════════════════════════


@app.callback(invoke_without_command=True)
def root_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", is_eager=True, help="Show version and exit."),
    json_output: bool = typer.Option(False, "--json", is_eager=True, help="Emit JSON output."),
    debug: bool = typer.Option(False, "--debug", is_eager=True, help="Show tracebacks on error."),
) -> None:
    """Root callback that initializes CLIState."""
    state = CLIState(json_output=json_output, debug=debug)
    ctx.obj = state

    if version:
        if json_output:
            emit_payload(ctx, {"version": ssmd.__version__}, result_type="version")
        else:
            typer.echo(f"ssmd {ssmd.__version__}")
        return  # Exit normally after version

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        return  # Exit normally after help


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def read_text(path_arg: str) -> tuple[str, str]:
    """Read text from a path or stdin (``-``). Returns (path_label, text)."""
    if path_arg == "-":
        return "<stdin>", sys.stdin.read()
    path = Path(path_arg)
    return str(path), path.read_text(encoding="utf-8")


def read_source_text(path_arg: str) -> tuple[str, str]:
    """Read source text without universal-newline translation."""
    if path_arg == "-":
        return "<stdin>", sys.stdin.read()
    path = Path(path_arg)
    return str(path), path.read_bytes().decode("utf-8")


def write_text(output_arg: str | None, text: str) -> None:
    """Write text to a path or stdout (``-`` or no ``-o``)."""
    if not output_arg or output_arg == "-":
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    Path(output_arg).write_text(text, encoding="utf-8")


def infer_format(path_arg: str) -> str | None:
    """Infer ``ssmd`` or ``ssml`` from a path extension. None for stdin/unknown."""
    if path_arg == "-":
        return None
    name = Path(path_arg).name.lower()
    if name.endswith(SSMD_EXTENSIONS):
        return "ssmd"
    if name.endswith(SSML_EXTENSIONS):
        return "ssml"
    return None


def validate_profile_and_capabilities(profile: str, capabilities: str | None) -> None:
    """Validate CLI profile and capability preset names as usage errors."""
    try:
        ssmd.get_profile(profile)
    except ValueError as exc:
        raise SSMDCLIError(
            str(exc),
            code=INVALID_PROFILE,
            exit_code=EXIT_USAGE,
            details={"profile": profile},
        ) from exc
    if capabilities:
        try:
            ssmd.get_preset(capabilities)
        except ValueError as exc:
            raise SSMDCLIError(
                str(exc),
                code=INVALID_CAPABILITY_PRESET,
                exit_code=EXIT_USAGE,
                details={"capabilities": capabilities},
            ) from exc


def ensure_single_stdin(path_args: list[str]) -> None:
    """Reject commands that would need to consume stdin more than once."""
    if path_args.count("-") > 1:
        raise SSMDCLIError(
            "stdin ('-') may only be specified once",
            code=STDIN_CONFLICT,
            exit_code=EXIT_USAGE,
        )


def issue_to_dict(issue: LintIssue) -> dict[str, Any]:
    """Convert a LintIssue to the documented JSON shape."""
    has_offset = issue.char_start is not None or issue.char_end is not None
    return {
        "code": issue.code,
        "severity": issue.severity,
        "message": issue.message,
        "char_start": issue.char_start,
        "char_end": issue.char_end,
        "coordinate_system": "clean_text" if has_offset else None,
        "source_start": issue.source_start,
        "source_end": issue.source_end,
        "line": issue.line,
        "column": issue.column,
    }


@dataclass
class FileLintResult:
    """Lint result for a single file."""

    path: str
    issues: list[LintIssue]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def lint_one_file(
    text: str,
    *,
    profile: str,
    capabilities: str | None,
    parse_yaml_header: bool,
    xml_check: bool,
) -> list[LintIssue]:
    """Run profile lint plus a strict conversion/XML check on one file's text."""
    issues: list[LintIssue] = []

    try:
        issues.extend(ssmd.lint(text, profile=profile))
    except ValueError as exc:
        return [LintIssue("error", str(exc), code="syntax.invalid_profile")]

    try:
        doc = ssmd.Document(
            text,
            config={"pretty_print": False},
            capabilities=capabilities,
            parse_yaml_header=parse_yaml_header,
            strict=True,
        )
        ssml_text = doc.to_ssml()

        for warning in doc.warnings:
            issues.append(LintIssue("warn", warning, code="capability.warning"))

        if xml_check:
            ET.fromstring(ssml_text)
    except Exception as exc:  # noqa: BLE001 - report any conversion/XML failure
        issues.append(
            LintIssue(
                "error",
                f"Conversion/XML validation failed: {exc}",
                code="conversion.validation_failed",
            )
        )

    return issues


def _roundtrip_issues(
    text: str,
    *,
    capabilities: str | None,
    parse_yaml_header: bool = False,
) -> list[LintIssue]:
    """Compare semantic SSMD content across the configured round-trip."""
    try:
        document = ssmd.Document(
            text,
            config={"pretty_print": False},
            capabilities=capabilities,
            parse_yaml_header=parse_yaml_header,
        )
        source_text = document.ssmd
        ssml_text = document.to_ssml()
        result_text = ssmd.from_ssml(ssml_text, capabilities=capabilities)
    except Exception as exc:  # noqa: BLE001
        return [
            LintIssue(
                "error",
                f"Round-trip conversion failed: {exc}",
                code="roundtrip.conversion_failed",
            )
        ]

    source_fingerprint = _semantic_fingerprint(source_text)
    result_fingerprint = _semantic_fingerprint(result_text)
    if source_fingerprint == result_fingerprint:
        return []

    if source_fingerprint["clean_text"] != result_fingerprint["clean_text"]:
        detail = (
            "clean text changed from "
            f"{source_fingerprint['clean_text']!r} to "
            f"{result_fingerprint['clean_text']!r}"
        )
    else:
        detail = "annotation, directive, break, mark, or paragraph metadata changed"

    severity = "warn" if capabilities else "error"
    code = "roundtrip.lossy_capability" if capabilities else "roundtrip.semantic_loss"
    return [
        LintIssue(
            severity,
            f"Semantic round-trip mismatch: {detail}.",
            code=code,
        )
    ]


def _semantic_value(value: Any) -> Any:
    """Convert model dataclasses to deterministic JSON-like values."""
    if is_dataclass(value):
        return {field.name: _semantic_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {str(key): _semantic_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_semantic_value(item) for item in value]
    return value


def _join_semantic_text(left: str, right: str) -> str:
    """Join equivalent adjacent semantic runs without inventing punctuation spacing."""
    if not left:
        return right
    if not right:
        return left
    if left[-1].isspace() or right[0].isspace():
        return left + right
    if right[0] in ".,!?;:)]}":
        return left + right
    if left[-1] in "([{":
        return left + right
    return f"{left} {right}"


def _semantic_segment_runs(sentence: Any) -> list[dict[str, Any]]:
    """Canonicalize sentence-level context and parser-only segment boundaries."""
    context_voice = _semantic_value(sentence.voice)
    context_prosody = _semantic_value(sentence.prosody)
    runs: list[dict[str, Any]] = []

    for segment in sentence.segments:
        value = _semantic_value(segment)
        if value.get("voice") is None:
            value["voice"] = context_voice
        if value.get("language") is None:
            value["language"] = sentence.language
        if value.get("prosody") is None:
            value["prosody"] = context_prosody

        metadata = {key: item for key, item in value.items() if key != "text"}
        if runs:
            previous = runs[-1]
            previous_metadata = {key: item for key, item in previous.items() if key != "text"}
            if previous_metadata == metadata:
                previous["text"] = _join_semantic_text(previous["text"], value["text"])
                continue
        runs.append(value)

    return runs


def _semantic_fingerprint(text: str) -> dict[str, Any]:
    """Build a canonical fingerprint for the observable SSMD model."""
    paragraphs = ssmd.parse_paragraphs(text, sentence_detection=False)
    paragraph_values: list[list[dict[str, Any]]] = []
    for paragraph in paragraphs:
        sentences: list[dict[str, Any]] = []
        for sentence in paragraph.sentences:
            sentences.append(
                {
                    "segments": _semantic_segment_runs(sentence),
                    "breaks_after": _semantic_value(sentence.breaks_after),
                }
            )
        paragraph_values.append(sentences)

    return {
        "clean_text": "\n\n".join(paragraph.to_text() for paragraph in paragraphs),
        "paragraphs": paragraph_values,
    }


def _build_config(
    *,
    pretty: bool = False,
    no_speak_tag: bool = False,
    auto_sentence_tags: bool = False,
    sentence_use_spacy: bool | None = None,
    sentence_model_size: str | None = None,
) -> dict[str, Any]:
    """Build conversion config dict from CLI options."""
    config: dict[str, Any] = {
        "pretty_print": pretty,
        "output_speak_tag": not no_speak_tag,
        "auto_sentence_tags": auto_sentence_tags,
    }
    if sentence_use_spacy is not None:
        config["sentence_use_spacy"] = sentence_use_spacy
    if sentence_model_size:
        config["sentence_model_size"] = sentence_model_size
    return config


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomically write ``path``, preserving permissions when it already exists."""
    if path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
    else:
        current_umask = os.umask(0)
        os.umask(current_umask)
        mode = 0o666 & ~current_umask
    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def _annotation_to_dict(span: Any) -> dict[str, Any]:
    return {
        "char_start": span.char_start,
        "char_end": span.char_end,
        "attrs": span.attrs,
        "kind": span.kind,
        "node_id": span.node_id,
    }


def _print_lint_text(results: list[FileLintResult], *, quiet: bool) -> str:
    """Render lint results as human text. Returns the text."""
    lines: list[str] = []
    for result in results:
        if not result.issues:
            if not quiet:
                lines.append(f"{result.path}: ok")
            continue
        for issue in result.issues:
            loc = ""
            if issue.char_start is not None and issue.char_end is not None:
                loc = f"clean chars {issue.char_start}-{issue.char_end}: "
            source_loc = ""
            if issue.line is not None and issue.column is not None:
                source_loc = f"line {issue.line}, column {issue.column}: "
            lines.append(
                f"{result.path}: {issue.severity} [{issue.code}]: {source_loc}{loc}{issue.message}"
            )
    return "\n".join(lines) + "\n" if lines else ""


# ═══════════════════════════════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════════════════════════════


@app.command("version")
def version_command(ctx: typer.Context) -> None:
    """Print the ssmd version."""
    emit_payload(
        ctx, {"version": ssmd.__version__}, result_type="version", human=f"ssmd {ssmd.__version__}"
    )


@app.command("profiles")
def profiles_command(
    ctx: typer.Context,
    json_compat: bool = typer.Option(False, "--json", help="(Legacy) Emit JSON output."),
) -> None:
    """List lint profiles and capability presets."""
    profiles = sorted(ssmd.list_profiles())
    presets = sorted(ssmd.list_presets())
    state = cli_state_from_context(ctx)

    if json_compat and not state.json_output:
        state.json_output = True

    payload = {
        "profiles": profiles,
        "presets": presets,
    }

    human_lines = ["Lint profiles:"]
    for name in profiles:
        human_lines.append(f"  {name}")
    human_lines.append("")
    human_lines.append("Capability presets:")
    for name in presets:
        human_lines.append(f"  {name}")

    emit_payload(ctx, payload, result_type="profile_catalog", human="\n".join(human_lines))


@app.command("lint")
def lint_command(
    ctx: typer.Context,
    files: list[str] = typer.Argument(..., help="SSMD files to lint."),
    profile: str = typer.Option("ssmd-core", help="Lint profile name."),
    capabilities: str | None = typer.Option(None, help="Capability preset name."),
    format: str = typer.Option("text", help="(Legacy) Output format: text or json."),
    fail_on_warn: bool = typer.Option(False, "--fail-on-warn", help="Treat warnings as errors."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress per-file ok messages."),
    no_xml_check: bool = typer.Option(False, "--no-xml-check", help="Skip XML validation."),
    roundtrip: bool = typer.Option(False, "--roundtrip", help="Check semantic round-trip."),
    parse_yaml_header: bool = typer.Option(
        False, "--parse-yaml-header", help="Parse YAML front matter."
    ),
) -> None:
    """Validate SSMD syntax and profile compatibility."""
    state = cli_state_from_context(ctx)

    # Legacy compatibility: --format json enables JSON mode
    if format == "json" and not state.json_output:
        state.json_output = True

    _run_lint(
        ctx,
        files=files,
        profile=profile,
        capabilities=capabilities,
        fail_on_warn=fail_on_warn,
        quiet=quiet,
        no_xml_check=no_xml_check,
        roundtrip=roundtrip,
        parse_yaml_header=parse_yaml_header,
        command_name="lint",
    )


@app.command("check")
def check_command(
    ctx: typer.Context,
    files: list[str] = typer.Argument(..., help="SSMD files to check."),
    profile: str = typer.Option("ssmd-core", help="Lint profile name."),
    capabilities: str | None = typer.Option(None, help="Capability preset name."),
    format: str = typer.Option("text", help="(Legacy) Output format: text or json."),
    fail_on_warn: bool = typer.Option(False, "--fail-on-warn", help="Treat warnings as errors."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress per-file ok messages."),
    no_xml_check: bool = typer.Option(False, "--no-xml-check", help="Skip XML validation."),
    roundtrip: bool = typer.Option(False, "--roundtrip", help="Check semantic round-trip."),
    parse_yaml_header: bool = typer.Option(
        False, "--parse-yaml-header", help="Parse YAML front matter."
    ),
) -> None:
    """Alias for lint."""
    state = cli_state_from_context(ctx)

    # Legacy compatibility: --format json enables JSON mode
    if format == "json" and not state.json_output:
        state.json_output = True

    _run_lint(
        ctx,
        files=files,
        profile=profile,
        capabilities=capabilities,
        fail_on_warn=fail_on_warn,
        quiet=quiet,
        no_xml_check=no_xml_check,
        roundtrip=roundtrip,
        parse_yaml_header=parse_yaml_header,
        command_name="check",
    )


def _run_lint(
    ctx: typer.Context,
    *,
    files: list[str],
    profile: str,
    capabilities: str | None,
    fail_on_warn: bool,
    quiet: bool,
    no_xml_check: bool,
    roundtrip: bool,
    parse_yaml_header: bool,
    command_name: str,
) -> None:
    """Shared lint implementation for lint and check commands."""
    validate_profile_and_capabilities(profile, capabilities)
    ensure_single_stdin(files)

    results: list[FileLintResult] = []
    io_error: SSMDCLIError | None = None

    for file_arg in files:
        try:
            path_label, text = read_text(file_arg)
        except OSError as exc:
            io_error = SSMDCLIError(
                f"Could not read input: {exc}",
                code=IO_READ_FAILED,
                exit_code=EXIT_USAGE,
                details={"path": file_arg},
            )
            continue
        issues = lint_one_file(
            text,
            profile=profile,
            capabilities=capabilities,
            parse_yaml_header=parse_yaml_header,
            xml_check=not no_xml_check,
        )
        if roundtrip:
            issues.extend(
                _roundtrip_issues(
                    text,
                    capabilities=capabilities,
                    parse_yaml_header=parse_yaml_header,
                )
            )
        results.append(FileLintResult(path=path_label, issues=issues))

    has_errors = any(not result.ok for result in results)
    has_warns = any(issue.severity == "warn" for result in results for issue in result.issues)
    passed = not has_errors and not (fail_on_warn and has_warns)

    # Build payload
    files_payload = [
        {
            "path": result.path,
            "ok": result.ok,
            "issues": [issue_to_dict(issue) for issue in result.issues],
        }
        for result in results
    ]
    error_count = sum(1 for r in results for i in r.issues if i.severity == "error")
    warning_count = sum(1 for r in results for i in r.issues if i.severity == "warn")

    payload = {
        "passed": passed,
        "profile": profile,
        "capabilities": capabilities,
        "roundtrip": roundtrip,
        "fail_on_warn": fail_on_warn,
        "files": files_payload,
        "summary": {
            "file_count": len(results),
            "error_count": error_count,
            "warning_count": warning_count,
        },
    }

    human_text = _print_lint_text(results, quiet=quiet)
    warning_messages = [str(i.message) for r in results for i in r.issues if i.severity == "warn"]

    # For IO errors, raise immediately without emitting payload
    if io_error is not None:
        raise io_error

    emit_payload(
        ctx,
        payload,
        human=human_text,
        result_type="lint_report",
        warnings=warning_messages if warning_messages else None,
    )

    if not passed:
        raise SSMDCLIError(
            "Lint found errors",
            code=LINT_FAILED,
            exit_code=EXIT_LINT_FAILED,
        )


@app.command("convert")
def convert_command(
    ctx: typer.Context,
    input: str = typer.Argument(..., help="Input file path or '-' for stdin."),
    output: str | None = typer.Option(None, "-o", "--output", help="Output file path."),
    from_format: str | None = typer.Option(None, "--from", help="Input format: ssmd or ssml."),
    to: str = typer.Option(..., help="Output format: ssmd, ssml, or text."),
    capabilities: str | None = typer.Option(None, help="Capability preset name."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print XML output."),
    no_speak_tag: bool = typer.Option(False, "--no-speak-tag", help="Omit <speak> wrapper."),
    auto_sentence_tags: bool = typer.Option(
        False, "--auto-sentence-tags", help="Auto-wrap sentences."
    ),
    parse_yaml_header: bool = typer.Option(
        False, "--parse-yaml-header", help="Parse YAML front matter."
    ),
    sentence_model_size: str | None = typer.Option(None, help="spaCy model size."),
    sentence_use_spacy: bool | None = typer.Option(None, help="Use spaCy for sentence detection."),
) -> None:
    """Convert between SSMD, SSML, and plain text."""
    _run_convert(
        ctx,
        input=input,
        output=output,
        from_format=from_format,
        to=to,
        capabilities=capabilities,
        pretty=pretty,
        no_speak_tag=no_speak_tag,
        auto_sentence_tags=auto_sentence_tags,
        parse_yaml_header=parse_yaml_header,
        sentence_model_size=sentence_model_size,
        sentence_use_spacy=sentence_use_spacy,
    )


@app.command("to-ssml")
def to_ssml_command(
    ctx: typer.Context,
    input: str = typer.Argument(..., help="SSMD input file path or '-' for stdin."),
    output: str | None = typer.Option(None, "-o", "--output", help="Output SSML file path."),
    capabilities: str | None = typer.Option(None, help="Capability preset name."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print XML output."),
    no_speak_tag: bool = typer.Option(False, "--no-speak-tag", help="Omit <speak> wrapper."),
    auto_sentence_tags: bool = typer.Option(
        False, "--auto-sentence-tags", help="Auto-wrap sentences."
    ),
    parse_yaml_header: bool = typer.Option(
        False, "--parse-yaml-header", help="Parse YAML front matter."
    ),
    sentence_model_size: str | None = typer.Option(None, help="spaCy model size."),
    sentence_use_spacy: bool | None = typer.Option(None, help="Use spaCy for sentence detection."),
) -> None:
    """Convert SSMD to SSML."""
    _run_convert(
        ctx,
        input=input,
        output=output,
        from_format="ssmd",
        to="ssml",
        capabilities=capabilities,
        pretty=pretty,
        no_speak_tag=no_speak_tag,
        auto_sentence_tags=auto_sentence_tags,
        parse_yaml_header=parse_yaml_header,
        sentence_model_size=sentence_model_size,
        sentence_use_spacy=sentence_use_spacy,
    )


@app.command("from-ssml")
def from_ssml_command(
    ctx: typer.Context,
    input: str = typer.Argument(..., help="SSML input file path or '-' for stdin."),
    output: str | None = typer.Option(None, "-o", "--output", help="Output SSMD file path."),
    capabilities: str | None = typer.Option(None, help="Capability preset name."),
) -> None:
    """Convert SSML to SSMD."""
    _run_convert(
        ctx,
        input=input,
        output=output,
        from_format="ssml",
        to="ssmd",
        capabilities=capabilities,
    )


@app.command("text")
def text_command(
    ctx: typer.Context,
    input: str = typer.Argument(..., help="SSMD input file path or '-' for stdin."),
    output: str | None = typer.Option(None, "-o", "--output", help="Output text file path."),
    capabilities: str | None = typer.Option(None, help="Capability preset name."),
    parse_yaml_header: bool = typer.Option(
        False, "--parse-yaml-header", help="Parse YAML front matter."
    ),
) -> None:
    """Convert SSMD to plain text."""
    _run_convert(
        ctx,
        input=input,
        output=output,
        from_format="ssmd",
        to="text",
        capabilities=capabilities,
        parse_yaml_header=parse_yaml_header,
    )


def _run_convert(
    ctx: typer.Context,
    *,
    input: str,
    output: str | None,
    from_format: str | None,
    to: str,
    capabilities: str | None,
    pretty: bool = False,
    no_speak_tag: bool = False,
    auto_sentence_tags: bool = False,
    parse_yaml_header: bool = False,
    sentence_model_size: str | None = None,
    sentence_use_spacy: bool | None = None,
) -> None:
    """Shared conversion implementation."""
    path_label, input_text = read_text(input)

    resolved_from = from_format or infer_format(input)
    if not resolved_from:
        raise SSMDCLIError(
            "--from is required when the input format cannot be inferred "
            "(e.g. when reading from stdin)",
            code=USAGE_ERROR,
            exit_code=EXIT_USAGE,
        )

    config = _build_config(
        pretty=pretty,
        no_speak_tag=no_speak_tag,
        auto_sentence_tags=auto_sentence_tags,
        sentence_use_spacy=sentence_use_spacy,
        sentence_model_size=sentence_model_size,
    )

    try:
        if resolved_from == "ssmd" and to == "ssml":
            doc = ssmd.Document(
                input_text,
                config=config,
                capabilities=capabilities,
                parse_yaml_header=parse_yaml_header,
            )
            output_text = doc.to_ssml()
        elif resolved_from == "ssml" and to == "ssmd":
            output_text = ssmd.from_ssml(input_text, capabilities=capabilities)
        elif resolved_from == "ssmd" and to == "text":
            doc = ssmd.Document(
                input_text,
                config=config,
                capabilities=capabilities,
                parse_yaml_header=parse_yaml_header,
                strict=capabilities is not None,
            )
            output_text = doc.to_text()
        elif resolved_from == to:
            output_text = input_text
        else:
            raise SSMDCLIError(
                f"Unsupported conversion: {resolved_from} -> {to}",
                code=CONVERSION_UNSUPPORTED,
                exit_code=EXIT_USAGE,
                details={"from": resolved_from, "to": to},
                remediation=["Choose a supported --from/--to combination."],
            )
    except SSMDCLIError:
        raise
    except Exception as exc:
        raise SSMDCLIError(
            f"Conversion failed: {exc}",
            code=CONVERSION_FAILED,
            exit_code=EXIT_FATAL,
        ) from exc

    state = cli_state_from_context(ctx)
    if state.json_output:
        payload: dict[str, Any] = {
            "input": path_label,
            "input_format": resolved_from,
            "output_format": to,
        }
        if output and output != "-":
            _atomic_write_text(Path(output), output_text)
            payload["output"] = output
            payload["bytes_written"] = len(output_text.encode("utf-8"))
        else:
            payload["output"] = None
            payload["content"] = output_text
        emit_payload(ctx, payload, result_type="conversion_result")
    else:
        write_text(output, output_text)


@app.command("create")
def create_command(
    ctx: typer.Context,
    input: str = typer.Argument(..., help="SSMD source path or '-' for stdin."),
    output: str = typer.Option(..., "-o", "--output", help="Output file path."),
    profile: str = typer.Option("ssmd-core", help="Lint profile name."),
    capabilities: str | None = typer.Option(None, help="Capability preset name."),
    parse_yaml_header: bool = typer.Option(
        False, "--parse-yaml-header", help="Parse YAML front matter."
    ),
    fail_on_warn: bool = typer.Option(False, "--fail-on-warn", help="Treat warnings as errors."),
    no_format: bool = typer.Option(False, "--no-format", help="Skip formatting."),
    no_roundtrip: bool = typer.Option(False, "--no-roundtrip", help="Skip round-trip check."),
    force: bool = typer.Option(False, "--force", help="Replace existing output."),
) -> None:
    """Create a formatted, validated SSMD file atomically."""
    validate_profile_and_capabilities(profile, capabilities)

    path_label, source_text = read_source_text(input)
    output_path = Path(output)

    if output == "-":
        raise SSMDCLIError(
            "create requires a filesystem output path",
            code=USAGE_ERROR,
            exit_code=EXIT_USAGE,
        )
    if output_path.exists() and not force:
        raise SSMDCLIError(
            f"output already exists: {output_path}; use --force to replace it",
            code=OUTPUT_EXISTS,
            exit_code=EXIT_USAGE,
            details={"output": str(output_path)},
        )

    candidate = source_text if no_format else format_source(source_text)
    issues = lint_one_file(
        candidate,
        profile=profile,
        capabilities=capabilities,
        parse_yaml_header=parse_yaml_header,
        xml_check=True,
    )
    if not no_roundtrip:
        issues.extend(
            _roundtrip_issues(
                candidate,
                capabilities=capabilities,
                parse_yaml_header=parse_yaml_header,
            )
        )

    result = FileLintResult(path=path_label, issues=issues)
    has_errors = not result.ok
    has_warns = any(issue.severity == "warn" for issue in issues)

    if issues:
        _print_lint_text([result], quiet=False)

    if has_errors or (fail_on_warn and has_warns):
        # Emit JSON if in JSON mode
        state = cli_state_from_context(ctx)
        if state.json_output:
            payload = {
                "created": False,
                "input": path_label,
                "output": str(output_path),
                "formatted": not no_format,
                "roundtrip_checked": not no_roundtrip,
                "profile": profile,
                "capabilities": capabilities,
                "bytes_written": 0,
                "issues": [issue_to_dict(i) for i in issues],
            }
            emit_payload(ctx, payload, result_type="create_result")
        # Emit human error message
        state = cli_state_from_context(ctx)
        if not state.json_output:
            lint_text = _print_lint_text([result], quiet=False)
            print(lint_text, end="", file=sys.stderr)
        raise SSMDCLIError(
            "Validation failed",
            code=LINT_FAILED,
            exit_code=EXIT_LINT_FAILED,
        )

    _atomic_write_text(output_path, candidate)

    payload = {
        "created": True,
        "input": path_label,
        "output": str(output_path),
        "formatted": not no_format,
        "roundtrip_checked": not no_roundtrip,
        "profile": profile,
        "capabilities": capabilities,
        "bytes_written": len(candidate.encode("utf-8")),
        "issues": [issue_to_dict(i) for i in issues],
    }

    emit_payload(
        ctx,
        payload,
        result_type="create_result",
        human=f"{output_path}: created",
    )


@app.command("fmt")
def fmt_command(
    ctx: typer.Context,
    files: list[str] = typer.Argument(..., help="SSMD files to format."),
    write: bool = typer.Option(
        False, "-w", "--write", help="Write formatted output back to files."
    ),
    check: bool = typer.Option(False, "--check", help="Check if files would be reformatted."),
    parse_yaml_header: bool = typer.Option(
        False, "--parse-yaml-header", help="Parse YAML front matter."
    ),
) -> None:
    """Format SSMD."""
    ensure_single_stdin(files)
    if len(files) > 1 and not write and not check:
        raise SSMDCLIError(
            "Multiple files require --write or --check",
            code=USAGE_ERROR,
            exit_code=EXIT_USAGE,
        )
    if write and "-" in files:
        raise SSMDCLIError(
            "stdin cannot be used with --write",
            code=STDIN_CONFLICT,
            exit_code=EXIT_USAGE,
        )

    changed = False
    had_syntax_error = False
    file_results: list[dict[str, Any]] = []
    human_lines: list[str] = []

    for file_arg in files:
        path_label, text = read_source_text(file_arg)
        syntax_issues = [issue for issue in ssmd.lint(text) if issue.severity == "error"]
        if syntax_issues:
            human_text = _print_lint_text([FileLintResult(path_label, syntax_issues)], quiet=False)
            human_lines.append(human_text.rstrip())
            had_syntax_error = True
            file_results.append(
                {
                    "path": path_label,
                    "changed": False,
                    "written": False,
                    "issues": [issue_to_dict(i) for i in syntax_issues],
                }
            )
            continue

        formatted = format_source(text)
        file_changed = formatted != text

        if check:
            if file_changed:
                changed = True
                human_lines.append(f"{path_label}: would reformat")
            file_results.append(
                {
                    "path": path_label,
                    "changed": file_changed,
                    "written": False,
                    "issues": [],
                }
            )
        elif write:
            if file_changed:
                _atomic_write_text(Path(file_arg), formatted)
            file_results.append(
                {
                    "path": path_label,
                    "changed": file_changed,
                    "written": file_changed,
                    "issues": [],
                }
            )
        else:
            sys.stdout.write(formatted)
            file_results.append(
                {
                    "path": path_label,
                    "changed": False,
                    "written": False,
                    "issues": [],
                }
            )

    mode = "check" if check else ("write" if write else "stdout")
    clean = not changed and not had_syntax_error

    payload = {
        "mode": mode,
        "clean": clean,
        "files": file_results,
    }

    human = "\n".join(human_lines) + "\n" if human_lines else ""
    emit_payload(ctx, payload, human=human, result_type="fmt_report")

    if changed or had_syntax_error:
        raise SSMDCLIError(
            "Format check found issues",
            code=FORMAT_CHECK_FAILED,
            exit_code=EXIT_LINT_FAILED,
        )


@app.command("profiles-json", hidden=True)
def profiles_json_compat(ctx: typer.Context) -> None:
    """(Legacy) profiles with --json as a subcommand alias."""
    profiles = sorted(ssmd.list_profiles())
    presets = sorted(ssmd.list_presets())
    payload = {
        "profiles": profiles,
        "presets": presets,
    }
    emit_payload(ctx, payload, result_type="profile_catalog")


def _print_inspect_text(payload: Any) -> str:
    """Render inspect payload as human-readable text."""
    import json

    return json.dumps(payload, indent=2, default=str) + "\n"


@app.command("inspect")
def inspect_command(
    ctx: typer.Context,
    input: str = typer.Argument(..., help="Input file path or '-' for stdin."),
    spans: bool = typer.Option(False, "--spans", help="Show parsed spans."),
    sentences: bool = typer.Option(False, "--sentences", help="Show parsed sentences."),
    paragraphs: bool = typer.Option(False, "--paragraphs", help="Show parsed paragraphs."),
) -> None:
    """Inspect parsed spans, sentences, or paragraphs (JSON)."""
    _, text = read_text(input)

    if spans:
        result = ssmd.parse_spans(text)
        data: Any = {
            "clean_text": result.clean_text,
            "annotations": [_annotation_to_dict(span) for span in result.annotations],
            "warnings": result.warnings,
        }
        view = "spans"
    elif sentences:
        sentences_data = ssmd.parse_sentences(text)
        data = [
            {
                "text": sentence.text,
                "paragraph_index": sentence.paragraph_index,
                "sentence_index": sentence.sentence_index,
            }
            for sentence in sentences_data
        ]
        view = "sentences"
    else:  # paragraphs (default)
        paragraphs_data = ssmd.parse_paragraphs(text)
        data = [
            {
                "text": paragraph.text,
                "sentences": len(paragraph.sentences),
            }
            for paragraph in paragraphs_data
        ]
        view = "paragraphs"

    payload = {
        "input": input,
        "view": view,
        "data": data,
    }

    human = _print_inspect_text(data)
    emit_payload(ctx, payload, human=human, result_type="inspect_result")


@app.command("commands")
def commands_command(
    ctx: typer.Context,
    audience: str | None = typer.Option(None, "--audience", help="Filter by audience."),
    agent_path: bool = typer.Option(False, "--agent-path", help="Show only agent golden path."),
) -> None:
    """List available commands and their metadata."""
    state = cli_state_from_context(ctx)

    if agent_path:
        payload = {
            "kind": "ssmd_command_inventory",
            "agent_path": list(AGENT_GOLDEN_PATH_COMMANDS),
            "commands": [],
        }
        human = "Agent golden path:\n"
        for name in AGENT_GOLDEN_PATH_COMMANDS:
            spec = COMMAND_METADATA[name]
            human += f"  {name:<12} {spec.phase:<12} {spec.tier}\n"
        emit_payload(ctx, payload, human=human, result_type="command_inventory")
        return

    if audience:
        filtered = get_commands_for_audience(audience)
        payload = {
            "kind": "ssmd_command_inventory",
            "audience": audience,
            "commands": filtered,
        }
        human = f"Commands ({audience}):\n"
        for name in filtered:
            human += f"  {name}\n"
        emit_payload(ctx, payload, human=human, result_type="command_inventory")
        return

    inventory = commands_inventory_json()
    # Build human view
    human = "Commands:\n"
    for cmd in inventory["commands"]:
        human += f"  {cmd['name']:<12} {cmd['audience']:<18} {cmd['phase']:<12} {cmd['effect']}\n"
    human += f"\nAgent path: {' -> '.join(inventory['agent_path'])}\n"
    emit_payload(ctx, inventory, human=human, result_type="command_inventory")


# ═══════════════════════════════════════════════════════════════════════════
# CLI entry points
# ═══════════════════════════════════════════════════════════════════════════


def cli_main(argv: list[str] | None = None) -> None:
    """Main CLI entry point with error handling.

    1. Determines whether root ``--json`` was requested.
    2. Invokes the Typer app.
    3. Converts Click/Typer usage exceptions into JSON when machine mode is active.
    4. Maps typed SSMD CLI errors to exit codes.
    """
    # Pre-parse to detect --json before Typer processes the command
    json_requested = "--json" in (argv or sys.argv[1:])

    try:
        result = app(standalone_mode=False, args=argv)
        # If app returns an exit code, use it
        if result is not None and result != 0:
            raise SystemExit(result)
    except SSMDCLIError as exc:
        # For lint/format failures, we already emitted the payload
        # Just set the exit code
        # For other errors (IO, usage, etc.), emit the error
        if exc.code not in (LINT_FAILED, FORMAT_CHECK_FAILED):
            if json_requested:
                # Emit error JSON directly
                sys.stdout.write(render_json(exc.to_dict("ssmd")))
            else:
                print(f"ssmd: error: {exc}", file=sys.stderr)
        raise SystemExit(exc.exit_code) from exc
    except click.exceptions.UsageError as exc:
        if json_requested:
            # Emit error JSON directly
            error = SSMDCLIError(
                str(exc),
                code=USAGE_ERROR,
                exit_code=EXIT_USAGE,
            )
            sys.stdout.write(render_json(error.to_dict("ssmd")))
        else:
            exc.show()
        raise SystemExit(EXIT_USAGE) from exc
    except Exception as exc:
        if json_requested:
            # Emit error JSON directly
            error = SSMDCLIError(
                str(exc),
                code=INTERNAL_ERROR,
                exit_code=EXIT_FATAL,
            )
            sys.stdout.write(render_json(error.to_dict("ssmd")))
        else:
            print(f"ssmd: fatal: {exc}", file=sys.stderr)
        raise SystemExit(EXIT_FATAL) from exc


def main(argv: list[str] | None = None) -> int:
    """Compatibility wrapper that returns an integer exit code."""
    try:
        cli_main(argv)
    except SystemExit as exc:
        return int(exc.code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line interface for the ssmd package.

Uses only the Python standard library (``argparse``, ``json``, ``pathlib``,
``xml.etree.ElementTree``) and reuses the public ``ssmd`` APIs instead of
duplicating parsing or conversion logic.

Exit codes:

* ``0`` - success (no lint errors; warnings allowed unless ``--fail-on-warn``).
* ``1`` - lint found errors, or ``--fail-on-warn`` found warnings.
* ``2`` - CLI usage error, unreadable input, invalid output path or profile.
* ``3`` - fatal conversion/parse error.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ssmd
from ssmd.spans import LintIssue

EXIT_OK = 0
EXIT_LINT_FAILED = 1
EXIT_USAGE = 2
EXIT_FATAL = 3

SSMD_EXTENSIONS = (".ssmd.md", ".ssmd", ".md")
SSML_EXTENSIONS = (".ssml", ".xml")


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def read_text(path_arg: str) -> tuple[str, str]:
    """Read text from a path or stdin (``-``). Returns (path_label, text)."""
    if path_arg == "-":
        return "<stdin>", sys.stdin.read()
    path = Path(path_arg)
    return str(path), path.read_text(encoding="utf-8")


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


def issue_to_dict(issue: LintIssue) -> dict[str, Any]:
    """Convert a LintIssue to the documented JSON shape.

    Offsets are clean-text coordinates, not source line/column positions.
    """
    has_offset = issue.char_start is not None or issue.char_end is not None
    return {
        "severity": issue.severity,
        "message": issue.message,
        "char_start": issue.char_start,
        "char_end": issue.char_end,
        "coordinate_system": "clean_text" if has_offset else None,
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
        return [LintIssue("error", str(exc))]

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
            issues.append(LintIssue("warn", warning))

        if xml_check:
            ET.fromstring(ssml_text)
    except Exception as exc:  # noqa: BLE001 - report any conversion/XML failure
        issues.append(LintIssue("error", f"Conversion/XML validation failed: {exc}"))

    return issues


# ═══════════════════════════════════════════════════════════════════════════
# Command handlers
# ═══════════════════════════════════════════════════════════════════════════


def cmd_version(args: argparse.Namespace) -> int:
    print(f"ssmd {ssmd.__version__}")
    return EXIT_OK


def cmd_profiles(args: argparse.Namespace) -> int:
    profiles = ssmd.list_profiles()
    presets = ssmd.list_presets()
    if args.json:
        print(json.dumps({"profiles": profiles, "presets": presets}, indent=2))
        return EXIT_OK
    print("Lint profiles:")
    for name in profiles:
        print(f"  {name}")
    print()
    print("Capability presets:")
    for name in presets:
        print(f"  {name}")
    return EXIT_OK


def _print_lint_text(results: list[FileLintResult], *, quiet: bool) -> None:
    for result in results:
        if not result.issues:
            if not quiet:
                print(f"{result.path}: ok")
            continue
        for issue in result.issues:
            loc = ""
            if issue.char_start is not None and issue.char_end is not None:
                loc = f"clean chars {issue.char_start}-{issue.char_end}: "
            print(f"{result.path}: {issue.severity}: {loc}{issue.message}")


def _lint_results_to_json(results: list[FileLintResult], *, ok: bool) -> dict[str, Any]:
    files = [
        {
            "path": result.path,
            "ok": result.ok,
            "issues": [issue_to_dict(issue) for issue in result.issues],
        }
        for result in results
    ]
    return {"ok": ok, "files": files}


def cmd_lint(args: argparse.Namespace) -> int:
    # Validate profile/preset up front so invalid values are usage errors (2).
    ssmd.get_profile(args.profile)
    if args.capabilities:
        ssmd.get_preset(args.capabilities)

    results: list[FileLintResult] = []
    had_io_error = False

    for file_arg in args.files:
        try:
            path_label, text = read_text(file_arg)
        except OSError as exc:
            had_io_error = True
            results.append(
                FileLintResult(
                    path=file_arg if file_arg != "-" else "<stdin>",
                    issues=[LintIssue("error", f"Could not read input: {exc}")],
                )
            )
            continue
        issues = lint_one_file(
            text,
            profile=args.profile,
            capabilities=args.capabilities,
            parse_yaml_header=args.parse_yaml_header,
            xml_check=not args.no_xml_check,
        )
        if args.roundtrip:
            issues.extend(_roundtrip_issues(text, capabilities=args.capabilities))
        results.append(FileLintResult(path=path_label, issues=issues))

    has_errors = any(not result.ok for result in results)
    has_warns = any(
        issue.severity == "warn" for result in results for issue in result.issues
    )
    passed = not has_errors and not (args.fail_on_warn and has_warns)

    if args.format == "json":
        print(json.dumps(_lint_results_to_json(results, ok=passed), indent=2))
    else:
        _print_lint_text(results, quiet=args.quiet)

    if had_io_error:
        return EXIT_USAGE
    return EXIT_OK if passed else EXIT_LINT_FAILED


def _roundtrip_issues(text: str, *, capabilities: str | None) -> list[LintIssue]:
    """Issues from an SSMD -> SSML -> SSMD round-trip (no byte comparison)."""
    try:
        ssml_text = ssmd.to_ssml(text)
        ssmd.from_ssml(ssml_text, capabilities=capabilities)
    except Exception as exc:  # noqa: BLE001
        return [LintIssue("error", f"Round-trip conversion failed: {exc}")]
    return []


def _build_config(args: argparse.Namespace) -> dict[str, Any]:
    config: dict[str, Any] = {
        "pretty_print": args.pretty,
        "output_speak_tag": not args.no_speak_tag,
        "auto_sentence_tags": args.auto_sentence_tags,
    }
    if getattr(args, "sentence_use_spacy", None) is not None:
        config["sentence_use_spacy"] = args.sentence_use_spacy
    if getattr(args, "sentence_model_size", None):
        config["sentence_model_size"] = args.sentence_model_size
    return config


def cmd_convert(args: argparse.Namespace) -> int:
    path_label, input_text = read_text(args.input)

    input_format = args.from_format or infer_format(args.input)
    if not input_format:
        raise ValueError(
            "--from is required when the input format cannot be inferred "
            "(e.g. when reading from stdin)"
        )

    output_format = args.to
    config = _build_config(args)

    if input_format == "ssmd" and output_format == "ssml":
        doc = ssmd.Document(
            input_text,
            config=config,
            capabilities=args.capabilities,
            parse_yaml_header=args.parse_yaml_header,
        )
        output_text = doc.to_ssml()
    elif input_format == "ssml" and output_format == "ssmd":
        output_text = ssmd.from_ssml(input_text, capabilities=args.capabilities)
    elif input_format == "ssmd" and output_format == "text":
        output_text = ssmd.to_text(
            input_text,
            parse_yaml_header=args.parse_yaml_header,
            **config,
        )
    elif input_format == output_format:
        output_text = input_text
    else:
        raise ValueError(
            f"Unsupported conversion: {input_format} -> {output_format}"
        )

    write_text(args.output, output_text)
    return EXIT_OK


def cmd_fmt(args: argparse.Namespace) -> int:
    if len(args.files) > 1 and not args.write and not args.check:
        raise ValueError(
            "Multiple files require --write or --check"
        )

    changed = False
    for file_arg in args.files:
        path_label, text = read_text(file_arg)
        doc = ssmd.Document(text, parse_yaml_header=args.parse_yaml_header)
        formatted = doc.to_ssmd()
        if args.check:
            if formatted.strip() != text.strip():
                changed = True
                print(f"{path_label}: would reformat")
        elif args.write:
            if formatted.strip() != text.strip():
                Path(file_arg).write_text(formatted, encoding="utf-8")
        else:
            write_text(None, formatted)
    return EXIT_LINT_FAILED if args.check and changed else EXIT_OK


def _annotation_to_dict(span: Any) -> dict[str, Any]:
    return {
        "char_start": span.char_start,
        "char_end": span.char_end,
        "attrs": span.attrs,
        "kind": span.kind,
        "node_id": span.node_id,
    }


def cmd_inspect(args: argparse.Namespace) -> int:
    _, text = read_text(args.input)

    if args.spans:
        result = ssmd.parse_spans(text)
        payload: Any = {
            "clean_text": result.clean_text,
            "annotations": [_annotation_to_dict(span) for span in result.annotations],
            "warnings": result.warnings,
        }
    elif args.sentences:
        sentences = ssmd.parse_sentences(text)
        payload = [
            {
                "text": sentence.text,
                "paragraph_index": sentence.paragraph_index,
                "sentence_index": sentence.sentence_index,
            }
            for sentence in sentences
        ]
    else:  # paragraphs (default)
        paragraphs = ssmd.parse_paragraphs(text)
        payload = [
            {
                "text": paragraph.text,
                "sentences": len(paragraph.sentences),
            }
            for paragraph in paragraphs
        ]

    print(json.dumps(payload, indent=2, default=str))
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# Argument parser
# ═══════════════════════════════════════════════════════════════════════════


def _add_lint_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("files", nargs="+")
    p.add_argument("--profile", default="ssmd-core")
    p.add_argument("--capabilities")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--fail-on-warn", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--no-xml-check", action="store_true")
    p.add_argument("--roundtrip", action="store_true")
    p.add_argument("--parse-yaml-header", action="store_true")
    p.set_defaults(func=cmd_lint)


def _add_convert_ssmd_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--capabilities")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--no-speak-tag", action="store_true")
    p.add_argument("--auto-sentence-tags", action="store_true")
    p.add_argument("--parse-yaml-header", action="store_true")
    p.add_argument("--sentence-model-size", choices=["sm", "md", "lg", "trf"])
    spacy = p.add_mutually_exclusive_group()
    spacy.add_argument(
        "--sentence-use-spacy", dest="sentence_use_spacy", action="store_true"
    )
    spacy.add_argument(
        "--no-sentence-use-spacy", dest="sentence_use_spacy", action="store_false"
    )
    p.set_defaults(sentence_use_spacy=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ssmd",
        description="Validate, convert, and format Speech Synthesis Markdown (SSMD).",
    )
    parser.add_argument(
        "--version", action="version", version=f"ssmd {ssmd.__version__}"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    lint_help = "Validate SSMD syntax and profile compatibility"
    _add_lint_args(sub.add_parser("lint", help=lint_help))
    _add_lint_args(sub.add_parser("check", help="Alias for lint"))

    convert = sub.add_parser(
        "convert", help="Convert between SSMD, SSML, and plain text"
    )
    convert.add_argument("input")
    convert.add_argument("-o", "--output")
    convert.add_argument("--from", dest="from_format", choices=["ssmd", "ssml"])
    convert.add_argument("--to", required=True, choices=["ssmd", "ssml", "text"])
    _add_convert_ssmd_options(convert)
    convert.set_defaults(func=cmd_convert)

    to_ssml = sub.add_parser("to-ssml", help="Convert SSMD to SSML")
    to_ssml.add_argument("input")
    to_ssml.add_argument("-o", "--output")
    _add_convert_ssmd_options(to_ssml)
    to_ssml.set_defaults(from_format="ssmd", to="ssml", func=cmd_convert)

    from_ssml = sub.add_parser("from-ssml", help="Convert SSML to SSMD")
    from_ssml.add_argument("input")
    from_ssml.add_argument("-o", "--output")
    from_ssml.add_argument("--capabilities")
    from_ssml.set_defaults(
        from_format="ssml",
        to="ssmd",
        func=cmd_convert,
        pretty=False,
        no_speak_tag=False,
        auto_sentence_tags=False,
        parse_yaml_header=False,
        sentence_model_size=None,
        sentence_use_spacy=None,
    )

    text = sub.add_parser("text", help="Convert SSMD to plain text")
    text.add_argument("input")
    text.add_argument("-o", "--output")
    text.add_argument("--parse-yaml-header", action="store_true")
    text.set_defaults(
        from_format="ssmd",
        to="text",
        func=cmd_convert,
        capabilities=None,
        pretty=False,
        no_speak_tag=False,
        auto_sentence_tags=False,
        sentence_model_size=None,
        sentence_use_spacy=None,
    )

    fmt = sub.add_parser("fmt", help="Format SSMD")
    fmt.add_argument("files", nargs="+")
    fmt.add_argument("-w", "--write", action="store_true")
    fmt.add_argument("--check", action="store_true")
    fmt.add_argument("--parse-yaml-header", action="store_true")
    fmt.set_defaults(func=cmd_fmt)

    profiles = sub.add_parser(
        "profiles", help="List lint profiles and capability presets"
    )
    profiles.add_argument("--json", action="store_true")
    profiles.set_defaults(func=cmd_profiles)

    inspect = sub.add_parser(
        "inspect", help="Inspect parsed spans, sentences, or paragraphs (JSON)"
    )
    inspect.add_argument("input")
    kind = inspect.add_mutually_exclusive_group()
    kind.add_argument("--spans", action="store_true")
    kind.add_argument("--sentences", action="store_true")
    kind.add_argument("--paragraphs", action="store_true")
    inspect.set_defaults(func=cmd_inspect)

    sub.add_parser("version", help="Print the ssmd version")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        return cmd_version(args)

    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"ssmd: error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001
        print(f"ssmd: fatal: {exc}", file=sys.stderr)
        return EXIT_FATAL


if __name__ == "__main__":
    raise SystemExit(main())

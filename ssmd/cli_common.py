"""Shared CLI state, JSON rendering, and error handling for the SSMD CLI.

This module provides the generic machine-facing contracts used by all SSMD
commands when ``--json`` is active at the root level.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

import typer

# ═══════════════════════════════════════════════════════════════════════════
# Exit codes (must match the documented CLI contract)
# ═══════════════════════════════════════════════════════════════════════════

EXIT_OK = 0
EXIT_LINT_FAILED = 1
EXIT_USAGE = 2
EXIT_FATAL = 3

# ═══════════════════════════════════════════════════════════════════════════
# Error codes
# ═══════════════════════════════════════════════════════════════════════════

LINT_FAILED = "LINT_FAILED"
FORMAT_CHECK_FAILED = "FORMAT_CHECK_FAILED"
USAGE_ERROR = "USAGE_ERROR"
IO_READ_FAILED = "IO_READ_FAILED"
IO_WRITE_FAILED = "IO_WRITE_FAILED"
INVALID_PROFILE = "INVALID_PROFILE"
INVALID_CAPABILITY_PRESET = "INVALID_CAPABILITY_PRESET"
CONVERSION_UNSUPPORTED = "CONVERSION_UNSUPPORTED"
CONVERSION_FAILED = "CONVERSION_FAILED"
PARSE_FAILED = "PARSE_FAILED"
OUTPUT_EXISTS = "OUTPUT_EXISTS"
STDIN_CONFLICT = "STDIN_CONFLICT"
INTERNAL_ERROR = "INTERNAL_ERROR"


# ═══════════════════════════════════════════════════════════════════════════
# CLI State
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(slots=True)
class CLIState:
    """Mutable CLI state stored in the Typer context."""

    json_output: bool = False
    debug: bool = False


def cli_state_from_context(ctx: typer.Context) -> CLIState:
    """Retrieve or create CLIState from a Typer context."""
    state = ctx.obj
    if state is None:
        state = CLIState()
        ctx.obj = state
    return state


def enable_json_output(ctx: typer.Context) -> CLIState:
    """Enable JSON output mode on the CLIState. Returns the state."""
    state = cli_state_from_context(ctx)
    state.json_output = True
    return state


# ═══════════════════════════════════════════════════════════════════════════
# Deterministic JSON
# ═══════════════════════════════════════════════════════════════════════════


def _default_serializer(obj: Any) -> Any:
    """Serialize dataclasses and other non-JSON-native types."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    return str(obj)


def render_json(payload: Any) -> str:
    """Render *payload* as a deterministic JSON string.

    Keys are sorted, UTF-8 characters are preserved, and the result ends
    with exactly one newline.
    """
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=_default_serializer,
        )
        + "\n"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Command name derivation
# ═══════════════════════════════════════════════════════════════════════════


def command_name_from_context(ctx: typer.Context) -> str:
    """Derive a stable dotted command name from the Typer context.

    For this flat CLI the dotted and ordinary forms are identical, but the
    generic logic supports future subgroups (``group.command``).
    """
    # For a flat CLI, just return the command name (not the program name)
    # The command name is the info_name of the current context
    if ctx.info_name and ctx.info_name != "ssmd":
        return ctx.info_name
    # If we're in the root callback, return 'ssmd'
    return "ssmd"


# ═══════════════════════════════════════════════════════════════════════════
# Success envelope
# ═══════════════════════════════════════════════════════════════════════════


def emit_payload(
    ctx: typer.Context,
    payload: Any,
    *,
    human: str | None = None,
    result_type: str | None = None,
    warnings: Sequence[str] | None = None,
) -> None:
    """Emit a success envelope in JSON mode or human text otherwise.

    Parameters
    ----------
    ctx:
        The Typer context carrying CLIState.
    payload:
        The result object to include in ``result``.
    human:
        Pre-formatted human text to emit when JSON mode is off.
    result_type:
        Optional ``result_type`` label for the envelope.
    warnings:
        Optional warning messages to include in the envelope.
    """
    state = cli_state_from_context(ctx)
    if state.json_output:
        command = command_name_from_context(ctx)
        envelope: dict[str, Any] = {
            "ok": True,
            "command": command,
            "result": payload,
        }
        if result_type is not None:
            envelope["result_type"] = result_type
        if warnings:
            envelope["warnings"] = list(warnings)
        sys.stdout.write(render_json(envelope))
    else:
        if human is not None:
            sys.stdout.write(human)
            if human and not human.endswith("\n"):
                sys.stdout.write("\n")


# ═══════════════════════════════════════════════════════════════════════════
# SSMD CLI Error
# ═══════════════════════════════════════════════════════════════════════════


class SSMDCLIError(Exception):
    """A typed CLI error with a stable code and exit code."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        exit_code: int,
        details: Mapping[str, object] | None = None,
        remediation: Sequence[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
        self.details = dict(details) if details else {}
        self.remediation = list(remediation) if remediation else []

    def to_dict(self, command: str) -> dict[str, Any]:
        """Convert to the error envelope structure."""
        return {
            "ok": False,
            "command": command,
            "error": {
                "code": self.code,
                "message": str(self),
                "details": self.details,
                "remediation": self.remediation,
                "exit_code": self.exit_code,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════
# Error envelope
# ═══════════════════════════════════════════════════════════════════════════


def emit_error(ctx: typer.Context, error: SSMDCLIError) -> None:
    """Emit an error envelope in JSON mode or human error text otherwise.

    Parameters
    ----------
    ctx:
        The Typer context carrying CLIState.
    error:
        The typed CLI error to emit.
    """
    state = cli_state_from_context(ctx)
    if state.json_output:
        command = command_name_from_context(ctx)
        sys.stdout.write(render_json(error.to_dict(command)))
    else:
        print(f"ssmd: error: {error}", file=sys.stderr)

"""Command metadata inventory and agent golden path for the SSMD CLI.

This module provides a structured inventory of all registered CLI commands
along with an explicit agent golden path that describes the recommended
workflow for coding agents.
"""

from __future__ import annotations

from typing import NamedTuple

# ═══════════════════════════════════════════════════════════════════════════
# Audience constants
# ═══════════════════════════════════════════════════════════════════════════

STABLE_FOR_AGENTS = "stable_for_agents"
HUMAN_ORIENTED = "human_oriented"
COMPATIBILITY = "compatibility"

# ═══════════════════════════════════════════════════════════════════════════
# Role constants
# ═══════════════════════════════════════════════════════════════════════════

PRIMARY = "primary"
SUPPORT = "support"

# ═══════════════════════════════════════════════════════════════════════════
# Phase constants
# ═══════════════════════════════════════════════════════════════════════════

PHASE_DISCOVERY = "discovery"
PHASE_AUTHORING = "authoring"
PHASE_VALIDATION = "validation"
PHASE_DIAGNOSTICS = "diagnostics"
PHASE_DELIVERY = "delivery"
PHASE_MAINTENANCE = "maintenance"

# ═══════════════════════════════════════════════════════════════════════════
# Tier constants
# ═══════════════════════════════════════════════════════════════════════════

TIER_CRITICAL = "critical"
TIER_NORMAL = "normal"

# ═══════════════════════════════════════════════════════════════════════════
# Effect constants
# ═══════════════════════════════════════════════════════════════════════════

EFFECT_NONE = "none"
EFFECT_READ = "read"
EFFECT_WRITE = "write"


class CommandSpec(NamedTuple):
    """Metadata for a single registered CLI command."""

    audience: str
    effect: str
    surface: str
    phase: str
    tier: str = TIER_NORMAL
    agent_safe: bool = True
    accepts_stdin: bool = False
    writes_files: bool = False


# ═══════════════════════════════════════════════════════════════════════════
# Command metadata
# ═══════════════════════════════════════════════════════════════════════════

COMMAND_METADATA: dict[str, CommandSpec] = {
    "profiles": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_NONE,
        surface="profiles",
        phase=PHASE_DISCOVERY,
        tier=TIER_CRITICAL,
    ),
    "commands": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_NONE,
        surface="commands",
        phase=PHASE_DISCOVERY,
    ),
    "profiles-json": CommandSpec(
        audience=COMPATIBILITY,
        effect=EFFECT_NONE,
        surface="profiles-json",
        phase=PHASE_DISCOVERY,
        tier=TIER_NORMAL,
        agent_safe=False,
    ),
    "create": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_WRITE,
        surface="create",
        phase=PHASE_AUTHORING,
        tier=TIER_CRITICAL,
        writes_files=True,
    ),
    "lint": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_READ,
        surface="lint",
        phase=PHASE_VALIDATION,
        tier=TIER_CRITICAL,
        accepts_stdin=True,
    ),
    "check": CommandSpec(
        audience=COMPATIBILITY,
        effect=EFFECT_READ,
        surface="check",
        phase=PHASE_VALIDATION,
        accepts_stdin=True,
    ),
    "inspect": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_READ,
        surface="inspect",
        phase=PHASE_DIAGNOSTICS,
        tier=TIER_CRITICAL,
        accepts_stdin=True,
    ),
    "to-ssml": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_WRITE,
        surface="to-ssml",
        phase=PHASE_DELIVERY,
        tier=TIER_CRITICAL,
        writes_files=True,
    ),
    "text": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_WRITE,
        surface="text",
        phase=PHASE_DELIVERY,
        writes_files=True,
    ),
    "convert": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_WRITE,
        surface="convert",
        phase=PHASE_DELIVERY,
        writes_files=True,
    ),
    "from-ssml": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_WRITE,
        surface="from-ssml",
        phase=PHASE_AUTHORING,
        writes_files=True,
    ),
    "fmt": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_WRITE,
        surface="fmt",
        phase=PHASE_MAINTENANCE,
        writes_files=True,
    ),
    "version": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_NONE,
        surface="version",
        phase=PHASE_DISCOVERY,
    ),
    "config path": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_READ,
        surface="config path",
        phase=PHASE_DISCOVERY,
        tier=TIER_CRITICAL,
    ),
    "config init": CommandSpec(
        audience=HUMAN_ORIENTED,
        effect=EFFECT_WRITE,
        surface="config init",
        phase=PHASE_AUTHORING,
        writes_files=True,
    ),
    "config show": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_READ,
        surface="config show",
        phase=PHASE_DISCOVERY,
    ),
    "config validate": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_READ,
        surface="config validate",
        phase=PHASE_VALIDATION,
    ),
    "config get": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_READ,
        surface="config get",
        phase=PHASE_DISCOVERY,
    ),
    "config set": CommandSpec(
        audience=HUMAN_ORIENTED,
        effect=EFFECT_WRITE,
        surface="config set",
        phase=PHASE_AUTHORING,
        writes_files=True,
    ),
    "config unset": CommandSpec(
        audience=HUMAN_ORIENTED,
        effect=EFFECT_WRITE,
        surface="config unset",
        phase=PHASE_AUTHORING,
        writes_files=True,
    ),
    "voices list": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_READ,
        surface="voices list",
        phase=PHASE_DISCOVERY,
        tier=TIER_CRITICAL,
    ),
    "voices show": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_READ,
        surface="voices show",
        phase=PHASE_DISCOVERY,
    ),
    "voices add": CommandSpec(
        audience=HUMAN_ORIENTED,
        effect=EFFECT_WRITE,
        surface="voices add",
        phase=PHASE_AUTHORING,
        writes_files=True,
    ),
    "voices remove": CommandSpec(
        audience=HUMAN_ORIENTED,
        effect=EFFECT_WRITE,
        surface="voices remove",
        phase=PHASE_AUTHORING,
        writes_files=True,
    ),
    "voices bind": CommandSpec(
        audience=HUMAN_ORIENTED,
        effect=EFFECT_WRITE,
        surface="voices bind",
        phase=PHASE_AUTHORING,
        writes_files=True,
    ),
    "voices unbind": CommandSpec(
        audience=HUMAN_ORIENTED,
        effect=EFFECT_WRITE,
        surface="voices unbind",
        phase=PHASE_AUTHORING,
        writes_files=True,
    ),
    "voices resolve": CommandSpec(
        audience=STABLE_FOR_AGENTS,
        effect=EFFECT_READ,
        surface="voices resolve",
        phase=PHASE_DIAGNOSTICS,
    ),
}

# ═══════════════════════════════════════════════════════════════════════════
# Agent golden path
# ═══════════════════════════════════════════════════════════════════════════

AGENT_GOLDEN_PATH_COMMANDS: tuple[str, ...] = (
    "profiles",
    "voices list",
    "create",
    "lint",
    "inspect",
    "to-ssml",
    "text",
)


def get_commands_for_audience(audience: str) -> list[str]:
    """Return sorted command names matching the given audience."""
    return sorted(name for name, spec in COMMAND_METADATA.items() if spec.audience == audience)


def get_agent_path_specs() -> list[tuple[str, CommandSpec]]:
    """Return the agent golden path as (name, spec) pairs."""
    return [(name, COMMAND_METADATA[name]) for name in AGENT_GOLDEN_PATH_COMMANDS]


def commands_inventory_json() -> dict:
    """Return the full command inventory as a JSON-serializable dict."""
    commands = []
    for name, spec in sorted(COMMAND_METADATA.items()):
        commands.append(
            {
                "name": name,
                "audience": spec.audience,
                "effect": spec.effect,
                "surface": spec.surface,
                "phase": spec.phase,
                "tier": spec.tier,
                "agent_safe": spec.agent_safe,
                "accepts_stdin": spec.accepts_stdin,
                "writes_files": spec.writes_files,
            }
        )
    return {
        "kind": "ssmd_command_inventory",
        "agent_path": list(AGENT_GOLDEN_PATH_COMMANDS),
        "commands": commands,
    }

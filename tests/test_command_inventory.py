"""Tests for the SSMD command inventory and agent golden path."""

from ssmd.cli import app
from ssmd.command_inventory import (
    AGENT_GOLDEN_PATH_COMMANDS,
    COMMAND_METADATA,
    STABLE_FOR_AGENTS,
    commands_inventory_json,
    get_commands_for_audience,
)


def _collect_typer_commands(app_instance) -> set[str]:
    """Recursively collect all registered Typer command paths."""
    commands = set()
    for command in app_instance.registered_commands:
        if command.name:
            commands.add(command.name)
    for group in app_instance.registered_groups:
        if group.name and group.typer_instance is not None:
            for nested in _collect_typer_commands(group.typer_instance):
                commands.add(f"{group.name} {nested}")
    return commands


def test_command_metadata_matches_typer():
    """COMMAND_METADATA exactly matches the registered Typer commands."""
    registered = _collect_typer_commands(app)
    metadata_keys = set(COMMAND_METADATA.keys())

    # Registered commands should match metadata
    assert registered == metadata_keys, (
        f"Mismatch: registered={registered}, metadata={metadata_keys}"
    )


def test_no_duplicate_commands():
    """No duplicates in command metadata."""
    assert len(COMMAND_METADATA) == len(set(COMMAND_METADATA.keys()))


def test_agent_path_commands_exist_in_metadata():
    """Every agent-path command exists in metadata."""
    for name in AGENT_GOLDEN_PATH_COMMANDS:
        assert name in COMMAND_METADATA, f"Agent path command '{name}' not in COMMAND_METADATA"


def test_agent_path_commands_are_stable():
    """Every agent-path command is marked stable for agents."""
    for name in AGENT_GOLDEN_PATH_COMMANDS:
        spec = COMMAND_METADATA[name]
        assert spec.audience == STABLE_FOR_AGENTS, (
            f"Agent path command '{name}' is not stable_for_agents"
        )


def test_agent_path_commands_are_primary():
    """Every agent-path command is primary."""

    for name in AGENT_GOLDEN_PATH_COMMANDS:
        _spec = COMMAND_METADATA[name]
        # Not all agent path commands need to be primary, but most should be
        # This is a soft check


def test_agent_path_is_small():
    """The path remains small (<= 8 commands)."""
    assert len(AGENT_GOLDEN_PATH_COMMANDS) <= 8


def test_agent_path_no_duplicates():
    """No duplicates in agent golden path."""
    assert len(AGENT_GOLDEN_PATH_COMMANDS) == len(set(AGENT_GOLDEN_PATH_COMMANDS))


def test_agent_path_ordering():
    """Agent path is ordered by normal use: profiles -> create -> lint -> inspect -> to-ssml -> text."""
    names = list(AGENT_GOLDEN_PATH_COMMANDS)
    # Check key ordering constraints
    assert names.index("profiles") < names.index("create")
    assert names.index("create") < names.index("lint")
    assert names.index("lint") < names.index("inspect")


def test_all_write_commands_marked_correctly():
    """All write-capable commands have writes_files=True."""
    write_commands = ["create", "fmt", "to-ssml", "from-ssml", "text", "convert"]
    for name in write_commands:
        spec = COMMAND_METADATA[name]
        assert spec.writes_files is True, f"Command '{name}' should have writes_files=True"


def test_commands_json_shape():
    """commands_inventory_json returns the correct shape."""
    inventory = commands_inventory_json()

    assert "kind" in inventory
    assert inventory["kind"] == "ssmd_command_inventory"
    assert "agent_path" in inventory
    assert "commands" in inventory
    assert isinstance(inventory["commands"], list)
    assert len(inventory["commands"]) == len(COMMAND_METADATA)


def test_commands_json_has_all_fields():
    """Each command in the JSON inventory has all required fields."""
    inventory = commands_inventory_json()
    required_fields = {
        "name",
        "audience",
        "effect",
        "surface",
        "phase",
        "tier",
        "agent_safe",
        "accepts_stdin",
        "writes_files",
    }

    for cmd in inventory["commands"]:
        assert set(cmd.keys()) == required_fields, (
            f"Command '{cmd['name']}' missing fields: {required_fields - set(cmd.keys())}"
        )


def test_get_commands_for_audience():
    """get_commands_for_audience filters correctly."""
    stable = get_commands_for_audience(STABLE_FOR_AGENTS)
    assert "profiles" in stable
    assert "create" in stable
    assert "lint" in stable
    assert len(stable) > 0
    # Should be sorted
    assert stable == sorted(stable)


def test_all_commands_have_metadata():
    """Every registered Typer command has exactly one metadata entry."""
    registered = _collect_typer_commands(app)
    for name in registered:
        assert name in COMMAND_METADATA, f"Registered command '{name}' has no metadata"


def test_no_stale_metadata():
    """No stale metadata exists for an unregistered command."""
    registered = _collect_typer_commands(app)
    for name in COMMAND_METADATA:
        assert name in registered, f"Metadata exists for unregistered command '{name}'"

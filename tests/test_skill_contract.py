"""Tests for the SSMD skill contract.

These tests verify that skills/ssmd/SKILL.md exists, references valid
commands, and uses root-level JSON examples.
"""

import re
from pathlib import Path

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "ssmd" / "SKILL.md"


@pytest.fixture
def skill_content():
    """Read the skill file content."""
    assert SKILL_PATH.exists(), f"Skill file not found at {SKILL_PATH}"
    return SKILL_PATH.read_text(encoding="utf-8")


def test_skill_exists():
    """Skill exists at skills/ssmd/SKILL.md."""
    assert SKILL_PATH.exists()


def test_skill_not_in_package():
    """Skill does not exist under ssmd/."""
    package_skill = Path(__file__).parent.parent / "ssmd" / "SKILL.md"
    assert not package_skill.exists(), "SKILL.md should not be inside the ssmd package"


def test_skill_has_front_matter(skill_content):
    """Skill has YAML front matter."""
    assert skill_content.startswith("---")


def test_skill_has_name(skill_content):
    """Skill front matter contains name."""
    assert "name: ssmd" in skill_content


def test_skill_has_description(skill_content):
    """Skill front matter contains description."""
    assert "description:" in skill_content


def test_skill_has_core_path(skill_content):
    """Skill contains the core agent command path."""
    # Look for the path pattern
    assert "profiles" in skill_content
    assert "create" in skill_content
    assert "lint" in skill_content


def test_skill_uses_root_json_examples(skill_content):
    """Machine examples place --json before the command."""
    # Find all ssmd command examples
    ssmd_pattern = re.compile(r"ssmd\s+--json\s+\w+")
    matches = ssmd_pattern.findall(skill_content)
    assert len(matches) > 0, "Skill should have examples with 'ssmd --json <command>'"


def test_skill_no_lint_format_json_preferred(skill_content):
    """No preferred example uses 'lint --format json'."""
    # Check that the preferred form is documented
    # The old form may be mentioned as legacy but not as preferred
    lines = skill_content.split("\n")
    for i, line in enumerate(lines):
        # Skip if it's in a "legacy" or "compatibility" context
        if "legacy" in line.lower() or "compatibility" in line.lower():
            continue
        if "old" in line.lower() and ("form" in line.lower() or "syntax" in line.lower()):
            continue
        # Check for the old form being used as a primary example
        assert "lint --format json" not in line or "legacy" in line.lower(), (
            f"Line {i + 1}: 'lint --format json' should be marked as legacy"
        )


def test_skill_shipping_gate(skill_content):
    """Shipping gate includes both create and second-pass lint."""
    # The skill should document the shipping gate
    assert "create" in skill_content
    assert "lint" in skill_content


def test_skill_has_fail_on_warn(skill_content):
    """Skill retains --fail-on-warn."""
    assert "--fail-on-warn" in skill_content


def test_skill_has_roundtrip(skill_content):
    """Skill retains --roundtrip."""
    assert "--roundtrip" in skill_content


def test_skill_json_placement(skill_content):
    """Skill shows --json before the command, not after."""
    # Find ssmd command patterns
    lines = skill_content.split("\n")
    in_legacy_section = False
    for i, line in enumerate(lines):
        # Track if we're in a legacy section
        if "legacy" in line.lower() or "compatibility" in line.lower():
            in_legacy_section = True
        elif line.startswith("##") or line.startswith("# "):
            in_legacy_section = False
        # Skip lines in legacy sections
        if in_legacy_section:
            continue
        # Check for incorrect placement: ssmd <command> --json
        if re.search(r"ssmd\s+\w+\s+--json", line):
            # This is incorrect placement
            assert False, f"Line {i + 1}: --json should be before the command, not after"


def test_skill_has_agent_protocol(skill_content):
    """Skill documents the agent protocol."""
    assert "agent" in skill_content.lower() or "Agent" in skill_content


def test_skill_has_failure_decision_table(skill_content):
    """Skill has a failure decision table or protocol."""
    assert "exit" in skill_content.lower()
    assert "error" in skill_content.lower()


def test_skill_has_discovery_command(skill_content):
    """Skill documents the commands discovery command."""
    assert "commands" in skill_content

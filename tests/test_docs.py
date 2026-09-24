import re
from pathlib import Path

from ssmd.formatter import format_canonical
from ssmd.migration import migrate_ssmd
from ssmd.parser import lint, parse_structure


def test_docs_use_myst_markdown_only() -> None:
    docs = Path(__file__).parents[1] / "docs"
    assert not list(docs.glob("*.rst"))

    expected = {
        "api.md",
        "capabilities.md",
        "cli.md",
        "examples.md",
        "index.md",
        "installation.md",
        "parser.md",
        "quickstart.md",
        "spans.md",
        "ssml_conversion.md",
        "syntax.md",
    }
    assert expected <= {path.name for path in docs.glob("*.md")}


def test_canonical_ssmd_examples_are_strict_09_and_canonical() -> None:

    examples = Path(__file__).parents[1] / "examples"
    documents = sorted(examples.glob("*.ssmd.md"))
    assert documents

    for path in documents:
        source = path.read_text(encoding="utf-8")
        structure = parse_structure(source, dialect="0.9")
        assert structure.header.get("ssmd_version") == "0.9", path.name
        assert not [item for item in structure.diagnostics if item.severity == "error"], path.name
        assert not [item for item in lint(source, dialect="0.9") if item.severity == "error"], (
            path.name
        )
        assert format_canonical(source) == source, path.name

        migrated = migrate_ssmd(source)
        assert migrated.success, path.name
        assert migrated.content == source, path.name

        assert "<div" not in source.lower(), path.name
        assert "voice-lang=" not in source, path.name
        assert not re.search(r"\b(?:v|r|p|vrp)\s*=", source), path.name
        assert not any(alias in source for alias in ("++", ">>", "^^")), path.name

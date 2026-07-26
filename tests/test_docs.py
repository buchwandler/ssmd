from pathlib import Path


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

from __future__ import annotations

import pytest

from ssmd import Document, parse_structure


def _semantics(source: str, *, dialect: str = "auto") -> tuple[object, ...]:
    structure = parse_structure(source, dialect=dialect)
    errors = [item for item in structure.diagnostics if item.severity == "error"]
    assert not errors, [item.code for item in errors]
    annotations = tuple(
        (item.char_start, item.char_end, tuple(sorted(item.attrs.items())))
        for item in structure.annotations
    )
    events = tuple(
        (item.pos, item.kind, item.anchor, tuple(sorted(item.attrs.items())))
        for item in structure.events
    )
    return structure.clean_text, annotations, events


def test_document_to_ssmd_preserves_fenced_directive() -> None:
    source = '---\nssmd_version: "0.9"\n---\n:::{voice="moderator"}\nHello. Second.\n:::'
    document = Document(source, config={"dialect": "0.9"})

    formatted = document.to_ssmd()

    assert formatted == ':::{voice="moderator"}\nHello. Second.\n:::'
    assert _semantics(formatted, dialect="0.9") == _semantics(source)


def test_document_source_is_self_identifying_and_valid_09() -> None:
    body = ':::{voice="moderator"}\nHello.\n:::'
    document = Document(body, config={"dialect": "0.9"})

    source = document.source

    assert parse_structure(source).header["ssmd_version"] == "0.9"
    assert _semantics(source) == _semantics(body, dialect="0.9")


def test_document_to_ssmd_preserves_nested_fences_and_inline_structure() -> None:
    source = (
        '---\nssmd_version: "0.9"\ntitle: Example\n---\n'
        "# Heading *with emphasis*\n\n"
        ':::{voice="moderator"}\n'
        '[outer [inner]{voice="announcer"} end]{lang="en"} ...s @chapter\n\n'
        '::::{rate="slow"}\nNested ~~quiet~~.\n::::\n'
        ":::\n\nFinal paragraph."
    )
    document = Document(source, config={"dialect": "0.9"})

    formatted = document.to_ssmd()

    assert ':::::{voice="moderator"}' in formatted
    assert ':::{rate="slow"}\nNested ~~quiet~~.\n:::' in formatted
    assert '[outer [inner]{voice="announcer"} end]{lang="en"}' in formatted
    assert _semantics(formatted, dialect="0.9") == _semantics(source)
    assert _semantics(document.source) == _semantics(source)


@pytest.mark.parametrize(
    "operation",
    [
        lambda document: list(document.sentences()),
        lambda document: list(document.paragraphs()),
        lambda document: document.split(),
        lambda document: len(document),
        lambda document: document[0],
        lambda document: document.__setitem__(0, "Changed."),
        lambda document: document.__delitem__(0),
        lambda document: list(document),
    ],
)
def test_legacy_sentence_apis_reject_09_documents(operation) -> None:
    document = Document("Hello.", config={"dialect": "0.9"})

    with pytest.raises(ValueError, match="0.9"):
        operation(document)


def test_document_merge_rejects_09_without_mutating_either_source() -> None:
    document = Document("One.", config={"dialect": "0.9"})
    other = Document("Two.", config={"dialect": "0.9"})
    original = document.source

    with pytest.raises(ValueError, match="0.9"):
        document.merge(other)

    assert document.source == original
    assert other.ssmd == "Two."


def test_source_model_mutations_do_not_use_legacy_sentence_rebuilding() -> None:
    document = Document("One.", config={"dialect": "0.9"})
    document.replace("One", "Two")
    document.add_paragraph("Three.")
    document.insert(1, "Four.", "\n\n")

    assert document.get_fragment(0) == "Two."
    assert _semantics(document.source) == _semantics(
        "---\nssmd_version: '0.9'\n---\nTwo.\n\nFour.\n\nThree."
    )

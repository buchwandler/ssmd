"""Tests for logical voice reference extraction and materialization planning."""

from ssmd import extract_voice_references


def references(source: str) -> tuple[str, ...]:
    return tuple(use.reference for use in extract_voice_references(source))


def test_single_line_voice_div_is_discovered():
    assert references('<div voice="host">Hello.</div>') == ("host",)


def test_multiline_voice_div_is_discovered():
    assert references('<div voice="host">\nHello.\n</div>') == ("host",)


def test_multiple_single_line_voice_divs_are_deduplicated_by_reference():
    source = "\n".join(
        (
            '<div voice="host">Opening.</div>',
            '<div voice="analyst">Analysis.</div>',
            '<div voice="host">Closing.</div>',
        )
    )
    assert references(source) == ("analyst", "host")
    uses = extract_voice_references(source)
    assert uses[1].count == 2


def test_mixed_voice_div_layouts_are_discovered():
    source = '<div voice="host">Opening.</div>\n\n<div voice="analyst">\nAnalysis.\n</div>'
    assert references(source) == ("analyst", "host")


def test_voice_div_attribute_order_and_class_are_supported():
    assert references('<div class="speaker" voice="host">Hello.</div>') == ("host",)


def test_direct_concrete_voice_id_is_discovered():
    assert references('<div voice="af_sarah">Hello.</div>') == ("af_sarah",)


def test_div_without_voice_is_not_discovered():
    assert references('<div class="note">Hello.</div>') == ()

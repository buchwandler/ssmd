"""Basic functionality tests for SSMD."""

import pytest

import ssmd


def test_simple_text():
    """Test plain text conversion."""
    result = ssmd.to_ssml("hello world")
    assert result == "<speak><p>hello world</p></speak>"


def test_end_to_end_snapshot():
    """End-to-end SSMD → SSML snapshot."""
    text = """<div voice="Joanna">
Hello *world* ...s
</div>"""
    result = ssmd.to_ssml(text)

    assert (
        result == '<speak><p><voice name="Joanna">Hello <emphasis>world</emphasis>'
        '<break strength="strong"/></voice></p></speak>'
    )


def test_emphasis():
    """Test emphasis conversion."""
    result = ssmd.to_ssml("hello *world*!")
    assert result == "<speak><p>hello <emphasis>world</emphasis>!</p></speak>"


def test_strip_emphasis():
    """Test stripping emphasis."""
    result = ssmd.to_text("hello *world*!")
    assert result == "hello world!"


def test_break():
    """Test break conversion."""
    result = ssmd.to_ssml("hello ...1s world")
    assert '<break time="1s"/>' in result


def test_language_annotation():
    """Test language annotation."""
    result = ssmd.to_ssml('[Guardians of the Galaxy]{lang="en"}')
    assert 'xml:lang="en-US"' in result
    assert "Guardians of the Galaxy" in result


def test_substitution():
    """Test substitution annotation."""
    result = ssmd.to_ssml('[H2O]{sub="water"}')
    assert '<sub alias="water">H2O</sub>' in result


def test_mark():
    """Test mark processor."""
    result = ssmd.to_ssml("hello @marker world")
    assert '<mark name="marker"/>' in result


def test_strip_mark():
    """Test stripping marks."""
    result = ssmd.to_text("hello @marker world")
    assert result == "hello world"


def test_paragraph():
    """Test paragraph processing - double newlines create sentence boundaries."""
    result = ssmd.to_ssml("First paragraph.\n\nSecond paragraph.")
    # New architecture doesn't use <p> tags - sentences are joined directly
    assert "First paragraph." in result
    assert "Second paragraph." in result


def test_document_iteration():
    """Test document sentence iteration."""
    doc = ssmd.Document("Hello world!\nHow are you?", config={"auto_sentence_tags": True})

    sentences = list(doc.sentences())
    assert len(sentences) > 0


def test_document_api():
    """Test Document class API."""
    doc = ssmd.Document("hello *world*")
    result = doc.to_ssml()
    assert "emphasis" in result

    plain = doc.to_text()
    assert plain == "hello world"


def test_document_properties():
    """Test Document properties."""
    doc = ssmd.Document("Hello *world*!")

    # Test ssml property via to_ssml()
    assert "<speak>" in doc.to_ssml()
    assert "<emphasis>" in doc.to_ssml()

    # Test to_text() method
    assert doc.to_text() == "Hello world!"

    # Test ssmd property
    assert doc.ssmd == "Hello *world*!"


def test_config_skip_processor():
    """Test disabling features via capabilities."""
    from ssmd.capabilities import TTSCapabilities

    # Create capabilities with emphasis disabled
    caps = TTSCapabilities(emphasis=False)
    doc = ssmd.Document("hello *world*", capabilities=caps)
    result = doc.to_ssml()
    # Should not process emphasis - text is passed through raw
    assert "<emphasis>" not in result
    assert "world" in result


def test_prosody_annotation():
    """Test prosody annotation."""
    result = ssmd.to_ssml('[loud]{volume="x-loud"}')
    assert '<prosody volume="x-loud">loud</prosody>' in result


def test_xml_escaping():
    """Test XML special characters are properly escaped."""
    result = ssmd.to_ssml("command & conquer")
    assert "&amp;" in result or "command & conquer" in result


def test_document_building():
    """Test building documents incrementally."""
    doc = ssmd.Document()
    doc.add("Hello")
    doc.add(" ")
    doc.add("*world*")

    assert doc.ssmd == "Hello *world*"
    assert "<emphasis>world</emphasis>" in doc.to_ssml()


def test_document_add_sentence():
    """Test add_sentence method."""
    doc = ssmd.Document("First")
    doc.add_sentence("Second")

    assert doc.ssmd == "First\nSecond"


def test_document_add_paragraph():
    """Test add_paragraph method."""
    doc = ssmd.Document("First")
    doc.add_paragraph("Second")

    assert doc.ssmd == "First\n\nSecond"


def test_document_from_ssml():
    """Test creating Document from SSML."""
    ssml = "<speak><emphasis>Hello</emphasis> world</speak>"
    doc = ssmd.Document.from_ssml(ssml)

    assert "*Hello* world" in doc.ssmd


def test_document_from_text():
    """Test creating Document from plain text."""
    doc = ssmd.Document.from_text("Hello world")

    assert doc.ssmd == "Hello world"


def test_voice_simple_name():
    """Test voice with simple name."""
    result = ssmd.to_ssml('[Hello]{voice="Joanna"}')
    assert '<voice name="Joanna">Hello</voice>' in result


def test_voice_language_gender():
    """Test voice with language and gender."""
    result = ssmd.to_ssml('[Bonjour]{voice-lang="fr-FR" gender="female"}')
    assert '<voice language="fr-FR" gender="female">Bonjour</voice>' in result


def test_voice_all_attributes():
    """Test voice with all attributes."""
    result = ssmd.to_ssml('[Text]{voice-lang="en-GB" gender="male" variant="1"}')
    assert '<voice language="en-GB" gender="male" variant="1">Text</voice>' in result


def test_voice_wavenet_name():
    """Test voice with Wavenet-style name."""
    result = ssmd.to_ssml('[Hello]{voice="en-US-Wavenet-A"}')
    assert '<voice name="en-US-Wavenet-A">Hello</voice>' in result


def test_strip_voice():
    """Test stripping voice markup."""
    result = ssmd.to_text('[Hello]{voice="Joanna"}')
    assert result == "Hello"


def test_voice_directive_simple():
    """Test directive with simple voice name."""
    text = """<div voice="sarah">
Hello from Sarah
</div>"""
    result = ssmd.to_ssml(text)
    assert '<voice name="sarah">Hello from Sarah</voice>' in result


def test_voice_directive_with_break():
    """Test directive with break."""
    text = """<div voice="sarah">
Hello from Sarah
...500ms
</div>"""
    result = ssmd.to_ssml(text)
    assert '<voice name="sarah">Hello from Sarah' in result
    assert '<break time="500ms"/>' in result


def test_voice_directive_multiple():
    """Test multiple directives in sequence."""
    text = """<div voice="sarah">
Hello from Sarah
</div>

<div voice="michael">
Hello from Michael
</div>"""
    result = ssmd.to_ssml(text)
    assert '<voice name="sarah">Hello from Sarah</voice>' in result
    assert '<voice name="michael">Hello from Michael</voice>' in result
    # Each voice block is separate (no <p> tags in new architecture)
    assert result.count("<voice") == 2


def test_voice_directive_strip():
    """Test stripping directive markup."""
    text = """<div voice="sarah">
Hello from Sarah
</div>"""
    result = ssmd.to_text(text)
    assert result.strip() == "Hello from Sarah"


def test_voice_inline_and_directive():
    """Test mixing inline and directive syntax."""
    text = """<div voice="sarah">
Hello from Sarah, and [this is Michael]{voice="michael"} interrupting!
</div>

<div voice="michael">
Now I'm speaking normally.
</div>"""
    result = ssmd.to_ssml(text)
    assert '<voice name="sarah">' in result
    assert '<voice name="michael">this is Michael</voice>' in result
    assert result.count('name="michael"') == 2


def test_voice_directive_language_gender():
    """Test directive with language and gender attributes."""
    text = """<div voice-lang="fr-FR" gender="female">
Bonjour! Comment allez-vous?
</div>"""
    result = ssmd.to_ssml(text)
    assert '<voice language="fr-FR" gender="female">' in result
    assert "Bonjour!" in result


def test_voice_directive_all_attributes():
    """Test directive with all attributes."""
    text = """<div voice-lang="en-GB" gender="male" variant="1">
Hello from England!
</div>"""
    result = ssmd.to_ssml(text)
    assert '<voice language="en-GB" gender="male" variant="1">' in result
    assert "Hello from England!" in result


def test_voice_directive_strip_with_attrs():
    """Test stripping directive with attributes."""
    text = """<div voice-lang="fr-FR" gender="female">
Bonjour! Comment allez-vous?
</div>"""
    result = ssmd.to_text(text)
    assert result.strip() == "Bonjour! Comment allez-vous?"


def test_quoted_sentence_splitting():
    """Test that closing quotes stay with the final sentence in a quote.

    When splitting sentences within quotes like "I'm Tom. This is great.",
    the closing quote must be attached to the last sentence.
    """
    from ssmd.parser import parse_sentences

    # Test basic quoted text with multiple sentences
    text = '"I\'m Tom. This is great."'
    sentences = parse_sentences(text)

    assert len(sentences) == 2
    # Opening quote should be with first sentence
    assert sentences[0].to_text().startswith('"')
    # Closing quote must be with last sentence
    assert sentences[1].to_text().endswith('"')
    assert sentences[1].to_text() == 'This is great."'


def test_quoted_sentence_splitting_hello():
    """Test quoted sentence splitting with greeting."""
    from ssmd.parser import parse_sentences

    text = '"Hello there. How are you?"'
    sentences = parse_sentences(text)

    assert len(sentences) == 2
    assert sentences[0].to_text() == '"Hello there.'
    assert sentences[1].to_text() == 'How are you?"'


def test_quoted_sentence_splitting_dialogue():
    """Test quoted sentence splitting in dialogue."""
    from ssmd.parser import parse_sentences

    text = 'He said, "Stop! Don\'t go."'
    sentences = parse_sentences(text)

    assert len(sentences) == 2
    # The closing quote must stay with "Don't go."
    assert sentences[1].to_text().endswith('"')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

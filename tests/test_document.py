"""Test Document class features - building, editing, and advanced methods."""

import xml.etree.ElementTree as ET

import pytest

from ssmd import Document, ExtensionHandler
from ssmd.parser import parse_paragraphs
from ssmd.utils import extract_sentences


def _sentence_item_count(doc: Document) -> int:
    return len(list(doc.sentences()))


class TestDocumentBuilding:
    """Test document building methods."""

    def test_empty_document(self):
        """Test creating an empty document."""
        doc = Document()
        assert doc.ssmd == ""
        assert len(doc._fragments) == 0

    def test_document_with_initial_content(self):
        """Test creating document with initial content."""
        doc = Document("Hello world")
        assert doc.ssmd == "Hello world"

    def test_add_without_separator(self):
        """Test add() method."""
        doc = Document("Hello")
        doc.add(" world")
        assert doc.ssmd == "Hello world"

    def test_add_chaining(self):
        """Test method chaining with add()."""
        doc = Document()
        result = doc.add("Hello").add(" ").add("world")
        assert result is doc  # Returns self
        assert doc.ssmd == "Hello world"

    def test_add_sentence(self):
        """Test add_sentence() method."""
        doc = Document("First")
        doc.add_sentence("Second")
        assert doc.ssmd == "First\nSecond"

    def test_add_paragraph(self):
        """Test add_paragraph() method."""
        doc = Document("First")
        doc.add_paragraph("Second")
        assert doc.ssmd == "First\n\nSecond"

    def test_mixed_separators(self):
        """Test mixing different separator types."""
        doc = Document("Start")
        doc.add(" inline")
        doc.add_sentence("New sentence")
        doc.add_paragraph("New paragraph")

        assert doc.ssmd == "Start inline\nNew sentence\n\nNew paragraph"

    def test_add_empty_string(self):
        """Test that adding empty strings is no-op."""
        doc = Document("Hello")
        doc.add("")
        doc.add_sentence("")
        doc.add_paragraph("")
        assert doc.ssmd == "Hello"

    def test_document_metadata(self):
        """Test adding metadata to document."""
        doc = Document("Hello [Franz]{voice='franz'}")
        sentences = []
        for sentence in doc.sentences(as_documents=True):
            sentences.append(sentence)
        assert len(sentences) == 1
        assert sentences[0][0] == '<s>Hello <voice name="franz">Franz</voice></s>'


class TestDocumentExport:
    """Test document export methods."""

    def test_to_ssml(self):
        """Test to_ssml() export."""
        doc = Document("Hello *world*")
        ssml = doc.to_ssml()
        assert "<speak>" in ssml
        assert "<emphasis>world</emphasis>" in ssml

    def test_extension_namespaces(self):
        """Extension tags should declare namespaces on <speak>."""
        doc = Document('[secret]{ext="whisper"}')
        ssml = doc.to_ssml()
        ET.fromstring(ssml)
        assert "xmlns:amazon" in ssml

    def test_custom_extension_namespace_registry(self):
        """Custom extension handlers can register namespaces."""

        def custom_handler(text: str) -> str:
            return f"<custom:effect>{text}</custom:effect>"

        doc = Document(
            '[hello]{ext="custom"}',
            config={
                "extensions": {
                    "custom": ExtensionHandler(
                        custom_handler,
                        namespaces={"custom": "https://example.com/custom"},
                    )
                }
            },
        )
        ssml = doc.to_ssml()
        ET.fromstring(ssml)
        assert "xmlns:custom" in ssml

    def test_to_ssml_directive_paragraph_boundaries(self):
        """Directive blocks should not merge paragraphs."""
        ssmd = """<div voice="sarah">
Hello there.
</div>

<div voice="michael">
Goodbye now.
</div>"""
        doc = Document(ssmd)
        ssml = doc.to_ssml()
        assert ssml.count("<p>") == 2

    def test_pretty_print_no_xml_declaration(self):
        """Pretty print should avoid XML declaration."""
        doc = Document("Hello world.")
        doc.config = {"pretty_print": True}
        ssml = doc.to_ssml()
        assert not ssml.lstrip().startswith("<?xml")
        assert ssml.lstrip().startswith("<speak")

    def test_to_ssmd(self):
        """Test to_ssmd() export."""
        doc = Document("Hello *world*")
        assert doc.to_ssmd() == "Hello *world*"
        assert doc.to_ssmd() == doc.ssmd

    def test_title_metadata_is_preserved_but_not_spoken(self):
        """Portable title metadata survives formatting without entering speech."""
        doc = Document("---\ntitle: Review podcast\n---\nHello *world*.")

        assert doc.header == {"title": "Review podcast"}
        assert "title: Review podcast" in doc.to_ssmd(include_header=True)
        assert "Review podcast" not in doc.to_text()
        assert "Review podcast" not in doc.to_ssml()

    def test_to_text(self):
        """Test to_text() export."""
        doc = Document("Hello *world* @marker")
        assert doc.to_text() == "Hello world"

    def test_export_caching(self):
        """Test that SSML conversion is cached."""
        doc = Document("Hello *world*")
        ssml1 = doc.to_ssml()
        ssml2 = doc.to_ssml()
        assert ssml1 is ssml2  # Same object (cached)

    def test_cache_invalidation(self):
        """Test that cache is invalidated on modifications."""
        doc = Document("Hello")
        ssml1 = doc.to_ssml()
        doc.add(" world")
        ssml2 = doc.to_ssml()
        assert ssml1 != ssml2


class TestDocumentListInterface:
    """Test list-like interface for documents."""

    def test_len(self):
        """Test __len__() returns sentence count."""
        doc = Document("First.\nSecond.\nThird.")
        assert len(doc) == 3
        doc.add_paragraph("Fourth sentence.")
        assert len(doc) == 4

    def test_getitem_single(self):
        """Test getting single sentence by index."""
        doc = Document("First. Second. Third.")
        sentences = list(doc.sentences())
        assert doc[0] == sentences[0]
        assert doc[-1] == sentences[-1]

    def test_getitem_slice(self):
        """Test getting sentence slice."""
        doc = Document("First.\nSecond.\nThird.")
        sentences = list(doc.sentences())
        if len(sentences) >= 2:
            sliced = doc[0:2]
            assert isinstance(sliced, list)
            assert len(sliced) == 2

    def test_setitem(self):
        """Test replacing sentence."""
        doc = Document("First. Second. Third.")
        original_len = _sentence_item_count(doc)
        doc[0] = "Modified sentence."
        assert _sentence_item_count(doc) == original_len
        assert "Modified" in doc.ssmd

    def test_setitem_last_sentence(self):
        """Test replacing last sentence."""
        doc = Document("First. Second. Third.")
        last_index = _sentence_item_count(doc) - 1
        if last_index >= 0:
            doc[last_index] = "Final sentence."
            assert doc.ssmd.endswith("Final sentence.")

    def test_setitem_preserves_separators(self):
        """Test replacement keeps newline separators."""
        doc = Document("First.\nSecond.\nThird.", config={"auto_sentence_tags": True})
        doc[1] = "Middle sentence."
        lines = doc.ssmd.strip().splitlines()
        assert len(lines) >= 3
        assert lines[0] == "First."
        assert "Middle sentence." in lines
        assert lines[-1] == "Third."

    def test_delitem(self):
        """Test deleting sentence."""
        doc = Document("First.\nSecond.\nThird.")
        original_len = _sentence_item_count(doc)
        if original_len > 1:
            del doc[1]
            assert _sentence_item_count(doc) == original_len - 1

    def test_delitem_first_sentence(self):
        """Test deleting first sentence."""
        doc = Document("First.\nSecond.\nThird.")
        if _sentence_item_count(doc) > 1:
            del doc[0]
            assert doc.ssmd.startswith("Second")

    def test_iter(self):
        """Test iteration through sentences."""
        doc = Document("First. Second. Third.")
        sentences = list(doc)
        assert len(sentences) >= 1
        assert all(isinstance(s, str) for s in sentences)

    def test_iadd_string(self):
        """Test += operator with string."""
        doc = Document("Hello")
        doc += " world"
        assert doc.ssmd == "Hello world"

    def test_iadd_document(self):
        """Test += operator with another document."""
        doc1 = Document("Hello")
        doc2 = Document(" world")
        doc1 += doc2
        assert doc1.ssmd == "Hello world"


class TestDocumentEditing:
    """Test document editing methods."""

    def test_insert_at_beginning(self):
        """Test inserting at beginning."""
        doc = Document("world")
        doc.insert(0, "Hello ", "")
        assert doc.ssmd == "Hello world"

    def test_insert_at_end(self):
        """Test inserting at end."""
        doc = Document("Hello")
        doc.insert(999, " world", "")  # Large index = append
        assert doc.ssmd == "Hello world"

    def test_insert_with_separator(self):
        """Test inserting with separator."""
        doc = Document("First")
        doc.insert(1, "Second", "\n")
        assert "\n" in doc.ssmd

    def test_remove(self):
        """Test remove() method."""
        doc = Document("First. Second. Third.")
        original_len = _sentence_item_count(doc)
        doc.remove(0)
        assert _sentence_item_count(doc) == original_len - 1

    def test_clear(self):
        """Test clear() method."""
        doc = Document("Hello world")
        doc.add_sentence("More text")
        doc.clear()
        assert doc.ssmd == ""
        assert len(doc._fragments) == 0

    def test_replace_simple(self):
        """Test replace() method."""
        doc = Document("Hello world. Hello again.")
        doc.replace("Hello", "Hi")
        assert "Hi world. Hi again." in doc.ssmd

    def test_replace_with_count(self):
        """Test replace() with count limit."""
        doc = Document("Hello Hello Hello")
        doc.replace("Hello", "Hi", count=2)
        ssmd = doc.ssmd
        assert ssmd.count("Hi") == 2
        assert "Hello" in ssmd  # One remains

    def test_replace_not_found(self):
        """Test replace() when text not found."""
        doc = Document("Hello world")
        doc.replace("foo", "bar")
        assert doc.ssmd == "Hello world"  # Unchanged


class TestDocumentAdvanced:
    """Test advanced document methods."""

    def test_merge_documents(self):
        """Test merge() method."""
        doc1 = Document("First document")
        doc2 = Document("Second document")
        doc1.merge(doc2)
        assert "First document" in doc1.ssmd
        assert "Second document" in doc1.ssmd

    def test_merge_with_separator(self):
        """Test merge() with custom separator."""
        doc1 = Document("First")
        doc2 = Document("Second")
        doc1.merge(doc2, separator="\n")
        assert doc1.ssmd == "First\nSecond"

    def test_merge_empty_document(self):
        """Test merging an empty document."""
        doc1 = Document("Hello")
        doc2 = Document()
        doc1.merge(doc2)
        assert doc1.ssmd == "Hello"

    def test_split_into_sentences(self):
        """Test split() method."""
        doc = Document("First. Second. Third.")
        sentences = doc.split()
        assert isinstance(sentences, list)
        assert len(sentences) >= 1
        assert all(isinstance(s, Document) for s in sentences)

    def test_split_preserves_content(self):
        """Test that split() preserves all content."""
        doc = Document("Hello *world*. Test sentence.")
        sentences = doc.split()
        # Each sentence should be a valid document
        for sent_doc in sentences:
            assert isinstance(sent_doc.to_ssml(), str)
            assert isinstance(sent_doc.ssmd, str)

    def test_get_fragment(self):
        """Test get_fragment() method."""
        doc = Document()
        doc.add("First")
        doc.add_sentence("Second")
        doc.add_paragraph("Third")

        assert doc.get_fragment(0) == "First"
        assert doc.get_fragment(1) == "Second"
        assert doc.get_fragment(2) == "Third"

    def test_get_fragment_out_of_range(self):
        """Test get_fragment() with invalid index."""
        doc = Document("Hello")
        with pytest.raises(IndexError):
            doc.get_fragment(999)


class TestDocumentIteration:
    """Test document iteration features."""

    def test_sentences_returns_strings(self):
        """Test sentences() returns strings by default."""
        doc = Document("First. Second.")
        for sentence in doc.sentences():
            assert isinstance(sentence, str)
            assert "<s>" in sentence or "</s>" in sentence

    def test_paragraphs_returns_strings(self):
        """Test paragraphs() returns SSML paragraphs."""
        doc = Document("First paragraph.\n\nSecond paragraph.")
        paragraphs = list(doc.paragraphs())
        assert len(paragraphs) == 2
        assert all("<p>" in paragraph or paragraph for paragraph in paragraphs)

    def test_sentences_as_documents(self):
        """Test sentences(as_documents=True)."""
        doc = Document("First *emphasis*. Second.")
        for sent_doc in doc.sentences(as_documents=True):
            assert isinstance(sent_doc, Document)
            assert hasattr(sent_doc, "to_ssml")
            assert hasattr(sent_doc, "ssmd")

    def test_iteration_consistency(self):
        """Test that iteration returns consistent results."""
        doc = Document("First. Second. Third.")
        list1 = list(doc.sentences())
        list2 = list(doc.sentences())
        assert list1 == list2


class TestSentenceExtraction:
    """Test sentence extraction from SSML."""

    def test_extract_sentences_with_attributes(self):
        ssml = '<speak><s data-id="1">Hello</s><s foo="bar">World</s></speak>'
        sentences = extract_sentences(ssml)

        assert sentences == [
            '<s data-id="1">Hello</s>',
            '<s foo="bar">World</s>',
        ]

    def test_extract_sentences_paragraph_fallback(self):
        ssml = '<speak><p class="intro">Hello</p><p>World</p></speak>'
        sentences = extract_sentences(ssml)

        assert sentences == [
            '<p class="intro">Hello</p>',
            "<p>World</p>",
        ]


class TestDocumentProperties:
    """Test document properties."""

    def test_ssmd_property(self):
        """Test ssmd property."""
        doc = Document()
        doc.add("Hello")
        doc.add(" world")
        assert doc.ssmd == "Hello world"

    def test_config_property(self):
        """Test config property getter."""
        config = {"auto_sentence_tags": True}
        doc = Document(config=config)
        assert doc.config == config

    def test_config_property_setter(self):
        """Test config property setter."""
        doc = Document()
        doc.config = {"pretty_print": True}
        assert doc.config["pretty_print"] is True

    def test_capabilities_property(self):
        """Test capabilities property."""
        doc = Document(capabilities="pyttsx3")
        assert doc.capabilities == "pyttsx3"

    def test_capabilities_property_setter(self):
        """Test capabilities property setter."""
        doc = Document()
        doc.capabilities = "google"
        assert doc.capabilities == "google"


class TestDocumentClassMethods:
    """Test Document class methods."""

    def test_from_ssml(self):
        """Test Document.from_ssml()."""
        ssml = "<speak><emphasis>Hello</emphasis> world</speak>"
        doc = Document.from_ssml(ssml)
        assert "*Hello*" in doc.ssmd or "Hello" in doc.ssmd

    def test_from_ssml_with_config(self):
        """Test from_ssml() with config."""
        ssml = "<speak>Hello</speak>"
        doc = Document.from_ssml(ssml, config={"pretty_print": True})
        assert doc.config["pretty_print"] is True

    def test_from_text(self):
        """Test Document.from_text()."""
        doc = Document.from_text("Hello world")
        assert doc.ssmd == "Hello world"

    def test_from_text_equivalent_to_init(self):
        """Test that from_text() is equivalent to __init__()."""
        text = "Hello world"
        doc1 = Document.from_text(text)
        doc2 = Document(text)
        assert doc1.ssmd == doc2.ssmd


class TestDocumentRepresentation:
    """Test document string representations."""

    def test_repr(self):
        """Test __repr__()."""
        doc = Document("First. Second.")
        repr_str = repr(doc)
        assert "Document" in repr_str
        assert "paragraphs" in repr_str or "chars" in repr_str

    def test_str(self):
        """Test __str__() returns SSMD."""
        doc = Document("Hello *world*")
        assert str(doc) == "Hello *world*"


class TestDocumentSentenceEndingPreservation:
    """Test that sentence endings (periods) are preserved with break markers."""

    def test_period_preservation_with_break_markers(self):
        """Verify periods are preserved when break markers are present in Document."""
        doc = Document("I like ...s to sleep. What a ...c great day.")
        ssml = doc.to_ssml()

        # Periods must be preserved in SSML
        assert "sleep." in ssml, f"Period after 'sleep' missing in: {ssml}"
        assert "day." in ssml, f"Period after 'day' missing in: {ssml}"

        # Plain text should also have periods
        text = doc.to_text()
        assert "sleep." in text
        assert "day." in text

    def test_period_before_break_marker(self):
        """Verify period is preserved when break marker comes after it."""
        doc = Document("I like to sleep ...s.")
        ssml = doc.to_ssml()

        # Period must be in the SSML
        assert "sleep" in ssml
        assert "." in ssml
        # Should not have space before period
        assert " ." not in ssml, f"Unexpected space before period in: {ssml}"

    def test_multiple_break_markers_preserve_periods(self):
        """Verify periods with multiple break markers in text."""
        doc = Document("First ...w word ...s here. Second ...c part.")
        ssml = doc.to_ssml()

        assert "here." in ssml, f"Period after 'here' missing in: {ssml}"
        assert "part." in ssml, f"Period after 'part' missing in: {ssml}"

    def test_period_count_matches_with_breaks(self):
        """Verify the correct number of periods are preserved."""
        doc = Document("One ...s. Two ...c. Three ...w.")
        ssml = doc.to_ssml()

        # Should have 3 periods
        period_count = ssml.count(".")
        assert period_count == 3, f"Expected 3 periods, found {period_count} in: {ssml}"

    def test_mixed_punctuation_with_breaks(self):
        """Verify all punctuation types are preserved with break markers."""
        doc = Document("Question ...s? Exclaim ...c! Period ...w.")
        ssml = doc.to_ssml()

        assert "?" in ssml, "Question mark missing"
        assert "!" in ssml, "Exclamation mark missing"
        assert "." in ssml, "Period missing"

    def test_document_add_methods_preserve_periods(self):
        """Verify periods are preserved when using Document.add_* methods."""
        doc = Document()
        doc.add_sentence("First ...s sentence.")
        doc.add_sentence("Second ...c sentence.")

        ssml = doc.to_ssml()
        assert "First" in ssml and "sentence." in ssml
        assert "Second" in ssml and "sentence." in ssml

    def test_plain_text_extraction_preserves_periods(self):
        """Verify to_text() preserves periods correctly."""
        doc = Document("Test ...s one. Test ...c two.")
        text = doc.to_text()

        # Break markers should be removed but periods kept
        assert "...s" not in text, "Break marker should be removed"
        assert "...c" not in text, "Break marker should be removed"
        assert "one." in text, "Period after 'one' should be preserved"
        assert "two." in text, "Period after 'two' should be preserved"


class TestDocumentEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_document_operations(self):
        """Test operations on empty document."""
        doc = Document()
        assert doc.ssmd == ""
        assert doc.to_text() == ""
        assert len(list(doc.sentences())) >= 0

    def test_delitem_only_sentence(self):
        """Test deleting the only sentence in a document."""
        doc = Document("Only sentence.")
        if _sentence_item_count(doc) >= 1:
            del doc[0]
            assert doc.ssmd == ""
            assert len(doc._fragments) == 0

    def test_very_long_document(self):
        """Test handling of large documents."""
        doc = Document()
        for i in range(100):
            doc.add_sentence(f"Sentence {i}.")
        assert len(doc._fragments) == 100

    def test_special_characters(self):
        """Test documents with special characters."""
        doc = Document("Hello & goodbye <test> 'quoted'")
        ssml = doc.to_ssml()
        assert "&amp;" in ssml or "&" in ssml

    def test_unicode_content(self):
        """Test Unicode content."""
        doc = Document("Hello 世界 🌍")
        assert "世界" in doc.ssmd
        assert "🌍" in doc.ssmd

    def test_multiline_content(self):
        """Test multiline content."""
        doc = Document("Line 1\nLine 2\n\nParagraph 2")
        assert "\n" in doc.ssmd


class TestDocumentParsing:
    """Test parsing SSMD into Document."""

    def test_parse_ssmd_basic(self):
        """Test basic SSMD parsing."""
        ssmd = "Hello *world*"
        doc = Document(ssmd)
        paragraphs = parse_paragraphs(doc.ssmd)
        assert doc.ssmd == ssmd
        assert len(paragraphs) == 1
        assert len(paragraphs[0].sentences) == 1

    def test_parse_ssmd_with_metadata(self):
        """Test parsing SSMD with metadata."""
        ssmd = "Hello [User]{voice='user_voice'}"
        doc = Document(ssmd)
        paragraphs = parse_paragraphs(doc.ssmd)
        assert len(paragraphs) == 1
        voice = paragraphs[0].sentences[0].segments[1].voice
        assert voice is not None
        assert voice.name == "user_voice"

    def test_parse_ssmd_with_paragraph(self):
        """Test adding metadata to document."""
        doc = Document("Hello! \n\n How are you... 'I'm fine.'\n")
        sentences = list(doc.sentences(as_documents=True))
        assert len(sentences) == 3
        paragraphs = parse_paragraphs(doc.ssmd)
        assert len(paragraphs) == 2
        assert paragraphs[0].sentences[0].segments[0].text == "Hello!"
        assert paragraphs[1].sentences[0].segments[0].text == "How are you..."
        assert paragraphs[1].sentences[1].segments[0].text == "'I'm fine.'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

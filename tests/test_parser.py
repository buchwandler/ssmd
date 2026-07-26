"""Tests for SSMD parser (segment-based parsing)."""

import pytest

from ssmd import (
    iter_sentences_spans,
    parse_paragraphs,
    parse_segments,
    parse_sentences,
    parse_spans,
    parse_voice_blocks,
)


class TestParseVoiceBlocks:
    """Test directive block parsing."""

    def test_no_directive(self):
        """Test text without directives."""
        text = "Hello world"
        blocks = parse_voice_blocks(text)

        assert len(blocks) == 1
        assert blocks[0][0].voice is None
        assert blocks[0][0].language is None
        assert blocks[0][0].prosody is None
        assert blocks[0][1] == "Hello world"

    def test_single_voice_div(self):
        """Test single voice directive block."""
        text = '<div voice="sarah">\nHello world\n</div>'
        blocks = parse_voice_blocks(text)

        assert len(blocks) == 1
        assert blocks[0][0].voice is not None
        assert blocks[0][0].voice.name == "sarah"
        assert blocks[0][1] == "Hello world"

    def test_multiple_divs(self):
        """Test multiple directive blocks."""
        text = """<div voice="sarah">
Hello from Sarah
</div>

<div voice="michael">
Hello from Michael
</div>"""
        blocks = parse_voice_blocks(text)

        assert len(blocks) == 2
        assert blocks[0][0].voice is not None
        assert blocks[0][0].voice.name == "sarah"
        assert "Sarah" in blocks[0][1]
        assert blocks[1][0].voice is not None
        assert blocks[1][0].voice.name == "michael"
        assert "Michael" in blocks[1][1]

    def test_voice_with_language_gender(self):
        """Test voice directive block with language and gender."""
        text = '<div voice-lang="fr-FR" gender="female">\nBonjour\n</div>'
        blocks = parse_voice_blocks(text)

        assert len(blocks) == 1
        voice = blocks[0][0].voice
        assert voice is not None
        assert voice.language == "fr-FR"
        assert voice.gender == "female"
        assert voice.name is None

    def test_voice_directive_single_quotes(self):
        """Test directive attributes with single quotes."""
        text = "<div voice='sarah'>\nHello\n</div>"
        blocks = parse_voice_blocks(text)

        assert len(blocks) == 1
        assert blocks[0][0].voice is not None
        assert blocks[0][0].voice.name == "sarah"

    def test_voice_with_all_attributes(self):
        """Test voice directive block with all attributes."""
        text = '<div voice-lang="en-GB" gender="male" variant="1">\nHello\n</div>'
        blocks = parse_voice_blocks(text)

        voice = blocks[0][0].voice
        assert voice is not None
        assert voice.language == "en-GB"
        assert voice.gender == "male"
        assert voice.variant == 1

    def test_language_div(self):
        """Test language directive block."""
        text = '<div lang="en">\nHello\n</div>'
        blocks = parse_voice_blocks(text)

        directive = blocks[0][0]
        assert directive.language == "en"
        assert directive.voice is None
        assert directive.prosody is None

    def test_nested_divs(self):
        """Nested directives should merge attributes."""
        text = """<div lang="en">
<div voice="sarah">
Hello world
</div>
</div>"""
        blocks = parse_voice_blocks(text)

        directive = blocks[0][0]
        assert directive.language == "en"
        assert directive.voice is not None
        assert directive.voice.name == "sarah"

    def test_nested_divs_merge_voice_fields(self):
        """Nested directives should deep-merge voice fields."""
        text = """<div voice="Joanna">
<div voice-lang="de-DE">
Hallo Welt
</div>
</div>"""
        blocks = parse_voice_blocks(text)

        directive = blocks[0][0]
        assert directive.voice is not None
        assert directive.voice.name == "Joanna"
        assert directive.voice.language == "de-DE"

    def test_nested_divs_merge_prosody_fields(self):
        """Nested directives should deep-merge prosody fields."""
        text = """<div volume="x-loud">
<div rate="slow">
Hello world
</div>
</div>"""
        blocks = parse_voice_blocks(text)

        directive = blocks[0][0]
        assert directive.prosody is not None
        assert directive.prosody.volume == "x-loud"
        assert directive.prosody.rate == "slow"


class TestParseSegments:
    """Test segment parsing."""

    def test_plain_text(self):
        """Test parsing plain text."""
        segments = parse_segments("Hello world")

        assert len(segments) == 1
        assert segments[0].text == "Hello world"
        assert segments[0].emphasis is False

    def test_emphasis(self):
        """Test parsing emphasis."""
        segments = parse_segments("Hello *world*")

        # Currently creates one segment with emphasis flag
        assert len(segments) >= 1
        # Find segment with "world"
        world_seg = next(s for s in segments if "world" in s.text)
        assert world_seg.emphasis is True

    def test_breaks(self):
        """Test parsing breaks."""
        segments = parse_segments("Hello ...500ms world")

        # Should create segments with break between them
        assert len(segments) >= 1
        # At least one segment should have breaks_after
        has_break = any(len(s.breaks_after) > 0 for s in segments)
        assert has_break

    def test_breaks_not_in_numeric_ranges(self):
        """Ellipses in numeric ranges should not create breaks."""
        text = "Price is $5...10 today."
        segments = parse_segments(text)

        combined_text = "".join(segment.text for segment in segments)
        assert "5...10" in combined_text
        assert all(not segment.breaks_before and not segment.breaks_after for segment in segments)

    def test_marks_not_in_emails_or_urls(self):
        """Marks should not trigger inside emails or URLs."""
        text = "Email me@example.com or visit https://example.com/@user"
        segments = parse_segments(text)

        combined_text = "".join(segment.text for segment in segments)
        assert "me@example.com" in combined_text
        assert "@user" in combined_text
        assert all(not segment.marks_before and not segment.marks_after for segment in segments)

    def test_say_as(self):
        """Test parsing say-as annotation."""
        segments = parse_segments('Call [+1-555-0123]{as="telephone"} now')

        # Should find segment with say-as
        say_as_seg = next((s for s in segments if s.say_as), None)
        assert say_as_seg is not None
        assert say_as_seg.say_as is not None
        assert say_as_seg.say_as.interpret_as == "telephone"
        assert say_as_seg.text == "+1-555-0123"

    def test_substitution(self):
        """Test parsing substitution."""
        segments = parse_segments('[H2O]{sub="water"} is important')

        # Should find segment with substitution
        sub_seg = next((s for s in segments if s.substitution), None)
        assert sub_seg is not None
        assert sub_seg.text == "H2O"
        assert sub_seg.substitution == "water"

    def test_phoneme(self):
        """Test parsing phoneme."""
        segments = parse_segments('Say [tomato]{ph="t@meItoU"} properly')

        # Should find segment with phoneme
        phoneme_seg = next((s for s in segments if s.phoneme), None)
        assert phoneme_seg is not None
        assert phoneme_seg.text == "tomato"
        assert phoneme_seg.phoneme is not None  # X-SAMPA converted to IPA

        segments = parse_segments('Say [tomato]{ipa="t@meItoU"} properly')

        # Should find segment with phoneme
        phoneme_seg = next((s for s in segments if s.phoneme), None)
        assert phoneme_seg is not None
        assert phoneme_seg.text == "tomato"
        assert phoneme_seg.phoneme is not None  # X-SAMPA converted to IPA

        segments = parse_segments('Say [tomato]{sampa="t@meItoU"} properly')

        # Should find segment with phoneme
        phoneme_seg = next((s for s in segments if s.phoneme), None)
        assert phoneme_seg is not None
        assert phoneme_seg.text == "tomato"
        assert phoneme_seg.phoneme is not None  # X-SAMPA converted to IPA

    def test_prosody_annotation(self):
        """Test parsing prosody annotation."""
        segments = parse_segments('[loud text]{volume="5"}')

        # Should find segment with prosody
        prosody_seg = next((s for s in segments if s.prosody), None)
        assert prosody_seg is not None
        assert prosody_seg.prosody is not None
        assert prosody_seg.prosody.volume == "x-loud"

    def test_language_annotation(self):
        """Test parsing language annotation."""
        segments = parse_segments('[Bonjour]{lang="fr"} everyone')

        # Should find segment with language
        lang_seg = next((s for s in segments if s.language), None)
        assert lang_seg is not None
        assert lang_seg.language == "fr"

    def test_language_annotation_single_quotes(self):
        """Test parsing language annotation with single quotes."""
        segments = parse_segments("[Bonjour]{lang='fr'}")

        lang_seg = next((s for s in segments if s.language), None)
        assert lang_seg is not None
        assert lang_seg.language == "fr"

    def test_multiple_annotation_attributes(self):
        """Test parsing multiple annotation attributes."""
        segments = parse_segments("[x]{key1=\"v1\" key2='v2'}")

        segment = next((s for s in segments if s.text == "x"), None)
        assert segment is not None
        assert segment.extension is None
        assert segment.voice is None
        assert segment.language is None

    def test_annotation_attribute_whitespace(self):
        """Test annotation parser whitespace handling."""
        segments = parse_segments('[Hello]{ lang = "fr" }')

        segment = next((s for s in segments if s.text == "Hello"), None)
        assert segment is not None
        assert segment.language == "fr"

        segments = parse_segments('[Hello]{ lang = "fr"  voice = "Joanna A" }')

        segment = next((s for s in segments if s.text == "Hello"), None)
        assert segment is not None
        assert segment.language == "fr"
        assert segment.voice is not None
        assert segment.voice.name == "Joanna A"
        segments = parse_segments("[Hello]{ lang = 'fr'  voice = 'Joanna A' }")

        segment = next((s for s in segments if s.text == "Hello"), None)
        assert segment is not None
        assert segment.language == "fr"
        assert segment.voice is not None
        assert segment.voice.name == "Joanna A"

    def test_annotation_attribute_escape(self):
        """Test annotation parser escape handling."""
        segments = parse_segments('[Hello]{voice="Jo\\"anna"}')

        segment = next((s for s in segments if s.text == "Hello"), None)
        assert segment is not None
        assert segment.voice is not None
        assert segment.voice.name == 'Jo"anna'

    def test_annotation_attribute_unterminated_quote_warning(self):
        """Test annotation parser warnings on unterminated quotes."""
        result = parse_spans('[Hello]{voice="Joanna}')
        assert result.warnings


class TestParseSentences:
    """Test sentence parsing."""

    def test_single_sentence(self):
        """Test parsing single sentence."""
        sentences = parse_sentences("Hello world.")

        assert len(sentences) == 1
        assert len(sentences[0].segments) >= 1

    def test_multiple_sentences(self):
        """Test parsing multiple sentences."""
        sentences = parse_sentences("Hello world. How are you?")

        assert len(sentences) == 2

    def test_voice_blocks_create_sentences(self):
        """Test that directive changes create sentence boundaries."""
        text = """<div voice="sarah">
Hello from Sarah
</div>

<div voice="michael">
Hello from Michael
</div>"""
        sentences = parse_sentences(text)

        # Should have at least 2 sentences (one per voice block)
        assert len(sentences) >= 2
        assert sentences[0].voice is not None
        assert sentences[0].voice.name == "sarah"

    def test_paragraph_detection(self):
        """Test paragraph break detection."""
        text = "First paragraph.\n\nSecond paragraph."
        sentences = parse_sentences(text, sentence_detection=True)

        # Should detect paragraph break
        assert len(sentences) >= 2
        # First sentence should be marked as paragraph end
        assert any(s.is_paragraph_end for s in sentences)

    def test_sentence_indexes(self):
        """Test paragraph_index and sentence_index assignment."""
        text = "First sentence. Second sentence.\n\nThird sentence."
        sentences = parse_sentences(text, sentence_detection=True, use_spacy=False)

        assert len(sentences) == 3
        assert sentences[0].paragraph_index == 0
        assert sentences[0].sentence_index == 0
        assert sentences[1].paragraph_index == 0
        assert sentences[1].sentence_index == 1
        assert sentences[2].paragraph_index == 1
        assert sentences[2].sentence_index == 2

    def test_no_sentence_detection(self):
        """Test disabling sentence detection."""
        text = "Hello. How are you?"
        sentences = parse_sentences(text, sentence_detection=False)

        # Should treat as single sentence when detection disabled
        assert len(sentences) == 1

    def test_sentence_split_ignores_annotations_with_spacy(self):
        text = 'Der Film [Guardians of the *Galaxy*]{lang="en-GB"} ist ganz [okay]{lang="en-US"}.'
        sentences = parse_sentences(text)
        assert len(sentences) == 1

    def test_sentence_split_keeps_annotations_intact(self):
        text = 'Ich sah [Guardians of the Galaxy]{lang="en-GB"} im Kino.'
        sentences = parse_sentences(text)
        assert len(sentences) == 1
        assert sentences[0].to_ssmd().strip() == text

    def test_sentence_spans_offsets(self):
        """Test sentence span offsets against clean text."""
        text = "Hello *world*. Next sentence."
        spans = iter_sentences_spans(text, use_spacy=False)
        assert spans[0][0] == "Hello world."
        assert spans[0][1] == 0
        assert spans[0][2] == len("Hello world.")
        assert spans[1][0] == "Next sentence."

        clean_text = parse_spans(text).clean_text
        assert clean_text == "Hello world. Next sentence."

    def test_include_default_voice(self):
        """Test including text before first directive."""
        text = """Intro text

 <div voice="sarah">
 Sarah speaks
 </div>"""
        sentences = parse_sentences(text, include_default_voice=True)

        # Should include intro text
        assert len(sentences) >= 2
        assert sentences[0].voice is None

    def test_exclude_default_voice(self):
        """Test excluding text before first directive."""
        text = """Intro text

<div voice="sarah">
Sarah speaks
</div>"""
        sentences = parse_sentences(text, include_default_voice=False)

        # Should skip intro text
        assert all(s.voice is not None for s in sentences)


class TestParseParagraphs:
    """Test paragraph parsing."""

    def test_paragraph_structure(self):
        text = "First sentence. Second sentence.\n\nThird sentence."
        paragraphs = parse_paragraphs(text, sentence_detection=True, use_spacy=False)

        assert len(paragraphs) == 2
        assert len(paragraphs[0].sentences) == 2
        assert len(paragraphs[1].sentences) == 1
        assert paragraphs[0].sentences[0].paragraph_index == 0
        assert paragraphs[1].sentences[0].paragraph_index == 1


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_multi_voice_dialogue(self):
        """Test parsing multi-voice dialogue."""
        script = """
<div voice="sarah">
Welcome to the show!
</div>

<div voice="michael">
Thanks Sarah!
</div>

<div voice="sarah">
Great idea!
</div>
"""
        sentences = parse_sentences(script)

        # Should parse all directive blocks
        assert len(sentences) == 3
        assert sentences[0].voice is not None
        assert sentences[0].voice.name == "sarah"
        assert sentences[1].voice is not None
        assert sentences[1].voice.name == "michael"
        assert sentences[2].voice is not None
        assert sentences[2].voice.name == "sarah"

    def test_complex_features(self):
        """Test parsing multiple features in one text."""
        text = """<div voice="sarah">
Hello *world*! ...500ms Call [+1-555-0123]{as="telephone"} now.
[H2O]{sub="water"} is important.
</div>"""

        sentences = parse_sentences(text)

        # Should parse all features
        assert len(sentences) >= 1

        # Collect all segments
        all_segments = []
        for sent in sentences:
            all_segments.extend(sent.segments)

        # Should have segments with different features
        has_say_as = any(s.say_as for s in all_segments)
        has_substitution = any(s.substitution for s in all_segments)

        assert has_say_as or has_substitution  # At least one text transformation
        # Note: breaks might be merged, so they're not checked

    def test_multilingual_script(self):
        """Test multi-language script with voice directives and gender."""
        script = """<div voice-lang="fr-FR" gender="female">
Bonjour! Comment allez-vous?
</div>

<div voice-lang="en-GB" gender="male">
Hello there! How are you?
</div>"""

        try:
            sentences = parse_sentences(script)

            assert len(sentences) >= 2
            assert sentences[0].voice is not None
            assert sentences[0].voice.language == "fr-FR"
            assert sentences[0].voice.gender == "female"
            # Later sentences may have en-GB voice
            en_sentence = next(
                (s for s in sentences if s.voice and s.voice.language == "en-GB"), None
            )
            if en_sentence:
                assert en_sentence.voice is not None
                assert en_sentence.voice.gender == "male"
        except OSError:
            # French or English model not installed - use regex mode
            pytest.skip("spaCy models not installed for all languages")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_text(self):
        """Test parsing empty text."""
        sentences = parse_sentences("")
        assert len(sentences) == 0

    def test_whitespace_only(self):
        """Test parsing whitespace-only text."""
        sentences = parse_sentences("   \n\n   ")
        assert len(sentences) == 0

    def test_voice_without_content(self):
        """Test directive without following content."""
        text = '<div voice="sarah">\n</div>'
        sentences = parse_sentences(text)

        # Should not create empty sentences
        assert all(len(s.segments) > 0 for s in sentences) or len(sentences) == 0

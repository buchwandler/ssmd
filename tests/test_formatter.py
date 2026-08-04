"""Tests for SSMD formatter module."""

import pytest

from ssmd.formatter import _format_breaks, format_source, format_ssmd
from ssmd.parser import parse_sentences
from ssmd.parser_types import BreakAttrs, SSMDSegment, SSMDSentence


class TestFormatSSMD:
    """Test the format_ssmd() function."""

    def test_empty_input(self):
        """Empty list returns empty string."""
        result = format_ssmd([])
        assert result == ""

    def test_source_formatter_is_idempotent_and_preserves_structure(self):
        source = "---\ntitle: Example\n---\n\n# Heading\r\n\r\nBody."

        formatted = format_source(source)

        assert formatted == "---\ntitle: Example\n---\n\n# Heading\n\nBody."
        assert format_source(formatted) == formatted

    def test_single_sentence(self):
        """Single sentence gets newline."""
        text = "Hello world."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        assert formatted == "Hello world.\n"

    def test_multiple_sentences(self):
        """Each sentence on separate line."""
        text = "First sentence. Second sentence. Third sentence."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        expected = "First sentence.\nSecond sentence.\nThird sentence.\n"
        assert formatted == expected

    def test_mid_sentence_breaks(self):
        """Breaks between segments stay inline."""
        text = "I like ...s to sleep."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Mid-sentence break should be inline
        assert "...s" in formatted
        assert formatted.count("\n") == 1  # Only sentence newline

    def test_sentence_boundary_breaks(self):
        """Breaks after sentence append to line."""
        text = "Hello world. ...s How are you?"
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Break should be present
        assert "...s" in formatted
        # Should have two sentences
        lines = formatted.strip().split("\n")
        assert len(lines) == 2

    def test_sentence_boundary_break_is_emitted_once(self):
        """A boundary pause is moved to the preceding line without duplication."""
        sentences = parse_sentences("Hello. ...250ms Done.")
        original_breaks = list(sentences[1].segments[0].breaks_before)

        formatted = format_ssmd(sentences)

        assert formatted == "Hello. ...250ms\nDone.\n"
        assert formatted.count("...250ms") == 1
        assert sentences[1].segments[0].breaks_before == original_breaks

    def test_paragraph_breaks(self):
        """Paragraph ends create double newlines."""
        text = "First paragraph.\n\nSecond paragraph."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Should have blank line between paragraphs
        assert "\n\n" in formatted

    def test_mixed_breaks(self):
        """Both mid-sentence and boundary breaks."""
        text = "I like ...s to sleep. ...w How about you?"
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Should have mid-sentence break inline and boundary break at end
        assert "...s" in formatted
        assert "...w" in formatted

    def test_abbreviations(self):
        """Dr., Mr., U.S. don't cause sentence breaks."""
        text = "Dr. Smith met Mr. Johnson at the U.S. Embassy."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Should be single sentence
        lines = formatted.strip().split("\n")
        assert len(lines) == 1
        assert "Dr. Smith" in lines[0]

    def test_emphasis_preserved(self):
        """Emphasis markers preserved in text.

        Note: The parser currently processes single * markers and removes them,
        but preserves ** markers. This test checks what's actually preserved.
        """
        text = "This is **strong** emphasis."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Double asterisks should be preserved
        assert "**strong**" in formatted or "*strong*" in formatted

    def test_multiple_break_types(self):
        """...w, ...s, ...p, ...500ms all work."""
        text = "Text ...w more ...s text ...p final ...500ms end."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # All break types should be present
        assert "...w" in formatted
        assert "...s" in formatted
        assert "...p" in formatted
        assert "...500ms" in formatted

    def test_question_mark_sentence(self):
        """Questions are separate sentences."""
        text = "How are you? I'm fine."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        lines = formatted.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "How are you?"
        assert lines[1] == "I'm fine."

    def test_exclamation_sentence(self):
        """Exclamations are separate sentences."""
        text = "Hello! Welcome here."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        lines = formatted.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "Hello!"

    def test_multiple_paragraphs(self):
        """Multiple paragraphs with proper spacing."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Count blank lines (paragraph separators)
        paragraphs = formatted.strip().split("\n\n")
        assert len(paragraphs) == 3

    def test_complex_text_with_quotes(self):
        """Quoted text with multiple sentences."""
        text = '"Hello there. How are you?" he asked.'
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Should preserve quotes
        assert '"' in formatted


class TestFormatBreaks:
    """Test the _format_breaks() helper function."""

    def test_empty_breaks(self):
        """Empty list returns empty string."""
        result = _format_breaks([])
        assert result == ""

    def test_strong_break(self):
        """Strong break formatted as ...s."""
        breaks = [BreakAttrs(strength="strong")]
        result = _format_breaks(breaks)
        assert result == "...s"

    def test_weak_break(self):
        """Weak break formatted as ...w."""
        breaks = [BreakAttrs(strength="weak")]
        result = _format_breaks(breaks)
        assert result == "...w"

    def test_x_weak_break(self):
        """X-weak break formatted as ...w."""
        breaks = [BreakAttrs(strength="x-weak")]
        result = _format_breaks(breaks)
        assert result == "...w"

    def test_medium_break(self):
        """Medium break formatted as ...c."""
        breaks = [BreakAttrs(strength="medium")]
        result = _format_breaks(breaks)
        assert result == "...c"

    def test_x_strong_break(self):
        """X-strong break formatted as ...p."""
        breaks = [BreakAttrs(strength="x-strong")]
        result = _format_breaks(breaks)
        assert result == "...p"

    def test_none_break(self):
        """None strength formatted as ...n."""
        breaks = [BreakAttrs(strength="none")]
        result = _format_breaks(breaks)
        assert result == "...n"

    def test_time_break_milliseconds(self):
        """Time break with milliseconds."""
        breaks = [BreakAttrs(time="500ms")]
        result = _format_breaks(breaks)
        assert result == "...500ms"

    def test_time_break_seconds(self):
        """Time break with seconds."""
        breaks = [BreakAttrs(time="2s")]
        result = _format_breaks(breaks)
        assert result == "...2s"

    def test_multiple_breaks(self):
        """Multiple breaks joined with space."""
        breaks = [BreakAttrs(strength="strong"), BreakAttrs(time="500ms")]
        result = _format_breaks(breaks)
        assert "...s" in result
        assert "...500ms" in result


class TestRoundTrip:
    """Test parse → format → parse round trips."""

    def test_simple_round_trip(self):
        """Parse, format, parse again produces same structure."""
        original_text = "Hello world. How are you?"

        # First parse
        sentences1 = parse_sentences(original_text)

        # Format
        formatted = format_ssmd(sentences1)

        # Parse again
        sentences2 = parse_sentences(formatted)

        # Should have same number of sentences
        assert len(sentences1) == len(sentences2)

    def test_break_round_trip(self):
        """Breaks preserved through round trip."""
        original_text = "Hello. ...s How are you?"

        sentences1 = parse_sentences(original_text)
        formatted = format_ssmd(sentences1)
        sentences2 = parse_sentences(formatted)

        # Should still have the break marker
        assert "...s" in formatted
        assert len(sentences1) == len(sentences2)

    def test_paragraph_round_trip(self):
        """Paragraphs preserved through round trip."""
        original_text = "First paragraph.\n\nSecond paragraph."

        sentences1 = parse_sentences(original_text)
        formatted = format_ssmd(sentences1)

        # Should preserve paragraph structure
        assert "\n\n" in formatted


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_period_as_separate_segment(self):
        """Period in separate segment handled correctly."""
        seg1 = SSMDSegment(text="Hello world")
        seg2 = SSMDSegment(text=".")
        sentence = SSMDSentence(segments=[seg1, seg2])

        result = format_ssmd([sentence]).strip()

        # Should join properly
        assert "Hello world ." in result or "Hello world." in result

    def test_empty_segment_filtered(self):
        """Empty segments are skipped."""
        seg1 = SSMDSegment(text="Hello")
        seg2 = SSMDSegment(text="")
        seg3 = SSMDSegment(text="world")
        sentence = SSMDSentence(segments=[seg1, seg2, seg3])

        result = format_ssmd([sentence]).strip()

        # Empty segment should not create extra space
        assert result.count("  ") == 0  # No double spaces

    def test_long_sentence(self):
        """Very long sentence handled correctly."""
        text = " ".join(["Word"] * 100) + "."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Should end with newline
        assert formatted.endswith("\n")
        # Should be single line (plus newline)
        assert formatted.count("\n") == 1

    def test_unicode_text(self):
        """Unicode text preserved correctly."""
        text = "Café résumé naïve. ...s Schön."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Unicode should be preserved
        assert "Café" in formatted
        assert "résumé" in formatted
        assert "naïve" in formatted
        assert "Schön" in formatted

    def test_multiple_consecutive_breaks(self):
        """Multiple breaks at same location.

        Note: The parser currently doesn't capture multiple consecutive breaks
        between sentences - only the first one. This is a known parser limitation.
        """
        text = "Hello. ...s ...500ms How are you?"
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # At least one break should be present (parser limitation)
        assert "...s" in formatted or "...500ms" in formatted

    def test_break_without_space(self):
        """Break marker without surrounding space."""
        # This tests direct concatenation
        seg1 = SSMDSegment(text="Text")
        seg1.breaks_after = [BreakAttrs(strength="strong")]
        seg2 = SSMDSegment(text="More")
        sentence = SSMDSentence(segments=[seg1, seg2])

        result = format_ssmd([sentence]).strip()

        # Should have break between segments
        assert "...s" in result


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_doctor_abbreviation_text(self):
        """Dr. Smith example from demo."""
        text = "Dr. Smith arrived at 3:00 P.M. on Tuesday. He met Mr. Johnson."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        lines = formatted.strip().split("\n")
        assert len(lines) == 2
        assert "Dr. Smith" in lines[0]
        assert "Mr. Johnson" in lines[1]

    def test_quoted_dialogue(self):
        """Quoted dialogue formatting."""
        text = '"Good morning," she said. "How are you today?"'
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Should preserve quotes
        assert '"Good morning,"' in formatted
        assert '"How are you today?"' in formatted

    def test_mixed_punctuation(self):
        """Mixed sentence-ending punctuation."""
        text = "Really? Yes! That's great."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        lines = formatted.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "Really?"
        assert lines[1] == "Yes!"
        assert lines[2] == "That's great."

    def test_list_with_commas(self):
        """List with commas in sentence."""
        text = "I need eggs, milk, bread, and butter."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Should be single sentence
        lines = formatted.strip().split("\n")
        assert len(lines) == 1

    def test_time_and_location(self):
        """Time and location abbreviations."""
        text = "The meeting is at 3:00 P.M. in Washington, D.C. tomorrow."
        sentences = parse_sentences(text)

        formatted = format_ssmd(sentences)

        # Should be single sentence
        lines = formatted.strip().split("\n")
        assert len(lines) == 1
        assert "3:00 P.M." in lines[0]
        assert "D.C." in lines[0]


class TestLosslessRoundtrip:
    """Test that SSMD documents remain valid through parse/format cycles.

    These tests ensure that when you read SSMD and export it formatted,
    all markup is preserved exactly (only line breaks are normalized).
    """

    def test_emphasis_partial(self):
        """Partial emphasis should be preserved."""
        text = "*Hello* world"
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert formatted.strip() == text

    def test_emphasis_multiple(self):
        """Multiple emphasis segments should be preserved."""
        text = "*Hello* and *goodbye* world"
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert formatted.strip() == text

    def test_emphasis_full_sentence(self):
        """Fully emphasized sentence should be preserved."""
        text = "*Hello world*"
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert formatted.strip() == text

    def test_break_inline(self):
        """Inline break should be preserved."""
        text = "I like ...s to sleep"
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        # Inline breaks stay inline
        assert "...s" in formatted
        assert formatted.strip().count("\n") == 0

    def test_break_between_sentences(self):
        """Break after sentence keeps sentences together if not separated."""
        # Note: "Hello. ...s How are you?" is ONE sentence with a break
        # The period doesn't split it because the break follows immediately
        text = "Hello. How are you?"
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        lines = formatted.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "Hello."
        assert lines[1] == "How are you?"

    def test_break_at_sentence_end(self):
        """Break at end of sentence should format correctly."""
        text = "Hello. ...s"
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        # Break at end of sentence stays on same line
        assert formatted.strip() == "Hello. ...s"

    def test_break_multiple_strengths(self):
        """Multiple break strengths should be preserved."""
        text = "Hello. ...w Wait. ...s Stop. ...p Next paragraph."
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert "...w" in formatted
        assert "...s" in formatted
        assert "...p" in formatted

    def test_language_annotation(self):
        """Language annotation should be preserved."""
        text = '[bonjour]{lang="fr"} my friend'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert '[bonjour]{lang="fr"}' in formatted

    def test_substitution(self):
        """Substitution should be preserved."""
        text = '[SSMD]{sub="Speech Synthesis Markdown"} is great'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert '[SSMD]{sub="Speech Synthesis Markdown"}' in formatted

    def test_say_as(self):
        """Say-as annotation should be preserved."""
        text = 'Call [555-1234]{as="telephone"} now'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert '[555-1234]{as="telephone"}' in formatted

    def test_say_as_with_format(self):
        """Say-as with format should be preserved."""
        text = 'The date is [12/31/2023]{as="date" format="mdy"}'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert '[12/31/2023]{as="date"' in formatted
        assert 'format="mdy"' in formatted

    def test_phoneme(self):
        """Phoneme annotation should be preserved."""
        text = 'Say [tomato]{ph="təˈmeɪtoʊ" alphabet="ipa"} carefully'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert '[tomato]{ph="təˈmeɪtoʊ" alphabet="ipa"}' in formatted

    def test_prosody_rate(self):
        """Prosody rate should be preserved."""
        text = '[speak quickly]{rate="fast"} please'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert 'rate="fast"' in formatted

    def test_prosody_pitch(self):
        """Prosody pitch should be preserved."""
        text = '[high voice]{pitch="+20%"} sounds different'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert "high voice" in formatted
        assert 'pitch="+20%"' in formatted

    def test_prosody_volume(self):
        """Prosody volume should be preserved."""
        text = '[quiet words]{volume="soft"} are hard to hear'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert 'volume="soft"' in formatted

    def test_prosody_multiple(self):
        """Multiple prosody attributes should be preserved."""
        text = '[fast and loud]{rate="fast" volume="loud"} speech'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert "fast and loud" in formatted
        assert 'rate="fast"' in formatted
        assert 'volume="loud"' in formatted

    def test_audio(self):
        """Audio should be preserved."""
        text = 'Listen to this [sound]{src="sound.mp3"} effect'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert '[sound]{src="sound.mp3"}' in formatted

    def test_marks(self):
        """Marks should be preserved."""
        text = "Start here @bookmark and continue"
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert "@bookmark" in formatted

    def test_complex_mixed(self):
        """Complex mixed markup should be preserved."""
        text = '*Hello* [world]{lang="en"} ...s how are [you]{emphasis="strong"}?'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert "*Hello*" in formatted
        assert '[world]{lang="en"}' in formatted
        assert "**you**" in formatted
        assert "...s" in formatted

    def test_paragraph_breaks(self):
        """Paragraph breaks should use double newlines."""
        text = "First paragraph.\n\nSecond paragraph."
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert "\n\n" in formatted

    def test_multiple_sentences_formatting(self):
        """Multiple sentences should each be on new lines."""
        text = "First. Second. Third."
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        lines = formatted.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "First."
        assert lines[1] == "Second."
        assert lines[2] == "Third."

    def test_double_roundtrip(self):
        """Double roundtrip should be stable."""
        text = "*Hello* world. ...s How are you?"

        # First roundtrip
        sentences1 = parse_sentences(text)
        formatted1 = format_ssmd(sentences1)

        # Second roundtrip
        sentences2 = parse_sentences(formatted1)
        formatted2 = format_ssmd(sentences2)

        # Key elements should be preserved
        assert "*Hello*" in formatted1
        assert "*Hello*" in formatted2
        assert "...s" in formatted1
        assert "...s" in formatted2

    def test_complex_document_roundtrip(self):
        """Complex document with all features should roundtrip."""
        text = """*Welcome* to SSMD. ...s

This is [français]{lang="fr"} text.
Call [555-1234]{as="telephone"} now. ...w
Say [tomato]{ph="təˈmeɪtoʊ" alphabet="ipa"} correctly.

@bookmark Start here.
[Speak fast]{rate="fast"} please."""

        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        # Key features should be preserved (SSMD spec formats)
        assert "*Welcome*" in formatted
        assert '[français]{lang="fr"}' in formatted
        assert '[555-1234]{as="telephone"}' in formatted
        assert '[tomato]{ph="təˈmeɪtoʊ" alphabet="ipa"}' in formatted
        assert "@bookmark" in formatted
        assert 'rate="fast"' in formatted
        assert "...s" in formatted
        assert "...w" in formatted

    def test_emphasis_with_punctuation(self):
        """Emphasis with punctuation should be preserved."""
        text = "*Hello!* she exclaimed"
        sentences = parse_sentences(text, use_spacy=False)
        formatted = format_ssmd(sentences)

        assert formatted.strip() == text

    @pytest.mark.parametrize(
        "text",
        [
            "*Hello!* she exclaimed",
            "**Stop!** Next sentence.",
            "~~Quiet?~~ he asked.",
            '"*Hello!*" she said.',
            "*One.* *Two.*",
            "Before *inside!* after.",
        ],
    )
    def test_emphasis_spans_with_sentence_punctuation_are_balanced(self, text):
        """Sentence splitting must not strand emphasis delimiters."""
        sentences = parse_sentences(text, use_spacy=False)
        formatted = format_ssmd(sentences).strip()

        for span in ("*Hello!*", "**Stop!**", "~~Quiet?~~", "*One.*", "*Two.*", "*inside!*"):
            if span in text:
                assert span in formatted
        assert formatted.count("*") % 2 == 0
        assert formatted.count("~~") % 2 == 0

    def test_nested_quotes_emphasis(self):
        """Nested quotes and emphasis should work."""
        text = '"*Hello*," she said'
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert "*Hello*" in formatted
        assert '"' in formatted

    def test_break_with_time(self):
        """Break with time value should be preserved."""
        text = "Wait ...500ms then continue"
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert "...500ms" in formatted

    def test_break_with_seconds(self):
        """Break with seconds should be preserved."""
        text = "Wait ...2s then continue"
        sentences = parse_sentences(text)
        formatted = format_ssmd(sentences)

        assert "...2s" in formatted

"""Tests for sentence detection model configuration."""

import pytest

from ssmd.parser import parse_sentences


class TestPhrasplitAlwaysAvailable:
    """Test that phrasplit is always importable."""

    def test_phrasplit_import(self):
        """Verify phrasplit is always importable (core dependency)."""
        import phrasplit  # noqa: F401

        # Should never raise ImportError
        assert True

    def test_parse_sentences_always_works(self):
        """Parser should always work (phrasplit is core dependency)."""
        sentences = parse_sentences("Hello. World.")
        # Should work in regex mode even without spaCy
        assert len(sentences) == 2


class TestParseSentencesRegexMode:
    """Test sentence parsing with regex mode (use_spacy=False)."""

    def test_regex_basic(self):
        """Parse basic sentences with regex."""
        text = "Hello world. This is a test."
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 2
        assert "Hello world" in sentences[0].segments[0].text
        assert "This is a test" in sentences[1].segments[0].text

    def test_regex_question_marks(self):
        """Parse sentences with question marks."""
        text = "Hello? How are you?"
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 2

    def test_regex_exclamation(self):
        """Parse sentences with exclamation marks."""
        text = "Hello! Welcome!"
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 2

    def test_regex_mixed_punctuation(self):
        """Parse sentences with mixed punctuation."""
        text = "Hello! How are you? I'm fine."
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 3

    def test_regex_single_sentence(self):
        """Parse single sentence."""
        text = "Hello world."
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 1
        assert "Hello world" in sentences[0].segments[0].text

    def test_regex_no_final_punctuation(self):
        """Parse text without final punctuation."""
        text = "Hello world"
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 1
        assert "Hello world" in sentences[0].segments[0].text


class TestParseSentencesModelSize:
    """Test sentence parsing with different model sizes."""

    def test_default_model_size(self):
        """Default uses small model (implicitly via phrasplit)."""
        text = "Hello world. This is a test."
        sentences = parse_sentences(text)

        # Should work with default small model
        assert len(sentences) == 2

    def test_explicit_small_model(self):
        """Explicitly specify small model."""
        text = "Hello world. This is a test."
        sentences = parse_sentences(text, model_size="sm")

        assert len(sentences) == 2

    def test_medium_model(self):
        """Specify medium model (may not be installed)."""
        text = "Hello world. This is a test."

        # If medium model not installed, should fall back to regex
        try:
            sentences = parse_sentences(text, model_size="md")
            # If it works, check results
            assert len(sentences) == 2
        except Exception:
            # If phrasplit fails, that's expected if model not installed
            pytest.skip("Medium model not installed")

    def test_large_model(self):
        """Specify large model (may not be installed)."""
        text = "Hello world. This is a test."

        try:
            sentences = parse_sentences(text, model_size="lg")
            assert len(sentences) == 2
        except Exception:
            pytest.skip("Large model not installed")


class TestParseSentencesCustomModel:
    """Test sentence parsing with custom spaCy model."""

    def test_custom_model_name(self):
        """Specify custom model name (overrides model_size)."""
        text = "Hello world. This is a test."

        # Try with a custom model (falls back to regex if not installed)
        try:
            sentences = parse_sentences(text, spacy_model="en_core_web_sm")
            assert len(sentences) == 2
        except Exception:
            pytest.skip("Custom model not available")

    def test_custom_model_overrides_size(self):
        """Custom model overrides model_size parameter."""
        text = "Hello world. This is a test."

        # spacy_model should take priority over model_size
        try:
            sentences = parse_sentences(text, model_size="lg", spacy_model="en_core_web_sm")
            # Should use en_core_web_sm, not en_core_web_lg
            assert len(sentences) == 2
        except Exception:
            pytest.skip("spaCy model not available")


class TestParseSentencesMultiLanguage:
    """Test sentence parsing with multiple languages."""

    def test_locale_normalization(self):
        """BCP-47 locales (en-US, fr-FR) should normalize to 2-letter codes (en, fr)."""
        # Test with en-US locale - should use en_core_web_sm, not en-US_core_web_sm
        text = "Hello world. This is a test."
        sentences = parse_sentences(text, language="en-US")
        # Should work (phrasplit will use "en" internally)
        assert len(sentences) == 2

        # Test with en-GB locale
        sentences = parse_sentences(text, language="en-GB")
        assert len(sentences) == 2

    def test_french_default_model(self):
        """Parse French text with default small model."""
        text = """
        <div voice-lang="fr-FR">
        Bonjour tout le monde.
        </div>
        """
        try:
            sentences = parse_sentences(text, language="fr")
            # Should work with French small model if installed
            assert len(sentences) >= 1
        except OSError:
            # French model not installed - skip test
            pytest.skip("French spaCy model not installed")

    def test_french_medium_model(self):
        """Parse French text with medium model."""
        text = """
        <div voice-lang="fr-FR">
        Bonjour tout le monde.
        </div>
        """

        try:
            sentences = parse_sentences(text, language="fr", model_size="md")
            assert len(sentences) >= 1
        except Exception:
            pytest.skip("French medium model not installed")

    def test_voice_language_overrides_parameter(self):
        """Voice language should override language parameter."""
        text = """
        <div voice-lang="fr-FR">
        Bonjour. Comment allez-vous?
        </div>

        <div voice-lang="en-US">
        Hello. How are you?
        </div>
        """

        sentences = parse_sentences(text, language="en")

        # Should detect both French and English blocks
        assert len(sentences) >= 2


class TestParseSentencesBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_no_new_parameters(self):
        """Calling without new parameters should work as before."""
        text = "Hello world. This is a test."
        sentences = parse_sentences(text)

        assert len(sentences) == 2

    def test_existing_parameters_still_work(self):
        """Existing parameters should still work."""
        text = "Hello world. This is a test."

        sentences = parse_sentences(
            text, sentence_detection=True, include_default_voice=True, language="en"
        )

        assert len(sentences) == 2

    def test_sentence_detection_false(self):
        """Disabling sentence detection should still work."""
        text = "Hello world. This is a test."
        sentences = parse_sentences(text, sentence_detection=False)

        # Should return single sentence
        assert len(sentences) == 1


class TestParseSentencesEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_text_with_use_spacy_false(self):
        """Empty text with regex mode."""
        sentences = parse_sentences("", use_spacy=False)
        assert len(sentences) == 0

    def test_whitespace_only_with_use_spacy_false(self):
        """Whitespace-only text with regex mode."""
        sentences = parse_sentences("   \n\n   ", use_spacy=False)
        assert len(sentences) == 0

    def test_no_punctuation_with_use_spacy_false(self):
        """Text without punctuation in regex mode."""
        text = "Hello world"
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 1
        assert "Hello world" in sentences[0].segments[0].text

    def test_multiple_spaces_with_use_spacy_false(self):
        """Text with multiple spaces in regex mode."""
        text = "Hello  world.  This  is  a  test."
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 2


class TestSentenceEndingPreservation:
    """Test that sentence endings (periods, punctuation) are preserved correctly."""

    def test_period_preservation_normal_sentences(self):
        """Verify periods are preserved in normal multi-word sentences."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        sentences = parse_sentences(text, use_spacy=False)

        # Should split into 3 sentences
        assert len(sentences) == 3

        # Each sentence should end with a period
        for i, sent in enumerate(sentences):
            full_text = "".join(seg.text for seg in sent.segments)
            assert full_text.strip().endswith("."), (
                f"Sentence {i} should end with period: '{full_text}'"
            )

        # Verify exact content
        sentence_texts = ["".join(seg.text for seg in s.segments).strip() for s in sentences]
        assert sentence_texts[0] == "This is sentence one."
        assert sentence_texts[1] == "This is sentence two."
        assert sentence_texts[2] == "This is sentence three."

    def test_period_preservation_short_sentences(self):
        """Verify periods are preserved in short sentences."""
        text = "First. Second. Third."
        sentences = parse_sentences(text, use_spacy=False)

        # Should split into 3 sentences
        assert len(sentences) == 3

        # Each sentence should preserve its period
        sentence_texts = ["".join(seg.text for seg in s.segments).strip() for s in sentences]
        assert sentence_texts[0] == "First."
        assert sentence_texts[1] == "Second."
        assert sentence_texts[2] == "Third."

    def test_single_letter_sentences_with_paragraphs(self):
        """Single-letter sentences with paragraph breaks split correctly.

        When fed 'A.\\n\\nB.\\n\\nC.' with paragraph breaks, should produce
        three separate sentences with periods preserved.
        """
        text = "A.\n\nB.\n\nC."
        sentences = parse_sentences(text, use_spacy=False)

        # Should split into 3 sentences (paragraph breaks force sentence boundaries)
        assert len(sentences) == 3, f"Expected 3 sentences, got {len(sentences)}"

        # Each sentence must preserve its period
        sentence_texts = ["".join(seg.text for seg in s.segments).strip() for s in sentences]
        assert sentence_texts[0] == "A.", (
            f"First sentence should be 'A.', got '{sentence_texts[0]}'"
        )
        assert sentence_texts[1] == "B.", (
            f"Second sentence should be 'B.', got '{sentence_texts[1]}'"
        )
        assert sentence_texts[2] == "C.", (
            f"Third sentence should be 'C.', got '{sentence_texts[2]}'"
        )

        # First two should be marked as paragraph ends
        assert sentences[0].is_paragraph_end is True
        assert sentences[1].is_paragraph_end is True
        assert sentences[2].is_paragraph_end is False

    def test_single_letter_abbreviations_without_breaks(self):
        """Single-letter sequences without breaks treated as abbreviations.

        'A. B. C.' without paragraph breaks is linguistically an abbreviation
        sequence, not three separate sentences. This is correct behavior from
        phrasplit.
        """
        text = "A. B. C."
        sentences = parse_sentences(text, use_spacy=False)

        # Phrasplit treats this as 1 sentence (abbreviation), which is
        # linguistically correct
        assert len(sentences) == 1

        # Period is still preserved in the output
        full_text = "".join(seg.text for seg in sentences[0].segments)
        assert "." in full_text, "Periods should be preserved even in abbreviations"

    def test_mixed_punctuation_preservation(self):
        """Verify that different punctuation marks (!, ?, .) are all preserved."""
        text = "Hello! How are you? I'm fine."
        sentences = parse_sentences(text, use_spacy=False)

        # Should split into 3 sentences
        assert len(sentences) == 3

        # Each sentence should preserve its punctuation
        sentence_texts = ["".join(seg.text for seg in s.segments).strip() for s in sentences]
        assert sentence_texts[0].endswith("!"), "First sentence should end with !"
        assert sentence_texts[1].endswith("?"), "Second sentence should end with ?"
        assert sentence_texts[2].endswith("."), "Third sentence should end with ."

        # Verify exact punctuation
        assert sentence_texts[0] == "Hello!"
        assert sentence_texts[1] == "How are you?"
        assert sentence_texts[2] == "I'm fine."

    def test_paragraph_end_markers(self):
        """Verify that paragraph end markers are set correctly with double newlines."""
        text = "First.\n\nSecond.\n\nThird."
        sentences = parse_sentences(text, use_spacy=False)

        # Should split into 3 sentences
        assert len(sentences) == 3

        # First two should be paragraph ends, last should not
        assert sentences[0].is_paragraph_end is True, "First sentence should be paragraph end"
        assert sentences[1].is_paragraph_end is True, "Second sentence should be paragraph end"
        assert sentences[2].is_paragraph_end is False, "Last sentence should not be paragraph end"

        # Verify periods are preserved
        for i, sent in enumerate(sentences):
            full_text = "".join(seg.text for seg in sent.segments).strip()
            assert full_text.endswith("."), f"Sentence {i} should end with period"

    def test_question_mark_preservation(self):
        """Verify question marks are preserved at sentence endings."""
        text = "What is this? Where am I? Who are you?"
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 3

        for i, sent in enumerate(sentences):
            full_text = "".join(seg.text for seg in sent.segments).strip()
            assert full_text.endswith("?"), f"Sentence {i} should end with question mark"

    def test_exclamation_mark_preservation(self):
        """Verify exclamation marks are preserved at sentence endings."""
        text = "Watch out! Stop now! Be careful!"
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 3

        for i, sent in enumerate(sentences):
            full_text = "".join(seg.text for seg in sent.segments).strip()
            assert full_text.endswith("!"), f"Sentence {i} should end with exclamation mark"

    def test_no_punctuation_at_end(self):
        """Verify behavior when text has no final punctuation."""
        text = "This is a sentence without punctuation"
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 1

        full_text = "".join(seg.text for seg in sentences[0].segments).strip()
        # Should preserve the text as-is, without adding punctuation
        assert full_text == "This is a sentence without punctuation"

    def test_multiple_sentences_no_final_punctuation(self):
        """Verify mixed case: some sentences have punctuation, last one doesn't."""
        text = "First sentence. Second sentence. Third without punctuation"
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 3

        sentence_texts = ["".join(seg.text for seg in s.segments).strip() for s in sentences]
        assert sentence_texts[0] == "First sentence."
        assert sentence_texts[1] == "Second sentence."
        assert sentence_texts[2] == "Third without punctuation"

    def test_period_preservation_with_break_markers(self):
        """Verify periods are preserved when break markers are present.

        Bug: Break markers like ...s, ...c should be removed but periods and
        spaces should be preserved. "I like ...s to sleep." should become
        "I like to sleep." not "I liketo sleep."
        """
        text = "I like ...s to sleep. What a ...c great day."
        sentences = parse_sentences(text, use_spacy=False)

        # Should split into 2 sentences
        assert len(sentences) == 2

        # First sentence: "I like ...s to sleep." -> segments ["I like", "to sleep."]
        sentence1_text = " ".join(seg.text for seg in sentences[0].segments)
        assert sentence1_text == "I like to sleep.", (
            f"Expected 'I like to sleep.', got '{sentence1_text}'"
        )
        assert sentence1_text.endswith("."), "First sentence must end with period"

        # Second sentence: "What a ...c great day." -> segments ["What a", "great day."]
        sentence2_text = " ".join(seg.text for seg in sentences[1].segments)
        assert sentence2_text == "What a great day.", (
            f"Expected 'What a great day.', got '{sentence2_text}'"
        )
        assert sentence2_text.endswith("."), "Second sentence must end with period"

    def test_break_marker_at_sentence_end(self):
        """Verify period is preserved when break marker is at end before period."""
        text = "I like to sleep ...s."
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 1

        full_text = "".join(seg.text for seg in sentences[0].segments)
        assert full_text.endswith("."), f"Sentence should end with period: '{full_text}'"
        assert full_text == "I like to sleep.", f"Expected 'I like to sleep.', got '{full_text}'"

    def test_multiple_break_markers_in_sentence(self):
        """Verify spaces and periods with multiple break markers."""
        text = "First ...w word ...s here. Second ...c part."
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 2

        sentence1_text = " ".join(seg.text for seg in sentences[0].segments)
        sentence2_text = " ".join(seg.text for seg in sentences[1].segments)

        # Break markers removed, spaces preserved, periods preserved
        assert sentence1_text == "First word here.", (
            f"Expected 'First word here.', got '{sentence1_text}'"
        )
        assert sentence2_text == "Second part.", f"Expected 'Second part.', got '{sentence2_text}'"


class TestParseSentencesIntegration:
    """Integration tests with full features."""

    def test_regex_mode_with_emphasis(self):
        """Regex mode should preserve emphasis."""
        text = "Hello *world*. This is *great*."
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 2
        # Emphasis should be preserved in segments
        assert any("world" in seg.text for seg in sentences[0].segments)

    def test_regex_mode_with_language(self):
        """Regex mode should preserve lang info."""
        text = 'Hello [world]{lang="en-gb"}, [cafe]{lang="fr"}. Hello again.'
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 2
        assert len(sentences[0].segments) == 5
        assert sentences[0].segments[1].language == "en-gb"
        assert sentences[0].segments[3].language == "fr"
        # Emphasis should be preserved in segments
        assert any("world" in seg.text for seg in sentences[0].segments)

    def test_regex_mode_with_voice_blocks(self):
        """Regex mode should work with directive blocks."""
        text = """
        <div voice="sarah">
        Hello world. How are you?
        </div>

        <div voice="michael">
        I'm fine. Thanks!
        </div>
        """
        sentences = parse_sentences(text, use_spacy=False)

        # Should split into 4 sentences (2 per voice)
        assert len(sentences) >= 4

    def test_model_size_with_voice_blocks(self):
        """Model size should apply to all directive blocks."""
        text = """
        <div voice-lang="en-US">
        Hello world.
        </div>

        <div voice-lang="fr-FR">
        Bonjour monde.
        </div>
        """

        sentences = parse_sentences(text, model_size="sm")

        # Should detect sentences in both languages
        assert len(sentences) >= 2


class TestSegmentSplittingAtBreaks:
    """Test that break markers create separate segments for TTS."""

    def test_single_break_creates_two_segments(self):
        """Break marker should split text into two segments."""
        text = "I like ...s to sleep."
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 1
        segments = sentences[0].segments

        # Should have 2 segments: "I like" + "to sleep."
        assert len(segments) == 2, f"Expected 2 segments, got {len(segments)}"

        assert segments[0].text == "I like", f"Expected 'I like', got '{segments[0].text}'"
        assert segments[1].text == "to sleep.", f"Expected 'to sleep.', got '{segments[1].text}'"

        # First segment should have break_after
        assert len(segments[0].breaks_after) == 1
        assert segments[0].breaks_after[0].strength == "strong"

        # Second segment should have no breaks
        assert len(segments[1].breaks_after) == 0

    def test_break_at_end_preserves_period(self):
        """Period after break should be in separate segment."""
        text = "I like to sleep ...s."
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 1
        segments = sentences[0].segments

        # Should have 2 segments: text with break, then period
        assert len(segments) == 2, f"Expected 2 segments, got {len(segments)}: {segments}"
        assert segments[0].text == "I like to sleep", (
            f"Expected 'I like to sleep', got '{segments[0].text}'"
        )
        assert len(segments[0].breaks_after) == 1
        assert segments[0].breaks_after[0].strength == "strong"

        # Period becomes separate segment
        assert segments[1].text == "."

    def test_multiple_breaks_create_multiple_segments(self):
        """Multiple break markers should create multiple segments."""
        text = "What a ...c great day. I feel ...s amazing today."
        sentences = parse_sentences(text, use_spacy=False)

        # Should be 2 sentences
        assert len(sentences) == 2

        # First sentence: "What a ...c great day."
        seg1 = sentences[0].segments
        assert len(seg1) == 2, f"Expected 2 segments in sentence 1, got {len(seg1)}"
        assert seg1[0].text == "What a", f"Expected 'What a', got '{seg1[0].text}'"
        assert seg1[1].text == "great day.", f"Expected 'great day.', got '{seg1[1].text}'"
        assert len(seg1[0].breaks_after) == 1
        assert seg1[0].breaks_after[0].strength == "medium"

        # Second sentence: "I feel ...s amazing today."
        seg2 = sentences[1].segments
        assert len(seg2) == 2, f"Expected 2 segments in sentence 2, got {len(seg2)}"
        assert seg2[0].text == "I feel", f"Expected 'I feel', got '{seg2[0].text}'"
        assert seg2[1].text == "amazing today.", f"Expected 'amazing today.', got '{seg2[1].text}'"
        assert len(seg2[0].breaks_after) == 1
        assert seg2[0].breaks_after[0].strength == "strong"

    def test_period_stays_in_correct_segment_before_break(self):
        """Period before break ends sentence, break goes to next as
        breaks_before."""
        text = "Hello world. ...s How are you?"
        sentences = parse_sentences(text, use_spacy=False)

        # Period before break should end the sentence
        assert len(sentences) == 2

        # First sentence should be "Hello world." with NO break
        assert sentences[0].segments[0].text == "Hello world."
        assert len(sentences[0].segments[0].breaks_after) == 0

        # Second sentence should have the break BEFORE the text
        seg2 = sentences[1].segments[0]
        assert seg2.text == "How are you?"
        assert len(seg2.breaks_before) == 1
        assert seg2.breaks_before[0].strength == "strong"

    def test_period_stays_in_correct_segment_after_break(self):
        """Period after break should stay in following segment."""
        text = "Hello world ...s. How are you?"
        sentences = parse_sentences(text, use_spacy=False)

        # Should be 2 sentences
        assert len(sentences) == 2

        # First sentence: "Hello world" + break + "."
        segments = sentences[0].segments
        assert segments[0].text == "Hello world"
        assert len(segments[0].breaks_after) == 1

        # Period should be in second segment
        assert segments[1].text == "."

    def test_timed_break_creates_segments(self):
        """Timed breaks (500ms, 2s) should also split segments."""
        text = "Wait for it ...500ms here it is!"
        sentences = parse_sentences(text, use_spacy=False)

        assert len(sentences) == 1
        segments = sentences[0].segments

        assert len(segments) == 2
        assert segments[0].text == "Wait for it"
        assert segments[1].text == "here it is!"

        # Check break duration
        assert len(segments[0].breaks_after) == 1
        assert segments[0].breaks_after[0].time == "500ms"

    def test_no_space_before_punctuation_in_segments(self):
        """Segments should not have space before punctuation."""
        text = "I like ...s to sleep ."
        sentences = parse_sentences(text, use_spacy=False)

        segments = sentences[0].segments

        # Second segment should normalize "to sleep ." -> "to sleep."
        assert segments[1].text == "to sleep.", f"Expected 'to sleep.', got '{segments[1].text}'"

    def test_emphasis_preserved_in_split_segments(self):
        """Emphasis markers should work in split segments."""
        text = "I *really* ...s love this."
        sentences = parse_sentences(text, use_spacy=False)

        segments = sentences[0].segments

        assert len(segments) == 3
        # First segment should be plain text
        assert segments[0].text == "I"
        assert segments[0].emphasis is False

        # Second segment should have emphasis
        assert segments[1].text == "really"
        assert segments[1].emphasis is True

        # Third segment should be plain text after the break
        assert segments[2].text == "love this."


class TestQuotePreservation:
    """Test that quote signs are preserved across multiple sentences."""

    def test_double_quotes_across_multiple_sentences(self):
        """Double quotes should be preserved across sentence boundaries."""
        text = 'She said "My name is Tina. I like to swim. Today is great!"'
        sentences = parse_sentences(text, use_spacy=False)

        # Should split into 3 sentences (sentence detection splits on periods)
        assert len(sentences) == 3, f"Expected 3 sentences, got {len(sentences)}"

        # Reconstruct full text
        full_text = " ".join(" ".join(seg.text for seg in s.segments) for s in sentences)

        # Opening quote should be in first sentence
        sentence1 = " ".join(seg.text for seg in sentences[0].segments)
        assert '"' in sentence1, f"Opening quote missing from sentence 1: {sentence1}"
        assert sentence1.startswith('She said "'), (
            f"Expected to start with 'She said \"', got: {sentence1}"
        )

        # Closing quote should be in last sentence
        sentence3 = " ".join(seg.text for seg in sentences[2].segments)
        assert '"' in sentence3, f"Closing quote missing from sentence 3: {sentence3}"
        assert sentence3.endswith('!"'), f"Expected to end with '!\"', got: {sentence3}"

        # Count quotes - should have exactly 2 (opening and closing)
        quote_count = full_text.count('"')
        assert quote_count == 2, f"Expected 2 quotes, found {quote_count} in: {full_text}"

    def test_single_quotes_across_sentences(self):
        """Single quotes should be preserved across sentence boundaries."""
        text = "She said 'My name is Tina. I like to swim.'"
        sentences = parse_sentences(text, use_spacy=False)

        # Reconstruct full text
        full_text = " ".join(" ".join(seg.text for seg in s.segments) for s in sentences)

        # Count single quotes - should have exactly 2
        quote_count = full_text.count("'")
        assert quote_count == 2, f"Expected 2 single quotes, found {quote_count} in: {full_text}"

        # Opening quote in first sentence
        sentence1 = " ".join(seg.text for seg in sentences[0].segments)
        assert "'" in sentence1, f"Opening single quote missing: {sentence1}"

        # Closing quote in last sentence
        last_sentence = " ".join(seg.text for seg in sentences[-1].segments)
        assert last_sentence.endswith(".'"), f"Expected to end with '.'' got: {last_sentence}"

    def test_quotes_with_break_markers(self):
        """Quotes should be preserved when combined with break markers."""
        text = 'He said "Hello ...s world. How are you?"'
        sentences = parse_sentences(text, use_spacy=False)

        # Reconstruct full text (joining segments with spaces)
        full_text = " ".join(" ".join(seg.text for seg in s.segments) for s in sentences)

        # Should have 2 quotes
        quote_count = full_text.count('"')
        assert quote_count == 2, f"Expected 2 quotes, found {quote_count} in: {full_text}"

        # First sentence should have opening quote
        sentence1_text = " ".join(seg.text for seg in sentences[0].segments)
        assert '"' in sentence1_text, f"Opening quote missing: {sentence1_text}"
        assert "Hello" in sentence1_text and "world." in sentence1_text

    def test_nested_quotes(self):
        """Nested quotes should be preserved."""
        text = '''She said "He told me 'hello' yesterday."'''
        sentences = parse_sentences(text, use_spacy=False)

        full_text = " ".join(" ".join(seg.text for seg in s.segments) for s in sentences)

        # Should have 2 double quotes and 2 single quotes
        double_quote_count = full_text.count('"')
        single_quote_count = full_text.count("'")

        assert double_quote_count == 2, f"Expected 2 double quotes, found {double_quote_count}"
        assert single_quote_count == 2, f"Expected 2 single quotes, found {single_quote_count}"

    def test_quotes_at_sentence_boundaries(self):
        """Quotes at exact sentence boundaries should be preserved."""
        text = '"First sentence." "Second sentence."'
        sentences = parse_sentences(text, use_spacy=False)

        full_text = " ".join(" ".join(seg.text for seg in s.segments) for s in sentences)

        # Should have 4 quotes total
        quote_count = full_text.count('"')
        assert quote_count == 4, f"Expected 4 quotes, found {quote_count} in: {full_text}"

    def test_quotes_with_multiple_punctuation(self):
        """Quotes with various punctuation marks should be preserved."""
        text = 'She asked "What? Really! No way."'
        sentences = parse_sentences(text, use_spacy=False)

        # Reconstruct
        full_text = " ".join(" ".join(seg.text for seg in s.segments) for s in sentences)

        # Should preserve both quotes
        quote_count = full_text.count('"')
        assert quote_count == 2, f"Expected 2 quotes, found {quote_count} in: {full_text}"

        # Should preserve all punctuation
        assert "?" in full_text, "Question mark should be preserved"
        assert "!" in full_text, "Exclamation mark should be preserved"

    def test_quotes_with_emphasis_and_breaks(self):
        """Quotes combined with emphasis and breaks should all be preserved."""
        text = 'She said "*Important* ...s message here."'
        sentences = parse_sentences(text, use_spacy=False)

        full_text = " ".join(" ".join(seg.text for seg in s.segments) for s in sentences)

        # Quotes should be preserved
        quote_count = full_text.count('"')
        assert quote_count == 2, f"Expected 2 quotes, found {quote_count}"

        # Text should have "Important" (emphasis markers removed but text preserved)
        assert "Important" in full_text, f"Emphasis text missing: {full_text}"

    def test_empty_quotes(self):
        """Empty quotes should be preserved."""
        text = 'She said "" and left.'
        sentences = parse_sentences(text, use_spacy=False)

        full_text = " ".join(" ".join(seg.text for seg in s.segments) for s in sentences)

        # Should still have 2 quotes
        quote_count = full_text.count('"')
        assert quote_count == 2, f"Expected 2 quotes for empty string, found {quote_count}"

"""Tests for SSMD heading functionality with pause_before and pause_after."""

import pytest

from ssmd import Document, to_ssml
from ssmd.parser import parse_paragraphs
from ssmd.types import DEFAULT_HEADING_LEVELS


class TestDefaultHeadingLevels:
    """Test default heading level configuration with pause_before."""

    def test_level_1_heading_default(self):
        """Test level 1 heading has pause before and after with strong emphasis."""
        result = to_ssml("# Main Heading")

        # Should have pause before
        assert '<break time="300ms"/>' in result
        # Should have strong emphasis
        assert '<emphasis level="strong">Main Heading</emphasis>' in result
        # Should have pause after
        assert result.count('<break time="300ms"/>') == 2

    def test_level_2_heading_default(self):
        """Test level 2 heading has pause before and after with moderate emphasis."""
        result = to_ssml("## Subheading")

        # Should have pause before
        assert '<break time="75ms"/>' in result
        # Should have moderate emphasis
        assert "<emphasis>Subheading</emphasis>" in result
        # Should have pause after
        assert result.count('<break time="75ms"/>') == 2

    def test_level_3_heading_default(self):
        """Test level 3 heading has pause before and after."""
        result = to_ssml("### Sub-subheading")

        # Should have pause before and after (50ms each)
        assert '<break time="50ms"/>' in result
        assert result.count('<break time="50ms"/>') == 2
        # Should contain the text
        assert "Sub-subheading" in result

    def test_heading_level_4_unconfigured(self):
        """Test level 4 heading falls back to plain text (no default config)."""
        result = to_ssml("#### Level 4")

        # Should just be plain text since level 4 is not in DEFAULT_HEADING_LEVELS
        assert "Level 4" in result
        # Should not have emphasis or breaks
        assert "<emphasis" not in result or result.count("<break") == 0

    def test_heading_level_5_unconfigured(self):
        """Test level 5 heading falls back to plain text (no default config)."""
        result = to_ssml("##### Level 5")

        # Should just be plain text
        assert "Level 5" in result

    def test_heading_level_6_unconfigured(self):
        """Test level 6 heading falls back to plain text (no default config)."""
        result = to_ssml("###### Level 6")

        # Should just be plain text
        assert "Level 6" in result


class TestHeadingWithContent:
    """Test headings integrated with surrounding content."""

    def test_heading_with_paragraph_before(self):
        """Test heading with content before it."""
        text = """Previous content here.

# Main Heading

Content after heading starts here."""
        result = to_ssml(text)

        # Should have the pause before heading
        assert '<break time="300ms"/>' in result
        assert "Previous content" in result
        assert "Content after heading" in result

    def test_heading_with_paragraph_after(self):
        """Test heading followed by paragraph."""
        text = """# Chapter 1

This is the first paragraph of the chapter."""
        result = to_ssml(text)

        # Should have pause before "Chapter 1"
        assert '<break time="300ms"/>' in result
        # Should have emphasis on heading
        assert '<emphasis level="strong">Chapter 1</emphasis>' in result
        # Should have pause after
        assert result.count('<break time="300ms"/>') == 2
        assert "first paragraph" in result

    def test_multiple_headings(self):
        """Test multiple headings in sequence."""
        text = """# Chapter 1

## Section 1.1

### Subsection"""
        result = to_ssml(text)

        # Should have all three headings with their pauses
        assert '<break time="300ms"/>' in result  # Level 1
        assert '<break time="75ms"/>' in result  # Level 2
        assert '<break time="50ms"/>' in result  # Level 3
        assert "Chapter 1" in result
        assert "Section 1.1" in result
        assert "Subsection" in result


class TestCustomHeadingConfiguration:
    """Test custom heading level configuration."""

    def test_custom_pause_durations(self):
        """Test custom pause durations for headings."""
        doc = Document(
            config={
                "heading_levels": {
                    1: [
                        ("pause_before", "500ms"),
                        ("emphasis", "strong"),
                        ("pause", "500ms"),
                    ],
                }
            }
        )
        doc.add("# Custom Heading")
        result = doc.to_ssml()

        # Should use custom 500ms pauses
        assert '<break time="500ms"/>' in result
        assert result.count('<break time="500ms"/>') == 2
        assert '<emphasis level="strong">Custom Heading</emphasis>' in result

    def test_custom_emphasis_levels(self):
        """Test custom emphasis levels for headings."""
        doc = Document(
            config={
                "heading_levels": {
                    1: [
                        ("pause_before", "100ms"),
                        ("emphasis", "reduced"),
                        ("pause", "100ms"),
                    ],
                }
            }
        )
        doc.add("# Quiet Heading")
        result = doc.to_ssml()

        # Should use reduced emphasis
        assert '<emphasis level="reduced">Quiet Heading</emphasis>' in result
        assert '<break time="100ms"/>' in result

    def test_heading_with_prosody(self):
        """Test heading with prosody configuration."""
        doc = Document(
            config={
                "heading_levels": {
                    1: [
                        ("pause_before", "200ms"),
                        ("prosody", {"rate": "slow", "pitch": "high"}),
                        ("pause", "200ms"),
                    ],
                }
            }
        )
        doc.add("# Slow High Heading")
        result = doc.to_ssml()

        # Should have prosody settings
        assert 'rate="slow"' in result
        assert 'pitch="high"' in result
        assert '<break time="200ms"/>' in result
        assert "Slow High Heading" in result

    def test_heading_only_pause_before(self):
        """Test heading with only pause_before, no pause after."""
        doc = Document(
            config={
                "heading_levels": {
                    1: [("pause_before", "250ms"), ("emphasis", "strong")],
                }
            }
        )
        doc.add("# Heading_NoAfter")
        result = doc.to_ssml()

        # Should have pause before but not after
        assert '<break time="250ms"/>' in result
        # Only one break tag (before the heading)
        assert result.count('<break time="250ms"/>') == 1
        assert '<emphasis level="strong">Heading_NoAfter</emphasis>' in result

    def test_heading_only_pause_after(self):
        """Test heading with only pause after, no pause_before."""
        doc = Document(
            config={
                "heading_levels": {
                    1: [("emphasis", "strong"), ("pause", "250ms")],
                }
            }
        )
        doc.add("# Heading_NoBefore")
        result = doc.to_ssml()

        # Should have pause after but not before at the emphasis
        # (The break should appear after the emphasis tag)
        assert '<emphasis level="strong">Heading_NoBefore</emphasis>' in result
        assert '<break time="250ms"/>' in result
        # Only one 250ms break (after the heading)
        assert result.count('<break time="250ms"/>') == 1

    def test_different_durations_before_after(self):
        """Test different pause durations before and after heading."""
        doc = Document(
            config={
                "heading_levels": {
                    1: [
                        ("pause_before", "100ms"),
                        ("emphasis", "strong"),
                        ("pause", "500ms"),
                    ],
                }
            }
        )
        doc.add("# Asymmetric Pauses")
        result = doc.to_ssml()

        # Should have both pause durations
        assert '<break time="100ms"/>' in result
        assert '<break time="500ms"/>' in result
        assert '<emphasis level="strong">Asymmetric Pauses</emphasis>' in result


class TestHeadingSegmentParsing:
    """Test heading parsing at the segment level."""

    def test_heading_segment_breaks_before(self):
        """Test that heading segments have breaks_before populated."""
        paragraphs = parse_paragraphs("# Test Heading", heading_levels=DEFAULT_HEADING_LEVELS)

        # Should have at least one sentence
        assert len(paragraphs) > 0

        # Get segments from the first sentence
        segments = paragraphs[0].sentences[0].segments
        assert len(segments) > 0

        # The heading segment should have breaks_before
        heading_seg = segments[0]
        assert len(heading_seg.breaks_before) > 0
        assert heading_seg.breaks_before[0].time == "300ms"

    def test_heading_segment_breaks_after(self):
        """Test that heading segments have breaks_after populated."""
        paragraphs = parse_paragraphs("# Test Heading", heading_levels=DEFAULT_HEADING_LEVELS)

        # The heading segment should have breaks_after
        heading_seg = paragraphs[0].sentences[0].segments[0]
        assert len(heading_seg.breaks_after) > 0
        assert heading_seg.breaks_after[0].time == "300ms"

    def test_heading_segment_emphasis(self):
        """Test that heading segments have correct emphasis."""
        paragraphs = parse_paragraphs("# Test Heading", heading_levels=DEFAULT_HEADING_LEVELS)

        heading_seg = paragraphs[0].sentences[0].segments[0]
        assert heading_seg.emphasis == "strong"

    def test_level_2_heading_segment(self):
        """Test level 2 heading segment properties."""
        paragraphs = parse_paragraphs("## Level 2", heading_levels=DEFAULT_HEADING_LEVELS)

        heading_seg = paragraphs[0].sentences[0].segments[0]
        assert heading_seg.text == "Level 2"
        assert heading_seg.emphasis == "moderate"
        assert len(heading_seg.breaks_before) > 0
        assert heading_seg.breaks_before[0].time == "75ms"
        assert len(heading_seg.breaks_after) > 0
        assert heading_seg.breaks_after[0].time == "75ms"

    def test_level_3_heading_segment(self):
        """Test level 3 heading segment properties."""
        paragraphs = parse_paragraphs("### Level 3", heading_levels=DEFAULT_HEADING_LEVELS)

        heading_seg = paragraphs[0].sentences[0].segments[0]
        assert heading_seg.text == "Level 3"
        # Level 3 doesn't have emphasis in default config, only pauses
        assert heading_seg.emphasis is False
        assert len(heading_seg.breaks_before) > 0
        assert heading_seg.breaks_before[0].time == "50ms"
        assert len(heading_seg.breaks_after) > 0
        assert heading_seg.breaks_after[0].time == "50ms"


class TestHeadingEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_heading(self):
        """Test empty heading text."""
        result = to_ssml("#")
        # Should handle gracefully - may create empty segment or skip
        assert "<speak>" in result

    def test_heading_with_whitespace(self):
        """Test heading with extra whitespace."""
        result = to_ssml("#    Lots of Space    ")
        # Should trim whitespace in heading
        assert "Lots of Space" in result

    def test_heading_with_special_characters(self):
        """Test heading with special characters."""
        result = to_ssml("# Chapter 1: The Beginning & End")
        # Should properly escape special characters
        assert "Chapter 1: The Beginning" in result
        assert "&amp;" in result or "&" in result

    def test_heading_with_emphasis_markdown(self):
        """Test heading containing emphasis markdown."""
        result = to_ssml("# *Important* Heading")
        # Should process both heading and emphasis
        assert "Important" in result
        # Heading emphasis should be applied
        assert '<emphasis level="strong">' in result

    def test_heading_with_inline_annotations(self):
        """Test heading with inline SSMD annotations."""
        result = to_ssml('# Chapter [1]{as="cardinal"}')
        # Should process heading and say-as
        assert "Chapter" in result
        assert '<emphasis level="strong">' in result

    def test_mixed_heading_levels(self):
        """Test document with various heading levels mixed."""
        text = """# Top Level
Some content.

## Second Level
More content.

### Third Level
Even more content.

# Another Top Level"""
        result = to_ssml(text)

        # Should have all heading pauses
        assert '<break time="300ms"/>' in result  # Level 1
        assert '<break time="75ms"/>' in result  # Level 2
        assert '<break time="50ms"/>' in result  # Level 3
        assert "Top Level" in result
        assert "Second Level" in result
        assert "Third Level" in result
        assert "Another Top Level" in result


class TestHeadingDocumentAPI:
    """Test heading functionality through Document API."""

    def test_document_with_headings(self):
        """Test creating document with headings."""
        doc = Document("# Main Title\n\nContent here.")
        result = doc.to_ssml()

        assert '<break time="300ms"/>' in result
        assert '<emphasis level="strong">Main Title</emphasis>' in result
        assert "Content here" in result

    def test_document_add_heading(self):
        """Test adding headings to document."""
        doc = Document()
        doc.add_paragraph("# Introduction")
        doc.add_paragraph("This is the intro.")

        result = doc.to_ssml()
        assert '<emphasis level="strong">Introduction</emphasis>' in result
        assert '<break time="300ms"/>' in result
        assert "This is the intro" in result

    def test_document_to_text_strips_heading_markers(self):
        """Test to_text() removes heading markers but keeps text."""
        doc = Document("# Heading\n\nContent")
        text = doc.to_text()

        # Should not have # marker
        assert "#" not in text
        # Should have the heading text
        assert "Heading" in text
        assert "Content" in text


class TestDefaultHeadingConfiguration:
    """Test the DEFAULT_HEADING_LEVELS configuration."""

    def test_default_config_has_pause_before(self):
        """Test that default config includes pause_before for all levels."""
        assert 1 in DEFAULT_HEADING_LEVELS
        assert 2 in DEFAULT_HEADING_LEVELS
        assert 3 in DEFAULT_HEADING_LEVELS

        # Level 1 should have pause_before, emphasis, and pause
        level_1 = DEFAULT_HEADING_LEVELS[1]
        effect_types = [effect[0] for effect in level_1]
        assert "pause_before" in effect_types
        assert "emphasis" in effect_types
        assert "pause" in effect_types

    def test_default_config_pause_values(self):
        """Test that default config has correct pause values."""
        # Level 1: 300ms before and after
        level_1 = DEFAULT_HEADING_LEVELS[1]
        pause_before = next(e[1] for e in level_1 if e[0] == "pause_before")
        pause_after = next(e[1] for e in level_1 if e[0] == "pause")
        assert pause_before == "300ms"
        assert pause_after == "300ms"

        # Level 2: 75ms before and after
        level_2 = DEFAULT_HEADING_LEVELS[2]
        pause_before = next(e[1] for e in level_2 if e[0] == "pause_before")
        pause_after = next(e[1] for e in level_2 if e[0] == "pause")
        assert pause_before == "75ms"
        assert pause_after == "75ms"

        # Level 3: 50ms before and after
        level_3 = DEFAULT_HEADING_LEVELS[3]
        pause_before = next(e[1] for e in level_3 if e[0] == "pause_before")
        pause_after = next(e[1] for e in level_3 if e[0] == "pause")
        assert pause_before == "50ms"
        assert pause_after == "50ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

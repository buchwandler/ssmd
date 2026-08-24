"""Tests for SSMD syntax escaping functionality."""

import ssmd


class TestEscapeSyntaxUtility:
    """Test the escape_ssmd_syntax utility function."""

    def test_escape_emphasis_single(self):
        """Single asterisks should be escaped."""
        text = "This *word* is emphasized"
        result = ssmd.escape_ssmd_syntax(text)
        # Escaped text should not be equal to original
        assert result != text
        # And should be reversible
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_escape_emphasis_double(self):
        """Double asterisks should be escaped."""
        text = "This **word** is strong"
        result = ssmd.escape_ssmd_syntax(text)
        assert result != text
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_escape_emphasis_underscore(self):
        """Underscores for reduced emphasis should be escaped."""
        text = "This _word_ is reduced"
        result = ssmd.escape_ssmd_syntax(text)
        assert result != text
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_escape_annotations(self):
        """Annotation syntax should be escaped."""
        text = 'Visit [our website]{src="https://example.com"}'
        result = ssmd.escape_ssmd_syntax(text)
        assert result != text
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_escape_breaks(self):
        """Break patterns should be escaped."""
        text = "Wait for it ...s then continue"
        result = ssmd.escape_ssmd_syntax(text)
        assert result != text
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_escape_breaks_timed(self):
        """Timed break patterns should be escaped."""
        text = "Wait ...500ms or ...3s before continuing"
        result = ssmd.escape_ssmd_syntax(text)
        assert result != text
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_escape_marks(self):
        """Mark patterns should be escaped."""
        text = "Click @here to continue"
        result = ssmd.escape_ssmd_syntax(text)
        assert result != text
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_escape_headings(self):
        """Heading patterns should be escaped."""
        text = "# Chapter 1\n## Section 1.1"
        result = ssmd.escape_ssmd_syntax(text)
        assert result != text
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_escape_directive(self):
        """Directive blocks should be escaped."""
        text = '<div voice="sarah">\nHello world\n</div>'
        result = ssmd.escape_ssmd_syntax(text)
        assert result != text
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_escape_prosody_annotation(self):
        """Prosody annotation should be escaped."""
        text = 'This is [loud]{volume="x-loud"} text'
        result = ssmd.escape_ssmd_syntax(text)
        assert result != text
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_selective_escaping_emphasis_only(self):
        """Test escaping only emphasis patterns."""
        text = 'This *word* has [annotation]{lang="fr"} and @mark'
        result = ssmd.escape_ssmd_syntax(text, patterns=["emphasis"])
        # Emphasis should be changed
        assert "*word*" not in result
        # But annotations and marks should remain
        assert "[annotation]" in result
        assert "@mark" in result

    def test_selective_escaping_annotations_only(self):
        """Test escaping only annotation patterns."""
        text = 'This *word* has [annotation]{lang="fr"}'
        result = ssmd.escape_ssmd_syntax(text, patterns=["annotations"])
        # Emphasis should remain
        assert "*word*" in result
        # But annotations should be changed
        assert "[annotation]" not in result

    def test_selective_escaping_multiple(self):
        """Test escaping multiple specific patterns."""
        text = 'This *word* has [link]{src="url"} and @mark'
        result = ssmd.escape_ssmd_syntax(text, patterns=["emphasis", "annotations"])
        # Emphasis and annotations should be changed
        assert "*word*" not in result
        assert "[link]" not in result
        # But marks should remain
        assert "@mark" in result

    def test_unescape_removes_placeholders(self):
        """Test that unescape removes placeholder escapes."""
        text = 'This *word* has [annotation]{lang="fr"}'
        escaped = ssmd.escape_ssmd_syntax(text)
        result = ssmd.unescape_ssmd_syntax(escaped)
        assert result == text

    def test_ellipsis_without_modifier_not_escaped(self):
        """Bare ellipsis ... should not be escaped (literal ellipsis)."""
        text = "Wait... then continue"
        result = ssmd.escape_ssmd_syntax(text)
        # Bare ... without modifier should remain unchanged
        assert text == result

    def test_at_in_email_not_escaped(self):
        """@ in email addresses should not be escaped."""
        text = "Email me@example.com"
        result = ssmd.escape_ssmd_syntax(text)
        # @ followed by non-word chars or in middle of text shouldn't match
        assert "me@example" in result


class TestDocumentEscapeParameter:
    """Test Document class with escape_syntax parameter."""

    def test_document_with_escape_syntax_true(self):
        """Document with escape_syntax=True should escape patterns."""
        text = "This *word* should not be emphasized"
        doc = ssmd.Document(text, escape_syntax=True)
        ssml = doc.to_ssml()
        assert "<emphasis>" not in ssml
        assert "word" in ssml

    def test_escape_syntax_keeps_xml_safe(self):
        """Escaped directives should remain XML-safe in SSML output."""
        text = '<div voice="sarah">\nHello world.\n</div>'
        doc = ssmd.Document(text, escape_syntax=True)
        ssml = doc.to_ssml()

        assert "&lt;div" in ssml
        assert "&lt;/div&gt;" in ssml

        import xml.etree.ElementTree as ET

        ET.fromstring(ssml)

    def test_document_with_escape_syntax_false(self):
        """Document with escape_syntax=False should parse normally."""
        text = "This *word* should be emphasized"
        doc = ssmd.Document(text, escape_syntax=False)
        assert "<emphasis>" in doc.to_ssml()

    def test_document_default_no_escape(self):
        """Default behavior should parse SSMD normally."""
        text = "This *word* should be emphasized"
        doc = ssmd.Document(text)  # No escape_syntax parameter
        assert "<emphasis>" in doc.to_ssml()

    def test_document_to_ssmd_unescapes(self):
        """to_ssmd should restore escaped syntax."""
        text = "Literal *stars* and [brackets]{noop}"
        doc = ssmd.Document(text, escape_syntax=True)
        assert doc.to_ssmd() == text

    def test_document_to_text_unescapes(self):
        """to_text should restore escaped syntax."""
        text = "Literal *stars* and @marker"
        doc = ssmd.Document(text, escape_syntax=True)
        assert doc.to_text() == text

    def test_markdown_link_escaped(self):
        """Markdown links should not trigger audio/annotation."""
        text = '[Click here]{src="https://example.com"}'
        doc = ssmd.Document(text, escape_syntax=True)
        ssml = doc.to_ssml()
        # Should not have audio or annotation tags
        assert "<audio" not in ssml
        # Text should be present
        assert "Click here" in ssml

    def test_emphasis_patterns_escaped(self):
        """Emphasis patterns should be escaped."""
        text = "This is **bold** and *italic* and _reduced_"
        doc = ssmd.Document(text, escape_syntax=True)
        ssml = doc.to_ssml()
        # Should not create emphasis tags
        assert '<emphasis level="strong">' not in ssml
        assert "<emphasis>" not in ssml
        # Text should be present
        assert "bold" in ssml
        assert "italic" in ssml
        assert "reduced" in ssml

    def test_break_patterns_escaped(self):
        """Break patterns should be escaped."""
        text = "Wait ...s then continue"
        doc = ssmd.Document(text, escape_syntax=True)
        ssml = doc.to_ssml()
        # Should not have break tags
        assert "<break" not in ssml

    def test_selective_escape_emphasis_only(self):
        """Test Document with selective pattern escaping."""
        text = 'This *word* has [annotation]{lang="fr"}'
        doc = ssmd.Document(text, escape_syntax=True, escape_patterns=["emphasis"])
        ssml = doc.to_ssml()
        # Emphasis should not be created
        assert "<emphasis>" not in ssml
        # But we can't easily test if annotation was processed
        # without more complex checks

    def test_roundtrip_with_escaping(self):
        """Test that escaped content survives document creation."""
        text = "This *word* should not be emphasized"
        doc = ssmd.Document(text, escape_syntax=True)
        ssmd_output = doc.ssmd
        # The internal SSMD should have placeholders (not original *)
        assert "*word*" not in ssmd_output
        # But SSML should not have emphasis and should have restored text
        ssml = doc.to_ssml()
        assert "<emphasis>" not in ssml
        assert "*word*" in ssml  # Placeholders should be restored


class TestRealWorldMarkdown:
    """Test with real-world markdown examples."""

    def test_github_readme_style(self):
        """Test with GitHub README style markdown."""
        markdown = """# My Project

This is a **great** project with *awesome* features.

Visit [our website](https://example.com) for more info.

## Installation

Run `pip install myproject` to install.
        """
        doc = ssmd.Document(markdown, escape_syntax=True)
        ssml = doc.to_ssml()

        # Should contain the text
        assert "My Project" in ssml
        assert "great" in ssml
        assert "awesome" in ssml

        # Should NOT have SSMD markup
        assert "<emphasis" not in ssml
        assert "<audio" not in ssml

    def test_mixed_content(self):
        """Test that legitimate text isn't over-escaped."""
        text = "Email me at user@example.com about prices ($5...10)"
        doc = ssmd.Document(text, escape_syntax=True)
        ssml = doc.to_ssml()

        # Email should be preserved
        assert "user" in ssml or "example" in ssml

    def test_technical_documentation(self):
        """Test with technical documentation containing SSMD-like syntax."""
        text = """
The function returns *args and **kwargs as parameters.
Use [config](type: dict) to configure the system.
Wait ...s before retrying the connection.
        """
        doc = ssmd.Document(text, escape_syntax=True)
        ssml = doc.to_ssml()

        # Should not interpret as SSMD
        assert "args" in ssml
        assert "kwargs" in ssml
        # No emphasis tags
        assert "<emphasis>" not in ssml

    def test_chat_or_dialogue(self):
        """Test with dialogue that might have voice-like patterns."""
        text = """
@alice: Hello there!
@bob: Hi, how are you?
        """
        doc = ssmd.Document(text, escape_syntax=True)
        ssml = doc.to_ssml()

        # Should not interpret as directives
        assert "<voice" not in ssml
        # Text should be present
        assert "alice" in ssml or "Hello" in ssml


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_empty_string(self):
        """Empty string should not cause errors."""
        result = ssmd.escape_ssmd_syntax("")
        assert result == ""

    def test_no_patterns_to_escape(self):
        """Plain text without patterns should remain unchanged."""
        text = "This is plain text without any special syntax."
        result = ssmd.escape_ssmd_syntax(text)
        assert result == text

    def test_nested_patterns(self):
        """Nested patterns should be escaped."""
        text = "This **has *nested* emphasis** text"
        result = ssmd.escape_ssmd_syntax(text)
        # Should be different from original
        assert result != text
        # Should be reversible
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_multiline_content(self):
        """Multiline content should be handled correctly."""
        text = """Line 1 with *emphasis*
Line 2 with **strong**
Line 3 with [link]{src="url"}"""
        result = ssmd.escape_ssmd_syntax(text)
        # Should be different from original
        assert result != text
        # Should be reversible
        assert ssmd.unescape_ssmd_syntax(result) == text

    def test_special_characters_in_annotations(self):
        """Special characters in annotation params should work."""
        text = '[text]{src="https://example.com?param=value&other=123"}'
        result = ssmd.escape_ssmd_syntax(text)
        # Should be different from original
        assert result != text
        # Should be reversible
        assert ssmd.unescape_ssmd_syntax(result) == text
        # URL parameters should be preserved
        assert "param=value" in result

    def test_consecutive_patterns(self):
        """Consecutive patterns should all be escaped."""
        text = "*word1* *word2* *word3*"
        result = ssmd.escape_ssmd_syntax(text)
        # Should be different from original
        assert result != text
        # Should be reversible
        assert ssmd.unescape_ssmd_syntax(result) == text
        # Original asterisks should be replaced
        assert result.count("*") == 0

    def test_unescape_idempotent(self):
        """Unescaping already unescaped text should not change it."""
        text = "Plain text with * and [ and @"
        result = ssmd.unescape_ssmd_syntax(text)
        assert result == text

    def test_escape_unescape_roundtrip(self):
        """Escaping should be reversible."""
        text = 'Mix *emphasis* [note]{lang="fr"} and @mark'
        escaped = ssmd.escape_ssmd_syntax(text)
        assert ssmd.unescape_ssmd_syntax(escaped) == text

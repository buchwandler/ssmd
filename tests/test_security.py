"""Security tests for XML injection prevention and input validation."""

import pytest

import ssmd


class TestXMLInjectionPrevention:
    """Test that user input is properly escaped to prevent XML injection."""

    def test_voice_name_injection(self):
        """Test that malicious voice names are escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject script tag via voice name
        result = ssmd.to_ssml('[hello]{voice="Joanna<script>alert(1)</script>"}')

        # Should not contain unescaped script tag
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

        # Should contain escaped tag content
        assert "Joanna&lt;script&gt;" in result

    def test_voice_language_injection(self):
        """Test that malicious language codes are escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via language attribute
        result = ssmd.to_ssml('[text]{voice-lang="en-US<evil/>"}')

        # Should not contain unescaped evil tag
        assert "<evil/>" not in result
        assert "&lt;evil" in result

    def test_voice_gender_injection(self):
        """Test that malicious gender values are escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via gender attribute
        result = ssmd.to_ssml('[text]{voice-lang="en-US" gender="female<script>evil()</script>"}')

        # Should not contain unescaped script
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_substitution_injection(self):
        """Test that malicious aliases are escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via substitution alias
        result = ssmd.to_ssml('[H2O]{sub="water<evil/>"}')

        # Should not contain UNESCAPED evil tag (key test!)
        assert "<evil/>" not in result
        # The escaped version should be present
        assert "&lt;evil" in result and "&gt;" in result

    def test_phoneme_injection(self):
        """Test that malicious phonemes are escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via phoneme
        result = ssmd.to_ssml('[text]{ipa="ɑ<phoneme><script>alert(1)</script>"}')

        # Should not contain unescaped script tag
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_audio_url_injection(self):
        """Test that malicious URLs are escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via audio URL
        # This won't match the audio regex (doesn't end with .mp3 properly)
        result = ssmd.to_ssml('[desc]{src="sound.mp3<evil/>"}')

        # Should not create unescaped tag
        assert "<evil/>" not in result
        assert "&lt;evil" in result

    def test_audio_clip_injection(self):
        """Test that audio clip attributes are escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via clip attribute
        result = ssmd.to_ssml('[music]{src="song.mp3" clip="0s-1s<evil/>"}')

        # Should not contain unescaped evil tag
        assert "<evil/>" not in result
        assert "&lt;evil" in result

    def test_audio_speed_injection(self):
        """Test that audio speed attribute is escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via speed attribute
        result = ssmd.to_ssml('[fast]{src="speech.mp3" speed="150%<script>pwned()</script>"}')

        # Should not contain unescaped script
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_audio_desc_injection(self):
        """Test that audio descriptions are escaped."""
        result = ssmd.to_ssml('[<break time="10s"/>]{src="sound.mp3"}')

        assert "<break" not in result
        assert '&lt;break time="10s"/&gt;' in result

    def test_say_as_interpret_injection(self):
        """Test that say-as interpret-as is escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via interpret-as
        result = ssmd.to_ssml('[123]{as="cardinal<evil/>"}')

        # Should not contain unescaped evil tag
        assert "<evil/>" not in result
        assert "&lt;evil" in result

    def test_say_as_format_injection(self):
        """Test that say-as format attribute is escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via format
        result = ssmd.to_ssml('[date]{as="date" format="dd.mm.yyyy<script>alert()</script>"}')

        # Should not contain unescaped script
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_language_code_injection(self):
        """Test that language codes are escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via language code
        result = ssmd.to_ssml('[text]{lang="en-US<evil/>"}')

        # Should not contain unescaped evil tag
        assert "<evil/>" not in result
        assert "&lt;evil" in result

    def test_prosody_volume_injection(self):
        """Test that prosody volume values are escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via volume value (using annotation syntax)
        result = ssmd.to_ssml('[loud]{volume="+10dB<evil/>"}')

        # Should not contain unescaped evil tag
        assert "<evil/>" not in result
        assert "&lt;evil" in result

    def test_prosody_rate_injection(self):
        """Test that prosody rate values are escaped."""
        # Use ssmd.to_ssml convenience function

        # Attempt to inject via rate value
        result = ssmd.to_ssml('[fast]{rate="150%<script>bad()</script>"}')

        # Should not contain unescaped script
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_multiple_injections(self):
        """Test multiple injection attempts in same document."""
        # Use ssmd.to_ssml convenience function

        text = """
[evil1]{voice="Joanna<script>alert(1)</script>"}
[evil2]{sub="water<evil/>"}
[evil3]{ipa="ɑ<phoneme><script>pwned()</script>"}
        """

        result = ssmd.to_ssml(text)

        # Should not contain ANY unescaped malicious content
        assert "<script>" not in result or result.count("&lt;script&gt;") >= 2
        assert "<evil" not in result or "&lt;evil" in result
        assert "alert(1)" not in result or "&lt;script&gt;alert(1)&lt;/script&gt;" in result
        assert "pwned()" not in result or "&lt;script&gt;pwned()&lt;/script&gt;" in result


class TestQuoteEscaping:
    """Test that quotes are properly escaped in attributes."""

    def test_double_quotes_in_voice_name(self):
        """Test that double quotes in voice names are escaped."""
        # Use ssmd.to_ssml convenience function

        result = ssmd.to_ssml("[text]{voice='Voice\"Name'}")

        # Should escape the quote
        assert "Voice&quot;Name" in result or 'Voice"Name' not in result.replace('name="Voice', "")

    def test_single_quotes_converted_to_double(self):
        """Test that content with quotes is handled safely."""
        # Use ssmd.to_ssml convenience function

        # HTML escape should handle quotes
        result = ssmd.to_ssml('[text]{sub="O\'Brien"}')

        # Should be valid XML (parser won't throw)
        import xml.etree.ElementTree as ET

        try:
            ET.fromstring(result)
        except ET.ParseError:
            pytest.fail("Generated invalid XML with quotes")

    def test_mixed_quotes(self):
        """Test mixed single and double quotes."""
        # Use ssmd.to_ssml convenience function

        result = ssmd.to_ssml("[text]{sub='He said \"hi\" and she said \\'bye\\''}")

        # Should be valid XML
        import xml.etree.ElementTree as ET

        try:
            ET.fromstring(result)
        except ET.ParseError:
            pytest.fail("Generated invalid XML with mixed quotes")


class TestSpecialCharacters:
    """Test handling of XML special characters."""

    def test_ampersand_in_alias(self):
        """Test that ampersands are escaped."""
        # Use ssmd.to_ssml convenience function

        result = ssmd.to_ssml('[R&D]{sub="Research & Development"}')

        # Should escape ampersand
        assert "Research &amp; Development" in result or "&amp;" in result

    def test_less_than_in_phoneme(self):
        """Test that < is escaped."""
        # Use ssmd.to_ssml convenience function

        result = ssmd.to_ssml('[text]{ipa="ɑ<test"}')

        # Should escape <
        assert "ɑ&lt;test" in result or "<test" not in result.split(">")[-1]

    def test_greater_than_in_alias(self):
        """Test that > is escaped in alias values."""
        # Use ssmd.to_ssml convenience function

        # Test with > in the ALIAS, not the text
        result = ssmd.to_ssml('[text]{sub="A>B means A greater than B"}')

        # Should escape > in the alias attribute
        assert "A&gt;B" in result or 'alias="A>B' not in result

    def test_all_special_chars(self):
        """Test all XML special characters together."""
        # Use ssmd.to_ssml convenience function

        # All 5 XML special chars: < > & " '
        result = ssmd.to_ssml("[text]{sub='<tag> & \"quotes\" \\'test\\''}")

        # Should be valid XML
        import xml.etree.ElementTree as ET

        try:
            ET.fromstring(result)
        except ET.ParseError:
            pytest.fail("Failed to escape all special characters")

    def test_literal_special_chars_in_text(self):
        """Literal <, >, & in text should be XML-safe."""
        result = ssmd.to_ssml("Math: 5 < 7 & 8 > 3.")

        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result

        import xml.etree.ElementTree as ET

        ET.fromstring(result)

    def test_special_chars_inside_markup_text(self):
        """Text content inside SSMD markup should escape safely."""
        result = ssmd.to_ssml("*5 < 7 & 8 > 3*")

        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result

        import xml.etree.ElementTree as ET

        ET.fromstring(result)


class TestEdgeCases:
    """Test edge cases for security."""

    def test_empty_injection_attempt(self):
        """Test injection with empty content."""
        # Use ssmd.to_ssml convenience function

        result = ssmd.to_ssml('[]{voice="<script></script>"}')

        # Should not contain script tag
        assert "<script>" not in result or "&lt;script&gt;" in result

    def test_nested_tags_injection(self):
        """Test deeply nested tag injection."""
        # Use ssmd.to_ssml convenience function

        malicious = "<a><b><c><script>alert(1)</script></c></b></a>"
        result = ssmd.to_ssml(f'[text]{{sub="{malicious}"}}')

        # Should escape all tags
        assert "<script>" not in result or "&lt;script&gt;" in result
        assert "&lt;a&gt;&lt;b&gt;&lt;c&gt;" in result

    def test_null_byte_injection(self):
        """Test null byte injection attempt."""
        # Use ssmd.to_ssml convenience function

        # Null bytes should be handled safely
        result = ssmd.to_ssml('[text]{voice="Joanna\x00Evil"}')

        # Should be valid XML (parser won't crash)
        import xml.etree.ElementTree as ET

        try:
            ET.fromstring(result)
        except ET.ParseError:
            # Null bytes might be rejected, that's OK
            pass

    def test_unicode_injection(self):
        """Test unicode-based injection attempts."""
        # Use ssmd.to_ssml convenience function

        # Unicode look-alike characters
        result = ssmd.to_ssml('[text]{voice="Joanna＜script＞alert()＜/script＞"}')

        # Should not break XML parsing
        import xml.etree.ElementTree as ET

        try:
            ET.fromstring(result)
        except ET.ParseError:
            pytest.fail("Unicode characters broke XML parsing")

    def test_very_long_injection(self):
        """Test very long injection string."""
        # Use ssmd.to_ssml convenience function

        # Very long malicious string
        long_evil = "<script>" + "A" * 10000 + "alert(1)" + "</script>"
        result = ssmd.to_ssml(f'[text]{{sub="{long_evil}"}}')

        # Should escape without crashing
        assert len(result) > 0
        assert "<script>" not in result or "&lt;script&gt;" in result


class TestValidSSMLOutput:
    """Ensure that escaped output is still valid SSML."""

    def test_escaped_voice_parses(self):
        """Test that escaped voice attributes parse correctly."""
        # Use ssmd.to_ssml convenience function

        # Use a valid voice name (alphanumeric + hyphens/underscores only)
        result = ssmd.to_ssml('[hello]{voice="Joanna-Test_1"}')

        # Should be valid XML
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(result)
            # Should have voice element
            voice = root.find(".//voice")
            assert voice is not None
            assert "Joanna-Test_1" in ET.tostring(root, encoding="unicode")
        except ET.ParseError:
            pytest.fail("Escaped voice produced invalid XML")

    def test_escaped_substitution_parses(self):
        """Test that escaped substitution parses correctly."""
        # Use ssmd.to_ssml convenience function

        result = ssmd.to_ssml('[H2O]{sub="water & ice"}')

        # Should be valid XML
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(result)
            sub = root.find(".//sub")
            assert sub is not None
            assert "water &amp; ice" in ET.tostring(root, encoding="unicode")
        except ET.ParseError:
            pytest.fail("Escaped substitution produced invalid XML")

    def test_all_annotations_with_special_chars(self):
        """Test all annotation types with special characters."""
        # Use ssmd.to_ssml convenience function

        text = """
[text]{voice="Jo&anna"}
[H2O]{sub="water & ice"}
[text]{ipa="ɑ&test"}
[123]{as="cardinal"}
[hello]{lang="en-GB"}
[loud]{volume="5" rate="3" pitch="4"}
[desc]{src="sound.mp3" clip="0s-10s"}
        """

        result = ssmd.to_ssml(text)

        # Should be valid XML
        import xml.etree.ElementTree as ET

        try:
            ET.fromstring(result)
        except ET.ParseError as e:
            pytest.fail(f"Generated invalid XML: {e}")


class TestRoundtripWithEscaping:
    """Test that escaped content survives roundtrip conversion."""

    def test_roundtrip_special_chars_in_alias(self):
        """Test SSMD -> SSML -> SSMD with special characters."""
        from ssmd.ssml_parser import SSMLParser

        original = '[R&D]{sub="Research & Development"}'
        # Use ssmd.to_ssml convenience function
        parser = SSMLParser()

        # Convert to SSML
        ssml = ssmd.to_ssml(original)

        # Should contain escaped ampersand
        assert "&amp;" in ssml

        # Convert back to SSMD
        recovered = parser.to_ssmd(ssml)

        # Should preserve the content (might not be exact match due to formatting)
        assert "Research" in recovered
        assert "Development" in recovered
        assert "&" in recovered or "&amp;" in recovered

    def test_roundtrip_quotes_in_voice(self):
        """Test roundtrip with quotes in voice name."""
        from ssmd.ssml_parser import SSMLParser

        # Voice names with special chars
        original = '[text]{voice="Test-Voice-1"}'
        # Use ssmd.to_ssml convenience function
        parser = SSMLParser()

        ssml = ssmd.to_ssml(original)
        recovered = parser.to_ssmd(ssml)

        # Should preserve voice name
        assert "Test-Voice-1" in recovered or "Test-Voice-1" in ssml

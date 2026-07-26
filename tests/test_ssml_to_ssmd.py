"""Tests for SSML to SSMD conversion."""

import xml.etree.ElementTree as ET

import pytest

import ssmd
from ssmd import SSMLParser


class TestSSMLToSSMD:
    """Test SSML to SSMD reverse conversion."""

    def test_simple_text(self):
        """Test plain text without markup."""
        ssml = "<speak>Hello world</speak>"
        result = ssmd.from_ssml(ssml)
        assert result.strip() == "Hello world"

    def test_emphasis(self):
        """Test emphasis conversion."""
        ssml = "<speak><emphasis>Hello</emphasis> world</speak>"
        result = ssmd.from_ssml(ssml)
        assert result.strip() == "*Hello* world"

    def test_emphasis_with_capabilities(self):
        """Capabilities strip unsupported emphasis on reverse conversion."""
        ssml = "<speak><emphasis>Hello</emphasis></speak>"
        result = ssmd.from_ssml(ssml, capabilities="espeak")
        assert result.strip() == "Hello"

    def test_emphasis_strong(self):
        """Test strong emphasis conversion."""
        ssml = '<speak><emphasis level="strong">Hello</emphasis></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == "**Hello**"

    def test_break_default(self):
        """Test default break conversion."""
        ssml = '<speak>Hello<break time="1000ms"/>world</speak>'
        result = ssmd.from_ssml(ssml)
        # Breaks have space before and after per SSMD spec
        assert result.strip() == "Hello ...1000ms world"

    def test_break_custom_time(self):
        """Test break with custom time."""
        ssml = '<speak>Hello<break time="500ms"/>world</speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == "Hello ...500ms world"

    def test_break_seconds(self):
        """Test break with seconds."""
        ssml = '<speak>Hello<break time="2s"/>world</speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == "Hello ...2s world"

    def test_break_strength(self):
        """Test break with strength."""
        ssml = '<speak>Hello<break strength="strong"/>world</speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == "Hello ...s world"

    def test_paragraph(self):
        """Test paragraph conversion."""
        ssml = "<speak><p>First paragraph</p><p>Second paragraph</p></speak>"
        result = ssmd.from_ssml(ssml)
        assert "First paragraph" in result
        assert "Second paragraph" in result
        # Paragraphs should be separated by double newlines
        assert "\n\n" in result

    def test_roundtrip_paragraphs(self):
        """Paragraph breaks are preserved in roundtrip."""
        original = "First paragraph.\n\nSecond paragraph."
        ssml_out = ssmd.to_ssml(original)
        assert "<p>" in ssml_out
        ssmd_back = ssmd.from_ssml(ssml_out)
        assert "\n\n" in ssmd_back.strip()
        assert ssmd_back.strip() == original

    def test_language(self):
        """Test language tag conversion."""
        ssml = '<speak><lang xml:lang="en-US">Hello</lang></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Hello]{lang="en"}'

    def test_language_non_standard(self):
        """Test non-standard language locale."""
        ssml = '<speak><lang xml:lang="en-GB">Hello</lang></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Hello]{lang="en-GB"}'

    def test_phoneme_ipa(self):
        """Test phoneme with IPA."""
        ssml = '<speak><phoneme alphabet="ipa" ph="təmeɪtoʊ">tomato</phoneme></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[tomato]{ph="təmeɪtoʊ" alphabet="ipa"}'

    def test_phoneme_xsampa(self):
        """Test phoneme with X-SAMPA."""
        ssml = '<speak><phoneme alphabet="x-sampa" ph="t@meItoU">tomato</phoneme></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[tomato]{ph="t@meItoU" alphabet="x-sampa"}'

    def test_substitution(self):
        """Test substitution conversion."""
        ssml = '<speak><sub alias="World Wide Web Consortium">W3C</sub></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[W3C]{sub="World Wide Web Consortium"}'

    def test_say_as(self):
        """Test say-as conversion."""
        ssml = '<speak><say-as interpret-as="telephone">+1-555-1234</say-as></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[+1-555-1234]{as="telephone"}'

    def test_say_as_with_format(self):
        """Test say-as with format attribute."""
        ssml = '<speak><say-as interpret-as="date" format="mdy">12/31/2024</say-as></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[12/31/2024]{as="date" format="mdy"}'

    def test_say_as_detail_with_quotes_and_braces(self):
        """Say-as detail values should be quoted safely."""
        ssml = '<speak><say-as interpret-as="characters" detail=\'a"b{c}\'>abc</say-as></speak>'
        result = ssmd.from_ssml(ssml)
        assert "detail='a\"b\\{c\\}'" in result

        roundtrip = ssmd.to_ssml(result)
        ET.fromstring(roundtrip)
        assert 'detail="a&quot;b{c}"' in roundtrip

    def test_audio(self):
        """Test audio tag conversion."""
        ssml = '<speak><audio src="sound.mp3">Alternative text</audio></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Alternative text]{src="sound.mp3"}'

    def test_audio_no_alt(self):
        """Test audio tag without alt text."""
        ssml = '<speak><audio src="sound.mp3"/></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[]{src="sound.mp3"}'

    def test_mark(self):
        """Test mark conversion."""
        ssml = '<speak>Hello<mark name="point1"/>world</speak>'
        result = ssmd.from_ssml(ssml)
        # Marks have space before
        assert result.strip() == "Hello @point1 world"

    def test_prosody_volume(self):
        """Test prosody volume conversion."""
        ssml = '<speak><prosody volume="loud">Hello</prosody></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Hello]{volume="loud"}'

    def test_prosody_volume_xloud(self):
        """Test prosody x-loud volume."""
        ssml = '<speak><prosody volume="x-loud">Hello</prosody></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Hello]{volume="x-loud"}'

    def test_prosody_volume_soft(self):
        """Test prosody soft volume."""
        ssml = '<speak><prosody volume="soft">Hello</prosody></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Hello]{volume="soft"}'

    def test_prosody_rate(self):
        """Test prosody rate conversion."""
        ssml = '<speak><prosody rate="fast">Hello</prosody></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Hello]{rate="fast"}'

    def test_prosody_pitch(self):
        """Test prosody pitch conversion."""
        ssml = '<speak><prosody pitch="high">Hello</prosody></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Hello]{pitch="high"}'

    def test_prosody_multiple_attributes(self):
        """Test prosody with multiple attributes."""
        ssml = '<speak><prosody volume="loud" rate="fast">Hello</prosody></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Hello]{volume="loud" rate="fast"}'

    def test_amazon_whisper_effect(self):
        """Test Amazon whisper effect."""
        # Amazon effects require namespace declaration
        ssml = (
            '<speak xmlns:amazon="https://amazon.com/ssml">'
            '<amazon:effect name="whispered">secret</amazon:effect></speak>'
        )
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[secret]{ext="whisper"}'

    def test_non_amazon_effect_passthrough(self):
        """Non-Amazon effect tags should be ignored."""
        ssml = (
            '<speak xmlns:custom="https://example.com/custom">'
            '<custom:effect name="boom">Hello</custom:effect>'
            "</speak>"
        )
        result = ssmd.from_ssml(ssml)
        assert result.strip() == "Hello"

    def test_complex_nested(self):
        """Test complex nested markup."""
        ssml = """<speak>
            <p><emphasis>Hello</emphasis> world</p>
            <p>This is <prosody volume="loud">important</prosody></p>
        </speak>"""
        result = ssmd.from_ssml(ssml)
        assert "*Hello* world" in result
        assert '[important]{volume="loud"}' in result

    def test_roundtrip_simple(self):
        """Test roundtrip conversion for simple text."""
        original = "*Hello* world"
        ssml_out = ssmd.to_ssml(original)
        ssmd_back = ssmd.from_ssml(ssml_out)
        assert ssmd_back.strip() == original

    def test_roundtrip_emphasis(self):
        """Test roundtrip with emphasis."""
        original = "This is *emphasized* text"
        ssml_out = ssmd.to_ssml(original)
        ssmd_back = ssmd.from_ssml(ssml_out)
        assert ssmd_back.strip() == original

    def test_roundtrip_break(self):
        """Test roundtrip with break."""
        original = "Hello ...1s world"
        ssml_out = ssmd.to_ssml(original)
        ssmd_back = ssmd.from_ssml(ssml_out)
        assert ssmd_back.strip() == original

    def test_roundtrip_language(self):
        """Test roundtrip with language."""
        original = '[Bonjour]{lang="fr"} world'
        ssml_out = ssmd.to_ssml(original)
        ssmd_back = ssmd.from_ssml(ssml_out)
        assert ssmd_back.strip() == original

    def test_roundtrip_prosody_volume(self):
        """Test roundtrip with prosody volume."""
        original = '[loud]{volume="loud"}'
        ssml_out = ssmd.to_ssml(original)
        ssmd_back = ssmd.from_ssml(ssml_out)
        assert ssmd_back.strip() == original

    def test_invalid_ssml(self):
        """Test handling of invalid SSML."""
        with pytest.raises(ValueError, match="Invalid SSML XML"):
            ssmd.from_ssml("<speak><unclosed>")

    def test_parser_class(self):
        """Test using SSMLParser class directly."""
        parser = SSMLParser()
        ssml = "<speak><emphasis>Hello</emphasis></speak>"
        result = parser.to_ssmd(ssml)
        assert result.strip() == "*Hello*"

    def test_without_speak_wrapper(self):
        """Test SSML without <speak> wrapper."""
        ssml = "<emphasis>Hello</emphasis> world"
        result = ssmd.from_ssml(ssml)
        assert result.strip() == "*Hello* world"

    def test_sentence_tags(self):
        """Test sentence tags are stripped."""
        ssml = "<speak><s>Hello world</s></speak>"
        result = ssmd.from_ssml(ssml)
        assert result.strip() == "Hello world"

    def test_whitespace_normalization(self):
        """Test whitespace is normalized."""
        ssml = """<speak>
            Hello    world

            Test
        </speak>"""
        result = ssmd.from_ssml(ssml)
        # Multiple spaces should be collapsed
        assert "  " not in result
        # Content should be preserved
        assert "Hello world" in result
        assert "Test" in result

    def test_voice_name(self):
        """Test voice with name conversion."""
        ssml = '<speak><voice name="Joanna">Hello</voice></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Hello]{voice="Joanna"}'

    def test_voice_attribute_with_quotes(self):
        """Quoted SSML attributes should round-trip safely."""
        ssml = '<speak><voice name="He said &quot;hi&quot; and it\'s fine">Hello</voice></speak>'
        result = ssmd.from_ssml(ssml)
        assert "voice=" in result

        roundtrip = ssmd.to_ssml(result)
        assert "He said &quot;hi&quot;" in roundtrip

    def test_voice_attribute_ampersand_roundtrip(self):
        """Ampersands in attributes should stay unescaped in SSMD."""
        ssml = '<speak><voice name="R&amp;D">Hello</voice></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Hello]{voice="R&D"}'

        roundtrip = ssmd.to_ssml(result)
        ET.fromstring(roundtrip)
        assert "R&amp;D" in roundtrip

    def test_voice_language_gender(self):
        """Test voice with language and gender."""
        ssml = '<speak><voice language="fr-FR" gender="female">Bonjour</voice></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Bonjour]{voice-lang="fr-FR" gender="female"}'

    def test_voice_all_attributes(self):
        """Test voice with all attributes."""
        ssml = '<speak><voice language="en-GB" gender="male" variant="1">Text</voice></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.strip() == '[Text]{voice-lang="en-GB" gender="male" variant="1"}'

    def test_roundtrip_voice_name(self):
        """Test roundtrip voice with name."""
        original = '[Hello]{voice="Joanna"}'
        ssml_out = ssmd.to_ssml(original)
        ssmd_back = ssmd.from_ssml(ssml_out)
        assert ssmd_back.strip() == original

    def test_roundtrip_voice_complex(self):
        """Test roundtrip voice with language and gender."""
        original = '[Bonjour]{voice-lang="fr-FR" gender="female"}'
        ssml_out = ssmd.to_ssml(original)
        ssmd_back = ssmd.from_ssml(ssml_out)
        assert ssmd_back.strip() == original

    def test_voice_directive_to_ssmd(self):
        """Test converting multiline voice SSML to directive syntax."""
        ssml = (
            '<speak><p><voice name="sarah">This is a long sentence that '
            "should convert to directive syntax because it is longer than "
            "eighty characters.</voice></p></speak>"
        )
        result = ssmd.from_ssml(ssml)
        assert result.startswith('<div voice="sarah">')
        assert "This is a long sentence" in result

    def test_voice_paragraphs_to_directive(self):
        """Voice blocks with paragraphs use directive syntax."""
        ssml = '<speak><voice name="sarah"><p>Hello there.</p><p>How are you?</p></voice></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.startswith('<div voice="sarah">')
        assert "Hello there." in result
        assert "How are you?" in result
        assert "\n\n" in result

    def test_language_paragraphs_to_directive(self):
        """Language blocks with paragraphs use directive syntax."""
        ssml = '<speak><lang xml:lang="en-US"><p>Hello there.</p><p>How are you?</p></lang></speak>'
        result = ssmd.from_ssml(ssml)
        assert result.startswith('<div lang="en">')
        assert "Hello there." in result
        assert "How are you?" in result
        assert "\n\n" in result

    def test_voice_directive_roundtrip(self):
        """Test roundtrip with directive syntax."""
        original = """<div voice="sarah">
Hello from Sarah with a very long message that definitely spans way more
than eighty characters to trigger directive format
</div>

<div voice="michael">
And hello from Michael with another long message to ensure it uses
directive format too
</div>"""
        ssml_out = ssmd.to_ssml(original)
        assert '<voice name="sarah">' in ssml_out
        assert '<voice name="michael">' in ssml_out
        # Convert back - should use directive syntax for long content
        ssmd_back = ssmd.from_ssml(ssml_out)
        assert '<div voice="sarah">' in ssmd_back
        assert '<div voice="michael">' in ssmd_back

    def test_voice_directive_with_attrs_to_ssmd(self):
        """Test converting voice with attributes to directive syntax."""
        ssml = (
            '<speak><p><voice language="fr-FR" gender="female">'
            "Bonjour! Comment allez-vous aujourd'hui? "
            "J'espère que vous passez une excellente journée!"
            "</voice></p></speak>"
        )
        result = ssmd.from_ssml(ssml)
        # Should use directive syntax because content is long
        assert '<div voice-lang="fr-FR" gender="female">' in result
        assert "Bonjour!" in result

    def test_voice_directive_attrs_roundtrip(self):
        """Test roundtrip with directive using attributes."""
        original = """<div voice-lang="fr-FR" gender="female">
Bonjour! C'est un très grand plaisir de vous parler aujourd'hui dans
cette magnifique langue française!
</div>

<div voice-lang="en-GB" gender="male" variant="1">
Hello there! It's absolutely lovely to meet you on this fine day in
the beautiful United Kingdom.
</div>"""
        ssml_out = ssmd.to_ssml(original)
        assert '<voice language="fr-FR" gender="female">' in ssml_out
        assert '<voice language="en-GB" gender="male" variant="1">' in ssml_out
        # Convert back - should preserve directive format with attributes
        ssmd_back = ssmd.from_ssml(ssml_out)
        assert '<div voice-lang="fr-FR" gender="female">' in ssmd_back
        assert '<div voice-lang="en-GB" gender="male" variant="1">' in ssmd_back


class TestSSMLToSSMDHardening:
    """Regression tests for SSML->SSMD parser hardening.

    These cover the literal-text / bracket / decimal / namespace / vendor cases
    that previously corrupted generated SSMD.
    """

    def test_literal_emphasis_chars_preserved(self):
        """Literal asterisks in SSML text are not reparsed as SSMD emphasis."""
        result = ssmd.from_ssml("<speak>2 * 3 = 6</speak>").strip()
        assert result == "2 * 3 = 6"

    def test_literal_annotation_syntax_preserved(self):
        """Literal [x]{y=\"z\"} in SSML text survives verbatim."""
        result = ssmd.from_ssml('<speak>see [x]{y="z"} here</speak>').strip()
        assert result == 'see [x]{y="z"} here'

    def test_literal_mark_preserved(self):
        """Literal @word in SSML text is not reparsed as an SSMD mark."""
        result = ssmd.from_ssml("<speak>call @word now</speak>").strip()
        assert result == "call @word now"

    def test_xml_declaration_handled(self):
        """An XML declaration before <speak> no longer breaks parsing."""
        ssml = '<?xml version="1.0" encoding="UTF-8"?><speak>hi there</speak>'
        result = ssmd.from_ssml(ssml).strip()
        assert result == "hi there"

    def test_namespaced_desc_resolved(self):
        """A namespaced <desc> is matched namespace-agnostically."""
        ns = "http://www.w3.org/2001/10/synthesis"
        ssml = f'<speak xmlns="{ns}"><audio src="a.mp3"><desc>Sound clip</desc></audio></speak>'
        result = ssmd.from_ssml(ssml).strip()
        assert result == '[Sound clip]{src="a.mp3"}'

    def test_bracket_in_annotation_content_degrades_cleanly(self):
        """A literal ']' inside annotation content does not corrupt surrounding text."""
        result = ssmd.from_ssml(
            '<speak><say-as interpret-as="characters">a]b</say-as> after</speak>'
        ).strip()
        assert "a]b" in result
        assert "after" in result
        assert "</div>" not in result

    def test_decimal_break_duration_preserved(self):
        """Decimal break durations like 1.5s are preserved and round-trip."""
        result = ssmd.from_ssml('<speak>a<break time="1.5s"/>b</speak>').strip()
        assert result == "a ...1.5s b"
        # And it round-trips back to a real break.
        assert '<break time="1.5s"' in ssmd.to_ssml("a ...1.5s b")

    def test_nested_emphasis(self):
        """Nested emphasis levels are preserved."""
        ssml = '<speak><emphasis level="strong"><emphasis>deep</emphasis> nest</emphasis></speak>'
        result = ssmd.from_ssml(ssml).strip()
        assert "*deep*" in result
        assert "nest" in result

    def test_unknown_vendor_tag_flattened(self):
        """Unknown vendor tags are flattened to their children."""
        ssml = (
            '<speak>before <mstts:express-as style="cheerful" '
            'xmlns:mstts="https://example.com/mstts">happy</mstts:express-as>'
            " after</speak>"
        )
        result = ssmd.from_ssml(ssml).strip()
        assert "before" in result
        assert "happy" in result
        assert "after" in result

    def test_audio_single_sided_clip_begin(self):
        """A clipBegin-only audio clip is preserved (not dropped)."""
        ssml = '<speak><audio src="a.mp3" clipBegin="2s">Clip</audio></speak>'
        result = ssmd.from_ssml(ssml).strip()
        assert 'clip="2s-"' in result

    def test_audio_single_sided_clip_end(self):
        """A clipEnd-only audio clip is preserved (not dropped)."""
        ssml = '<speak><audio src="a.mp3" clipEnd="3s">Clip</audio></speak>'
        result = ssmd.from_ssml(ssml).strip()
        assert 'clip="-3s"' in result

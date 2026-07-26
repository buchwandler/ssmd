"""Test TTS capability filtering."""

import pytest

import ssmd
from ssmd import Document, TTSCapabilities, get_preset


def test_capability_emphasis_disabled():
    """Test that emphasis is stripped when not supported."""
    caps = TTSCapabilities(emphasis=False)
    doc = Document("Hello *world*!", capabilities=caps)

    result = doc.to_ssml()
    # Should strip emphasis markup
    assert "<emphasis>" not in result
    assert "world" in result


def test_capability_prosody_disabled():
    """Test that prosody is stripped when not supported."""
    caps = TTSCapabilities(prosody=False)
    doc = Document('[loud text]{volume="loud"}', capabilities=caps)

    result = doc.to_ssml()
    # Should strip prosody markup
    assert "<prosody" not in result
    assert "loud text" in result


def test_capability_break_disabled():
    """Test that breaks are stripped when not supported."""
    caps = TTSCapabilities(break_tags=False)
    doc = Document("Hello ...500ms world", capabilities=caps)

    result = doc.to_ssml()
    # Should strip break tags
    assert "<break" not in result
    assert "Hello" in result and "world" in result


def test_capability_language_disabled():
    """Test that language tags are stripped when not supported."""
    caps = TTSCapabilities(language=False)
    doc = Document('[Bonjour]{lang="fr"} world', capabilities=caps)

    result = doc.to_ssml()
    # Should strip language tags
    assert "<lang" not in result
    assert "Bonjour" in result


def test_capability_audio_disabled():
    """Test that audio tags are stripped when not supported."""
    caps = TTSCapabilities(audio=False)
    doc = Document('[sound]{src="https://example.com/beep.mp3"}', capabilities=caps)

    result = doc.to_ssml()
    # Should strip audio tags
    assert "<audio" not in result
    assert "sound" in result


def test_capability_extension_support():
    """Test that extensions respect capability support."""
    doc = Document('[secret]{ext="whisper"} [plain]{ext="custom"}', capabilities="polly")
    result = doc.to_ssml()

    assert "<amazon:effect" in result
    assert "plain" in result
    assert "custom" not in result


def test_capability_extension_minimal():
    """Test extensions are dropped for minimal capabilities."""
    doc = Document('[secret]{ext="whisper"}', capabilities="minimal")
    result = doc.to_ssml()

    assert "<amazon:effect" not in result
    assert "secret" in result


def test_capability_substitution_disabled():
    """Test that substitution tags are stripped when not supported."""
    caps = TTSCapabilities(substitution=False)
    doc = Document('[H2O]{sub="water"}', capabilities=caps)

    result = doc.to_ssml()
    # Should strip sub tags
    assert "<sub" not in result
    assert "H2O" in result


def test_to_text_respects_capabilities():
    """Plain text output should respect strict capabilities."""
    caps = TTSCapabilities(substitution=False)
    doc = Document('[H2O]{sub="water"}', capabilities=caps, strict=True)

    assert doc.to_text() == "H2O"


def test_preset_espeak():
    """Test eSpeak preset (limited capabilities)."""
    doc = Document(capabilities="espeak")

    # eSpeak doesn't support emphasis
    doc = Document("Hello *world*!", capabilities="espeak")
    result = doc.to_ssml()
    assert "<emphasis>" not in result

    # But it supports breaks
    doc = Document("Hello ...500ms world", capabilities="espeak")
    result = doc.to_ssml()
    assert "<break" in result


def test_preset_pyttsx3():
    """Test pyttsx3 preset (minimal SSML)."""
    doc = Document('Hello *world* ...500ms [bonjour]{lang="fr"}!', capabilities="pyttsx3")

    # pyttsx3 has very minimal SSML support
    result = doc.to_ssml()

    # Should strip most features
    assert "<emphasis>" not in result
    assert "<break" not in result
    assert "<lang" not in result

    # Should keep text
    assert "Hello" in result
    assert "world" in result


def test_preset_google():
    """Test Google TTS preset (full support)."""
    doc = Document('Hello *world* ...500ms [bonjour]{lang="fr"}!', capabilities="google")

    # Google supports most features
    result = doc.to_ssml()

    assert "<emphasis>" in result
    assert "<break" in result
    assert "<lang" in result


def test_ssml_green_preset_loading():
    """Test that ssml-green preset data loads from package data."""
    caps = get_preset("google")

    assert isinstance(caps, TTSCapabilities)
    assert caps.ssml_green


def test_preset_lookup_returns_isolated_objects():
    first = get_preset("minimal")
    first.emphasis = True

    second = get_preset("minimal")

    assert second.emphasis is False


def test_profile_lookup_returns_isolated_objects():
    first = ssmd.get_profile("ssmd-core")
    first.inline_tags.clear()
    first.attributes["emphasis"].clear()

    second = ssmd.get_profile("ssmd-core")

    assert "emphasis" in second.inline_tags
    assert second.attributes["emphasis"] == {"level"}


def test_mixed_config_and_capabilities():
    """Test combining custom config with capabilities."""
    caps = TTSCapabilities(emphasis=False)
    doc = Document(
        "Hello *world*!\nHow are you?",
        config={"auto_sentence_tags": True},
        capabilities=caps,
    )

    result = doc.to_ssml()

    # Should have sentence tags (from config)
    assert "<s>" in result or "<p>" in result

    # Should NOT have emphasis (from capabilities)
    assert "<emphasis>" not in result


def test_custom_capabilities():
    """Test custom capability definition."""
    # Create custom TTS with specific limitations
    caps = TTSCapabilities(
        emphasis=True,
        break_tags=True,
        prosody=False,  # No prosody
        language=True,
        audio=False,  # No audio
        say_as=False,  # No say-as
    )

    text = """
    Hello *world*!
    Pause here ...500ms please.
    Say [bonjour]{lang="fr"} to everyone.
    This is [very loud]{volume="x-loud"}.
    The number is [123]{as="cardinal"}.
    """

    doc = Document(text, capabilities=caps)
    result = doc.to_ssml()

    # Supported features
    assert "<emphasis>" in result
    assert "<break" in result
    assert "<lang" in result

    # Unsupported features (should be stripped)
    assert "<prosody" not in result
    assert "<say-as" not in result
    assert "very loud" in result  # Text preserved


def test_prosody_partial_support():
    """Test partial prosody support (only some attributes)."""
    caps = TTSCapabilities(
        prosody=True,
        volume=True,  # Supports volume
        rate=False,  # Doesn't support rate
        pitch=False,  # Doesn't support pitch
    )

    # Volume should work
    doc = Document('[loud]{volume="x-loud"}', capabilities=caps)
    result = doc.to_ssml()
    assert "<prosody" in result or "loud" in result

    # Rate should be stripped (not supported)
    doc = Document('[fast]{rate="fast"}', capabilities=caps)
    result = doc.to_ssml()
    # Should strip rate markup
    assert "fast" in result


def test_extension_filtering():
    """Test that extensions are filtered based on capabilities."""
    caps = TTSCapabilities(extensions={"whisper": True, "drc": False})

    # Whisper is supported
    doc = Document('[quiet]{ext="whisper"}', capabilities=caps)
    result = doc.to_ssml()
    assert "whisper" in result or "quiet" in result

    # DRC is not supported (should strip to text)
    doc = Document('[compressed]{ext="drc"}', capabilities=caps)
    result = doc.to_ssml()
    assert "compressed" in result
    # Should not have DRC-specific tags


def test_minimal_preset():
    """Test minimal preset (everything stripped)."""
    text = """
    # Heading
    Hello *world*!
    Pause ...500ms here.
    [Bonjour]{lang="fr"} everyone.
    [Loud text]{volume="x-loud"}
    """

    doc = Document(text, capabilities="minimal")
    result = doc.to_ssml()

    # Should strip all markup
    assert "<emphasis>" not in result
    assert "<break" not in result
    assert "<lang" not in result
    assert "<prosody" not in result

    # But preserve text
    assert "Heading" in result
    assert "Hello" in result
    assert "world" in result


def test_capability_preserves_text():
    """Test that all capabilities preserve the actual text content."""
    caps = TTSCapabilities(
        emphasis=False,
        prosody=False,
        break_tags=False,
        language=False,
    )

    text = (
        'Hello *world* from [France]{lang="fr"} with [excitement]{volume="x-loud"} ...500ms please!'
    )
    doc = Document(text, capabilities=caps)
    result = doc.to_ssml()

    # All text should be preserved
    assert "Hello" in result
    assert "world" in result
    assert "France" in result
    assert "excitement" in result
    assert "please" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

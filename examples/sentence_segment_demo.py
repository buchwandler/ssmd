"""
SSMD Sentence and Segment API Demo

This demo showcases the new Document-centric architecture with Sentence and Segment
classes. It demonstrates:

1. Programmatic creation of Segments with various attributes
2. Building Sentences from Segments
3. Converting to SSML, SSMD, and plain text
4. Using PhonemeAttrs, ProsodyAttrs, and other type objects
5. Working with TTS capabilities for engine-specific output

The Segment and Sentence classes are the core building blocks of SSMD, allowing
you to build TTS content programmatically or process parsed SSMD for custom pipelines.
"""

from ssmd import (
    TTSCapabilities,
    get_preset,
    parse_segments,
    parse_sentences,
)
from ssmd.segment import Segment
from ssmd.sentence import Sentence
from ssmd.types import (
    AudioAttrs,
    BreakAttrs,
    PhonemeAttrs,
    ProsodyAttrs,
    SayAsAttrs,
    VoiceAttrs,
)


def example_1_segment_basics():
    """Example 1: Creating segments programmatically."""
    print("=" * 70)
    print("Example 1: Segment Basics - Creating Segments Programmatically")
    print("=" * 70)

    # Simple text segment
    seg1 = Segment(text="Hello world")
    print("\n1a. Plain segment:")
    print(f"    Text: {seg1.text!r}")
    print(f"    SSML: {seg1.to_ssml()}")
    print(f"    SSMD: {seg1.to_ssmd()}")

    # Segment with emphasis
    seg2 = Segment(text="important", emphasis=True)
    print("\n1b. Emphasized segment:")
    print(f"    Text: {seg2.text!r}, emphasis={seg2.emphasis}")
    print(f"    SSML: {seg2.to_ssml()}")
    print(f"    SSMD: {seg2.to_ssmd()}")

    # Strong emphasis
    seg3 = Segment(text="CRITICAL", emphasis="strong")
    print("\n1c. Strong emphasis:")
    print(f"    Text: {seg3.text!r}, emphasis={seg3.emphasis!r}")
    print(f"    SSML: {seg3.to_ssml()}")
    print(f"    SSMD: {seg3.to_ssmd()}")

    # Segment with break after
    seg4 = Segment(
        text="Pause here",
        breaks_after=[BreakAttrs(time="500ms")],
    )
    print("\n1d. Segment with break:")
    print(f"    Text: {seg4.text!r}")
    print(f"    Breaks after: {[b.time for b in seg4.breaks_after]}")
    print(f"    SSML: {seg4.to_ssml()}")
    print(f"    SSMD: {seg4.to_ssmd()}")


def example_2_phoneme_attrs():
    """Example 2: Working with PhonemeAttrs."""
    print("\n" + "=" * 70)
    print("Example 2: PhonemeAttrs - Pronunciation Control")
    print("=" * 70)

    # IPA phoneme (default alphabet)
    phoneme_ipa = PhonemeAttrs(ph="təˈmeɪtoʊ")
    seg1 = Segment(text="tomato", phoneme=phoneme_ipa)

    print("\n2a. IPA phoneme:")
    print(f"    Text: {seg1.text!r}")
    print(f"    Phoneme: {seg1.phoneme.ph!r} (alphabet: {seg1.phoneme.alphabet})")
    print(f"    SSML: {seg1.to_ssml()}")
    print(f"    SSMD: {seg1.to_ssmd()}")

    # X-SAMPA phoneme (will be converted to IPA in SSML)
    phoneme_xsampa = PhonemeAttrs(ph='t@"meItoU', alphabet="x-sampa")
    seg2 = Segment(text="tomato", phoneme=phoneme_xsampa)

    print("\n2b. X-SAMPA phoneme (converted to IPA in SSML):")
    print(f"    Text: {seg2.text!r}")
    print(f"    Phoneme: {seg2.phoneme.ph!r} (alphabet: {seg2.phoneme.alphabet})")
    print(f"    SSML: {seg2.to_ssml()}")
    print(f"    SSMD: {seg2.to_ssmd()}")

    # Parse SSMD with phoneme and inspect
    ssmd_text = "Say [GIF](ph: dʒɪf) correctly."
    segments = parse_segments(ssmd_text)

    print("\n2c. Parsed phoneme from SSMD:")
    print(f"    Input: {ssmd_text!r}")
    for seg in segments:
        if seg.phoneme:
            print("    Found phoneme segment:")
            print(f"      text: {seg.text!r}")
            print(f"      phoneme.ph: {seg.phoneme.ph!r}")
            print(f"      phoneme.alphabet: {seg.phoneme.alphabet!r}")


def example_3_prosody_attrs():
    """Example 3: Working with ProsodyAttrs."""
    print("\n" + "=" * 70)
    print("Example 3: ProsodyAttrs - Volume, Rate, and Pitch")
    print("=" * 70)

    # Volume control
    prosody_loud = ProsodyAttrs(volume="x-loud")
    seg1 = Segment(text="Listen carefully", prosody=prosody_loud)

    print("\n3a. Volume control:")
    print(f"    Text: {seg1.text!r}")
    print(f"    Prosody: volume={seg1.prosody.volume}")
    print(f"    SSML: {seg1.to_ssml()}")
    print(f"    SSMD: {seg1.to_ssmd()}")

    # Rate control
    prosody_slow = ProsodyAttrs(rate="slow")
    seg2 = Segment(text="Take your time", prosody=prosody_slow)

    print("\n3b. Rate control:")
    print(f"    Text: {seg2.text!r}")
    print(f"    Prosody: rate={seg2.prosody.rate}")
    print(f"    SSML: {seg2.to_ssml()}")
    print(f"    SSMD: {seg2.to_ssmd()}")

    # Combined prosody
    prosody_combined = ProsodyAttrs(volume="loud", rate="fast", pitch="high")
    seg3 = Segment(text="Exciting news", prosody=prosody_combined)

    print("\n3c. Combined prosody (volume + rate + pitch):")
    print(f"    Text: {seg3.text!r}")
    print(
        f"    Prosody: volume={seg3.prosody.volume}, rate={seg3.prosody.rate}, "
        f"pitch={seg3.prosody.pitch}"
    )
    print(f"    SSML: {seg3.to_ssml()}")
    print(f"    SSMD: {seg3.to_ssmd()}")


def example_4_say_as_attrs():
    """Example 4: Working with SayAsAttrs."""
    print("\n" + "=" * 70)
    print("Example 4: SayAsAttrs - Text Interpretation")
    print("=" * 70)

    # Telephone number
    say_as_phone = SayAsAttrs(interpret_as="telephone")
    seg1 = Segment(text="+1-800-555-0123", say_as=say_as_phone)

    print("\n4a. Telephone interpretation:")
    print(f"    Text: {seg1.text!r}")
    print(f"    Say-as: interpret_as={seg1.say_as.interpret_as!r}")
    print(f"    SSML: {seg1.to_ssml()}")

    # Date with format
    say_as_date = SayAsAttrs(interpret_as="date", format="mdy")
    seg2 = Segment(text="01/15/2024", say_as=say_as_date)

    print("\n4b. Date with format:")
    print(f"    Text: {seg2.text!r}")
    print(f"    Say-as: interpret_as={seg2.say_as.interpret_as!r}, format={seg2.say_as.format!r}")
    print(f"    SSML: {seg2.to_ssml()}")

    # Cardinal number with detail
    say_as_num = SayAsAttrs(interpret_as="cardinal", detail="2")
    seg3 = Segment(text="12345", say_as=say_as_num)

    print("\n4c. Cardinal with detail level:")
    print(f"    Text: {seg3.text!r}")
    print(f"    Say-as: interpret_as={seg3.say_as.interpret_as!r}, detail={seg3.say_as.detail!r}")
    print(f"    SSML: {seg3.to_ssml()}")


def example_5_building_sentences():
    """Example 5: Building Sentences from Segments."""
    print("\n" + "=" * 70)
    print("Example 5: Building Sentences from Segments")
    print("=" * 70)

    # Create segments
    seg1 = Segment(text="Welcome")
    seg2 = Segment(text="everyone", emphasis=True)
    seg3 = Segment(
        text="to the show",
        breaks_after=[BreakAttrs(time="500ms")],
    )

    # Build a sentence
    sentence = Sentence(
        segments=[seg1, seg2, seg3],
        voice=VoiceAttrs(name="sarah"),
    )

    print("\n5a. Simple sentence:")
    print(f"    Segments: {len(sentence.segments)}")
    print(f"    Voice: {sentence.voice.name if sentence.voice else 'default'}")
    print(f"    Plain text: {sentence.to_text()!r}")
    print(f"    SSML: {sentence.to_ssml()}")
    print(f"    SSMD: {sentence.to_ssmd()}")

    # Sentence with paragraph end marker
    sentence2 = Sentence(
        segments=[
            Segment(text="This is the end of the paragraph."),
        ],
        is_paragraph_end=True,
        breaks_after=[BreakAttrs(strength="strong")],
    )

    print("\n5b. Paragraph-ending sentence:")
    print(f"    is_paragraph_end: {sentence2.is_paragraph_end}")
    print(f"    breaks_after: {[b.strength for b in sentence2.breaks_after]}")
    print(f"    SSML: {sentence2.to_ssml()}")


def example_6_voice_attrs():
    """Example 6: Working with VoiceAttrs."""
    print("\n" + "=" * 70)
    print("Example 6: VoiceAttrs - Voice Selection")
    print("=" * 70)

    # Voice by name
    voice1 = VoiceAttrs(name="en-US-Wavenet-F")
    sentence1 = Sentence(
        segments=[Segment(text="Hello from a named voice.")],
        voice=voice1,
    )

    print("\n6a. Voice by name:")
    print(f"    Voice name: {voice1.name}")
    print(f"    SSML: {sentence1.to_ssml()}")

    # Voice by attributes (language + gender)
    voice2 = VoiceAttrs(language="en-GB", gender="female")
    sentence2 = Sentence(
        segments=[Segment(text="Hello with British accent.")],
        voice=voice2,
    )

    print("\n6b. Voice by attributes:")
    print(f"    Language: {voice2.language}, Gender: {voice2.gender}")
    print(f"    SSML: {sentence2.to_ssml()}")

    # Inline voice on segment
    seg_with_voice = Segment(
        text="Different voice here",
        voice=VoiceAttrs(name="michael"),
    )

    print("\n6c. Inline voice on segment:")
    print(f"    Segment voice: {seg_with_voice.voice.name}")
    print(f"    SSML: {seg_with_voice.to_ssml()}")


def example_7_capabilities_filtering():
    """Example 7: TTS Capabilities Filtering."""
    print("\n" + "=" * 70)
    print("Example 7: TTS Capabilities - Engine-Specific Output")
    print("=" * 70)

    # Create a segment with multiple features
    segment = Segment(
        text="important announcement",
        emphasis="strong",
        prosody=ProsodyAttrs(volume="loud"),
        language="en-US",
    )

    print("\n7a. Original segment with multiple features:")
    print(f"    emphasis: {segment.emphasis}")
    print(f"    prosody.volume: {segment.prosody.volume}")
    print(f"    language: {segment.language}")

    # Full capabilities (default)
    print("\n7b. Full capabilities (all features):")
    print(f"    SSML: {segment.to_ssml()}")

    # Google TTS (full support)
    google_caps = get_preset("google")
    print("\n7c. Google TTS capabilities:")
    print(f"    SSML: {segment.to_ssml(google_caps)}")

    # eSpeak (limited support - no emphasis)
    espeak_caps = get_preset("espeak")
    print("\n7d. eSpeak capabilities (no emphasis):")
    print(f"    emphasis supported: {espeak_caps.emphasis}")
    print(f"    SSML: {segment.to_ssml(espeak_caps)}")

    # Minimal (plain text only)
    minimal_caps = get_preset("minimal")
    print("\n7e. Minimal capabilities (plain text):")
    print(f"    SSML: {segment.to_ssml(minimal_caps)}")

    # Custom capabilities
    custom_caps = TTSCapabilities(
        emphasis=True,
        prosody=False,  # Disable prosody
        language=True,
    )
    print("\n7f. Custom capabilities (no prosody):")
    print(f"    SSML: {segment.to_ssml(custom_caps)}")


def example_8_audio_attrs():
    """Example 8: Working with AudioAttrs."""
    print("\n" + "=" * 70)
    print("Example 8: AudioAttrs - Audio File Playback")
    print("=" * 70)

    # Basic audio
    audio1 = AudioAttrs(src="https://example.com/sound.mp3")
    seg1 = Segment(text="doorbell sound", audio=audio1)

    print("\n8a. Basic audio:")
    print(f"    Description: {seg1.text!r}")
    print(f"    Audio src: {seg1.audio.src}")
    print(f"    SSML: {seg1.to_ssml()}")

    # Audio with clipping and speed
    audio2 = AudioAttrs(
        src="https://example.com/music.mp3",
        clip_begin="5s",
        clip_end="10s",
        speed="150%",
        sound_level="+6dB",
        alt_text="background music",
    )
    seg2 = Segment(text="Music interlude", audio=audio2)

    print("\n8b. Audio with advanced options:")
    print(f"    src: {seg2.audio.src}")
    print(f"    clip: {seg2.audio.clip_begin} - {seg2.audio.clip_end}")
    print(f"    speed: {seg2.audio.speed}")
    print(f"    sound_level: {seg2.audio.sound_level}")
    print(f"    alt_text: {seg2.audio.alt_text}")
    print(f"    SSML: {seg2.to_ssml()}")


def example_9_marks():
    """Example 9: Working with Marks (Event Markers)."""
    print("\n" + "=" * 70)
    print("Example 9: Marks - Event Markers for Synchronization")
    print("=" * 70)

    # Segment with marks
    seg = Segment(
        text="Important content here",
        marks_before=["section_start"],
        marks_after=["section_end"],
    )

    print("\n9a. Segment with marks:")
    print(f"    Text: {seg.text!r}")
    print(f"    marks_before: {seg.marks_before}")
    print(f"    marks_after: {seg.marks_after}")
    print(f"    SSML: {seg.to_ssml()}")

    # Multiple marks
    seg2 = Segment(
        text="Synchronized text",
        marks_before=["word_1", "highlight_start"],
        marks_after=["highlight_end"],
    )

    print("\n9b. Multiple marks:")
    print(f"    marks_before: {seg2.marks_before}")
    print(f"    marks_after: {seg2.marks_after}")
    print(f"    SSML: {seg2.to_ssml()}")


def example_10_roundtrip():
    """Example 10: Roundtrip - Parse, Inspect, Modify, Output."""
    print("\n" + "=" * 70)
    print("Example 10: Roundtrip - Parse, Inspect, Modify, Output")
    print("=" * 70)

    # Original SSMD
    original_ssmd = """
<div voice="narrator">
Hello *everyone*! Call [+1-555-0123]{as="telephone"} for info.
Say [tomato]{ipa="təˈmeɪtoʊ"} correctly.
</div>
"""

    print("\n10a. Original SSMD:")
    print(f"    {original_ssmd.strip()}")

    # Parse to sentences
    sentences = parse_sentences(original_ssmd)

    print(f"\n10b. Parsed {len(sentences)} sentences:")
    for i, sent in enumerate(sentences, 1):
        voice_name = sent.voice.name if sent.voice else "(default)"
        print(f"    Sentence {i}: voice={voice_name}, {len(sent.segments)} segments")

        for j, seg in enumerate(sent.segments, 1):
            features = []
            if seg.emphasis:
                features.append(f"emphasis={seg.emphasis}")
            if seg.say_as:
                features.append(f"say_as={seg.say_as.interpret_as}")
            if seg.phoneme:
                features.append(f"phoneme={seg.phoneme.ph!r}")
            feature_str = f" [{', '.join(features)}]" if features else ""
            print(f"      Seg {j}: {seg.text!r}{feature_str}")

    # Modify: Add extra emphasis to all segments
    print("\n10c. Modifying: Adding prosody to all segments...")
    for sent in sentences:
        for seg in sent.segments:
            if not seg.prosody:
                seg.prosody = ProsodyAttrs(volume="loud")

    # Output as SSML
    print("\n10d. Modified output (SSML):")
    for sent in sentences:
        ssml = sent.to_ssml()
        print(f"    {ssml[:80]}{'...' if len(ssml) > 80 else ''}")

    # Convert back to SSMD
    print("\n10e. Convert back to SSMD:")
    for sent in sentences:
        ssmd_out = sent.to_ssmd()
        print(f"    {ssmd_out[:70]}{'...' if len(ssmd_out) > 70 else ''}")


def example_11_extensions():
    """Example 11: Platform-Specific Extensions."""
    print("\n" + "=" * 70)
    print("Example 11: Extensions - Platform-Specific Features")
    print("=" * 70)

    # Amazon Polly whisper effect
    seg1 = Segment(text="This is a secret", extension="whisper")

    print("\n11a. Amazon Polly whisper effect:")
    print(f"    Text: {seg1.text!r}")
    print(f"    Extension: {seg1.extension}")
    print(f"    SSML: {seg1.to_ssml()}")

    # Custom extension handler
    def google_style_handler(text):
        return f'<google:style name="cheerful">{text}</google:style>'

    custom_extensions = {
        "cheerful": google_style_handler,
    }

    seg2 = Segment(text="Great news everyone", extension="cheerful")

    print("\n11b. Custom extension (Google cheerful style):")
    print(f"    Extension: {seg2.extension}")
    print(f"    SSML: {seg2.to_ssml(extensions=custom_extensions)}")


if __name__ == "__main__":
    example_1_segment_basics()
    example_2_phoneme_attrs()
    example_3_prosody_attrs()
    example_4_say_as_attrs()
    example_5_building_sentences()
    example_6_voice_attrs()
    example_7_capabilities_filtering()
    example_8_audio_attrs()
    example_9_marks()
    example_10_roundtrip()
    example_11_extensions()

    print("\n" + "=" * 70)
    print("Sentence & Segment API Demo Complete!")
    print("=" * 70)
    print("\nKey classes and types:")
    print("  - Segment: Atomic unit of text with attributes")
    print("  - Sentence: Collection of segments with voice context")
    print("  - PhonemeAttrs: Pronunciation (ph, alphabet)")
    print("  - ProsodyAttrs: Volume, rate, pitch")
    print("  - SayAsAttrs: Text interpretation (telephone, date, etc.)")
    print("  - VoiceAttrs: Voice selection (name, language, gender)")
    print("  - BreakAttrs: Pauses (time, strength)")
    print("  - AudioAttrs: Audio file playback")
    print("  - TTSCapabilities: Engine-specific feature filtering")
    print("\nUse these classes to:")
    print("  1. Parse SSMD and inspect/modify the structure")
    print("  2. Build TTS content programmatically")
    print("  3. Generate engine-specific SSML output")
    print("  4. Create custom TTS processing pipelines")

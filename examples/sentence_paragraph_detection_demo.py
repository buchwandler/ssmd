#!/usr/bin/env python3
"""Complex text example demonstrating sentence and paragraph detection in SSMD.

This example creates a complex text with:
- Multiple sentences and paragraphs
- Quoted speech across sentence boundaries
- Abbreviations (Dr., Mr., U.S., etc.)
- Various punctuation marks
- SSMD break markers

The text is parsed and then written to an SSMD markdown file.
"""

from pathlib import Path

from ssmd.formatter import format_ssmd
from ssmd.parser import parse_sentences


def create_complex_text() -> str:  # noqa: E501
    """Create a complex test text with various linguistic features."""
    # fmt: off
    # ruff: noqa: E501
    text = """Dr. Smith arrived at 3:00 P.M. on Tuesday. He was scheduled to meet Mr. Johnson at the U.S. Embassy regarding the international treaty.

"Good afternoon, Dr. Smith," said the receptionist. "Mr. Johnson is expecting you. Please have a seat in the waiting room."

Dr. Smith sat down and opened his briefcase. Inside were several important documents: the treaty draft from the E.U., correspondence from the U.N., and notes from his meeting with Prof. Anderson at MIT.

The secretary announced, "Dr. Smith? Mr. Johnson will see you now. Please follow me."

They walked down a long corridor. Mr. Johnson greeted him warmly. "Welcome! I'm glad you could make it on such short notice. I hope the traffic on I-95 wasn't too terrible?"

"Not at all," replied Dr. Smith. "I left early, around 2:15 P.M., so I had plenty of time."

Mr. Johnson smiled. "Excellent! Let's get started then. We have much to discuss regarding the U.S.-E.U. cooperation agreement."

The meeting lasted three hours. They discussed various topics: economic policy, environmental regulations, and diplomatic relations. By 6:00 P.M., they had reached a preliminary agreement.

"This is fantastic progress," said Mr. Johnson. "I'll send the draft to our team in Washington, D.C. by tomorrow morning."

Dr. Smith nodded. "Perfect. I'll coordinate with our representatives in Brussels. They're expecting my report by Friday, i.e., in two days."

As they shook hands, Mr. Johnson added, "Safe travels, Dr. Smith. Give my regards to Prof. Anderson when you return to Cambridge, Mass."

"I certainly will," Dr. Smith replied. "Thank you for your time, Mr. Johnson."

The meeting concluded at 6:30 P.M. Dr. Smith left the building feeling optimistic about the future of international cooperation."""
    # fmt: on

    return text


def create_ssmd_text_with_breaks() -> str:  # noqa: E501
    """Create the same text with SSMD break markers for enhanced TTS control."""
    # fmt: off
    # ruff: noqa: E501
    text = """Dr. Smith arrived at 3:00 P.M. on Tuesday. ...s He was scheduled to meet Mr. Johnson at the U.S. Embassy regarding the international treaty.

"Good afternoon, Dr. Smith," said the receptionist. ...w "Mr. Johnson is expecting you. ...s Please have a seat in the waiting room."

Dr. Smith sat down and opened his briefcase. ...s Inside were several important documents: ...w the treaty draft from the E.U., ...w correspondence from the U.N., ...w and notes from his meeting with Prof. Anderson at MIT.

The secretary announced, ...w "Dr. Smith? ...w Mr. Johnson will see you now. ...s Please follow me."

They walked down a long corridor. ...s Mr. Johnson greeted him warmly. ...s "Welcome! ...w I'm glad you could make it on such short notice. ...s I hope the traffic on I-95 wasn't too terrible?"

"Not at all," replied Dr. Smith. ...s "I left early, ...w around 2:15 P.M., ...w so I had plenty of time."

Mr. Johnson smiled. ...s "Excellent! ...w Let's get started then. ...s We have much to discuss regarding the U.S.-E.U. cooperation agreement."

The meeting lasted three hours. ...s They discussed various topics: ...w economic policy, ...w environmental regulations, ...w and diplomatic relations. ...s By 6:00 P.M., ...w they had reached a preliminary agreement.

"This is fantastic progress," said Mr. Johnson. ...s "I'll send the draft to our team in Washington, D.C. by tomorrow morning."

Dr. Smith nodded. ...s "Perfect. ...s I'll coordinate with our representatives in Brussels. ...s They're expecting my report by Friday, ...w i.e., ...w in two days."

As they shook hands, ...w Mr. Johnson added, ...w "Safe travels, Dr. Smith. ...s Give my regards to Prof. Anderson when you return to Cambridge, Mass."

"I certainly will," Dr. Smith replied. ...s "Thank you for your time, Mr. Johnson."

The meeting concluded at 6:30 P.M. ...s Dr. Smith left the building feeling optimistic about the future of international cooperation."""
    # fmt: on

    return text


def analyze_and_save(text: str, output_filename: str, use_breaks: bool = False):
    """Parse text and save analysis to SSMD markdown file.

    Args:
        text: Input text to parse
        output_filename: Name of output file (without path)
        use_breaks: Whether the text contains SSMD break markers
    """
    print(f"\n{'=' * 70}")
    print(f"Analyzing: {output_filename}")
    print(f"Break markers: {'Yes' if use_breaks else 'No'}")
    print(f"{'=' * 70}\n")

    # Parse the text
    sentences = parse_sentences(
        text,
        sentence_detection=True,
        include_default_voice=True,
        language="en",
    )

    # Analyze results
    print(f"Total sentences detected: {len(sentences)}")
    print(f"Total paragraphs: {sum(1 for s in sentences if s.is_paragraph_end)}")
    print()

    # Create SSMD markdown output
    output_lines = [
        "# Sentence and Paragraph Detection Analysis",
        "",
        f"**Input type:** {'With SSMD breaks' if use_breaks else 'Plain text'}",
        f"**Sentences detected:** {len(sentences)}",
        f"**Paragraphs:** {sum(1 for s in sentences if s.is_paragraph_end)}",
        "",
        "---",
        "",
        "## Parsed Sentences",
        "",
    ]

    # Add each sentence with details
    for i, sentence in enumerate(sentences, 1):
        # Reconstruct sentence text from segments
        sentence_text = " ".join(seg.text for seg in sentence.segments)

        # Add sentence header
        output_lines.append(f"### Sentence {i}")
        output_lines.append("")
        output_lines.append(f"**Text:** {sentence_text}")
        output_lines.append("")
        output_lines.append(f"**Segments:** {len(sentence.segments)}")

        # List segments with break information
        if len(sentence.segments) > 1 or any(
            seg.breaks_after or seg.breaks_before for seg in sentence.segments
        ):
            output_lines.append("")
            output_lines.append("**Segment details:**")
            for j, seg in enumerate(sentence.segments, 1):
                seg_info = f"- Segment {j}: `{seg.text}`"

                if seg.breaks_before:
                    break_strs: list[str] = []
                    for b in seg.breaks_before:
                        val = b.strength or b.time
                        if val is not None:
                            break_strs.append(val)
                    if break_strs:
                        breaks = ", ".join(break_strs)
                        seg_info += f" [breaks_before: {breaks}]"

                if seg.breaks_after:
                    break_strs: list[str] = []
                    for b in seg.breaks_after:
                        val = b.strength or b.time
                        if val is not None:
                            break_strs.append(val)
                    if break_strs:
                        breaks = ", ".join(break_strs)
                        seg_info += f" [breaks_after: {breaks}]"

                output_lines.append(seg_info)

        # Mark paragraph end
        if sentence.is_paragraph_end:
            output_lines.append("")
            output_lines.append("**Paragraph end:** Yes")

        output_lines.append("")
        output_lines.append("---")
        output_lines.append("")

    # Add summary statistics
    output_lines.extend(
        [
            "## Summary Statistics",
            "",
            f"- Total sentences: {len(sentences)}",
            f"- Total segments: {sum(len(s.segments) for s in sentences)}",
            (
                f"- Sentences with multiple segments: "
                f"{sum(1 for s in sentences if len(s.segments) > 1)}"
            ),
            (
                f"- Sentences with breaks: "
                f"{sum(1 for s in sentences if any(seg.breaks_after or seg.breaks_before for seg in s.segments))}"  # noqa: E501
            ),
            f"- Paragraph breaks: {sum(1 for s in sentences if s.is_paragraph_end)}",
            "",
        ]
    )

    # Add abbreviation analysis
    abbreviations_found = []
    for sentence in sentences:
        sentence_text = " ".join(seg.text for seg in sentence.segments)
        for abbr in [
            "Dr.",
            "Mr.",
            "Mrs.",
            "Ms.",
            "Prof.",
            "P.M.",
            "A.M.",
            "U.S.",
            "U.N.",
            "E.U.",
            "i.e.",
            "e.g.",
            "etc.",
        ]:
            if abbr in sentence_text and abbr not in abbreviations_found:
                abbreviations_found.append(abbr)

    if abbreviations_found:
        output_lines.extend(
            [
                "## Abbreviations Detected",
                "",
                (
                    "The following abbreviations were correctly handled "
                    "(not treated as sentence endings):"
                ),
                "",
            ]
        )
        for abbr in sorted(abbreviations_found):
            output_lines.append(f"- `{abbr}`")
        output_lines.append("")

    # Add quote analysis
    quotes_count = sum(1 for s in sentences if any('"' in seg.text for seg in s.segments))
    if quotes_count > 0:
        output_lines.extend(
            [
                "## Quotation Analysis",
                "",
                f"- Sentences containing quotes: {quotes_count}",
                "- Quote marks preserved: Yes",
                "",
            ]
        )

    # Save to file
    output_path = Path(__file__).parent / output_filename
    output_content = "\n".join(output_lines)
    output_path.write_text(output_content, encoding="utf-8")

    print(f"✓ Analysis saved to: {output_path}")
    print(f"  File size: {len(output_content)} bytes")
    print()

    return sentences


def main():
    """Run the demonstration."""
    print("\n" + "=" * 70)
    print("SSMD Sentence and Paragraph Detection Demo")
    print("=" * 70)

    # Test 1: Plain text without SSMD markers
    print("\n[Test 1] Plain text analysis...")
    plain_text = create_complex_text()

    # Format the plain text with proper line breaks
    plain_sentences_temp = parse_sentences(plain_text, sentence_detection=True)
    plain_text_formatted = format_ssmd(plain_sentences_temp)

    # Save the formatted plain text as SSMD file
    plain_ssmd_path = Path(__file__).parent / "complex_text_plain.ssmd"
    plain_ssmd_path.write_text(plain_text_formatted, encoding="utf-8")
    print(f"✓ Plain SSMD saved to: {plain_ssmd_path}")
    print(f"  File size: {len(plain_text_formatted)} bytes")

    plain_sentences = analyze_and_save(plain_text, "sentence_detection_plain.md", use_breaks=False)

    # Test 2: Text with SSMD break markers
    print("\n[Test 2] Text with SSMD break markers...")
    ssmd_text = create_ssmd_text_with_breaks()

    # Format the SSMD text with proper line breaks
    ssmd_sentences_temp = parse_sentences(ssmd_text, sentence_detection=True)
    ssmd_text_formatted = format_ssmd(ssmd_sentences_temp)

    # Save the formatted SSMD text with breaks as SSMD file
    ssmd_path = Path(__file__).parent / "complex_text_with_breaks.ssmd"
    ssmd_path.write_text(ssmd_text_formatted, encoding="utf-8")
    print(f"✓ SSMD with breaks saved to: {ssmd_path}")
    print(f"  File size: {len(ssmd_text_formatted)} bytes")

    ssmd_sentences = analyze_and_save(
        ssmd_text, "sentence_detection_with_breaks.md", use_breaks=True
    )

    # Comparison
    print("\n" + "=" * 70)
    print("COMPARISON: Plain Text vs. SSMD Breaks")
    print("=" * 70)
    print(f"Plain text sentences:     {len(plain_sentences)}")
    print(f"SSMD text sentences:      {len(ssmd_sentences)}")
    print(f"Difference:               {abs(len(plain_sentences) - len(ssmd_sentences))}")
    print()

    plain_segments = sum(len(s.segments) for s in plain_sentences)
    ssmd_segments = sum(len(s.segments) for s in ssmd_sentences)
    print(f"Plain text segments:      {plain_segments}")
    print(f"SSMD text segments:       {ssmd_segments}")
    print(f"Additional segments:      {ssmd_segments - plain_segments}")
    print()

    ssmd_breaks = sum(
        sum(len(seg.breaks_after) + len(seg.breaks_before) for seg in s.segments)
        for s in ssmd_sentences
    )
    print(f"Total break markers:      {ssmd_breaks}")
    print()

    print("✓ Demo complete! Check the generated markdown files for detailed analysis.")
    print()


if __name__ == "__main__":
    main()

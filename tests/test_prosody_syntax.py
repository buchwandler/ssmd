"""Regression tests for compact and symbolic SSMD prosody syntax."""

import pytest

import ssmd


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("555", ("x-loud", "x-fast", "x-high")),
        (" 524 ", ("x-loud", "slow", "high")),
        ("011", ("silent", "x-slow", "x-low")),
        ("135", ("x-soft", "medium", "x-high")),
    ],
)
def test_vrp_normalizes_volume_rate_pitch(value, expected):
    segment = next(
        segment
        for segment in ssmd.parse_segments(f'[text]{{vrp="{value}"}}')
        if segment.text == "text"
    )

    assert segment.prosody is not None
    assert (segment.prosody.volume, segment.prosody.rate, segment.prosody.pitch) == expected


def test_vrp_overrides_are_applied_per_field():
    segment = next(
        segment
        for segment in ssmd.parse_segments('[text]{vrp="555" r="2" pitch="low"}')
        if segment.text == "text"
    )

    assert segment.prosody is not None
    assert segment.prosody.volume == "x-loud"
    assert segment.prosody.rate == "slow"
    assert segment.prosody.pitch == "low"


def test_vrp_long_name_overrides_short_name():
    segment = next(
        segment
        for segment in ssmd.parse_segments('[text]{vrp="555" r="2" rate="fast"}')
        if segment.text == "text"
    )

    assert segment.prosody is not None
    assert segment.prosody.rate == "fast"


def test_vrp_converts_to_ssml_and_canonical_ssmd():
    ssml = ssmd.to_ssml('[text]{vrp="555"}')

    assert '<prosody volume="x-loud" rate="x-fast" pitch="x-high">text</prosody>' in ssml
    assert ssmd.Document('[text]{vrp="555"}').to_ssmd() == (
        '[text]{volume="x-loud" rate="x-fast" pitch="x-high"}'
    )


@pytest.mark.parametrize("value", ["", "55", "5555", "abc", "505", "550", "678", "5 5"])
def test_invalid_vrp_is_plain_text_with_lint_diagnostic(value):
    source = f'[text]{{vrp="{value}"}}'

    assert "<prosody" not in ssmd.to_ssml(source)
    assert ssmd.to_text(source) == "text"

    issues = ssmd.lint(source)
    issue = next(issue for issue in issues if issue.code == "prosody.invalid_vrp")
    assert issue.severity == "warn"
    assert issue.message == (
        f"Invalid vrp value '{value}'; expected exactly three digits matching [0-5][1-5][1-5]."
    )


def test_vrp_is_tagged_as_prosody_in_spans():
    result = ssmd.parse_spans('[text]{vrp="555"}')

    assert result.clean_text == "text"
    assert result.annotations[0].attrs == {"vrp": "555", "tag": "prosody"}


def test_vrp_is_supported_on_div_directives():
    blocks = ssmd.parse_voice_blocks('<div vrp="524">\nText.\n</div>')

    assert blocks[0][0].prosody is not None
    assert blocks[0][0].prosody.rate == "slow"
    assert 'rate="slow"' in ssmd.to_ssml('<div vrp="524">\nText.\n</div>')


@pytest.mark.parametrize(
    ("source", "field", "expected"),
    [
        ("++extra loud++", "volume", "x-loud"),
        (">>extra fast>>", "rate", "x-fast"),
        ("^^extra high^^", "pitch", "x-high"),
        ("~silent~", "volume", "silent"),
        ("--extra soft--", "volume", "x-soft"),
        ("-soft-", "volume", "soft"),
        ("+loud+", "volume", "loud"),
        ("<<extra slow<<", "rate", "x-slow"),
        ("<slow<", "rate", "slow"),
        (">fast>", "rate", "fast"),
        ("__extra low__", "pitch", "x-low"),
        ("^high^", "pitch", "high"),
    ],
)
def test_symbolic_prosody_aliases(source, field, expected):
    segment = next(segment for segment in ssmd.parse_segments(source) if segment.text)

    assert getattr(segment.prosody, field) == expected
    assert segment.to_text() == source.strip(source[0])


def test_single_underscore_remains_reduced_emphasis():
    segment = next(segment for segment in ssmd.parse_segments("_low_") if segment.text == "low")

    assert segment.emphasis == "reduced"
    assert segment.prosody is None


def test_symbolic_aliases_protect_sentence_punctuation():
    sentences = ssmd.parse_sentences("Start. ++Is this loud? Yes!++ End.", use_spacy=False)

    assert len(sentences) == 2
    assert sentences[1].segments[0].text == "Is this loud? Yes!"
    assert sentences[1].segments[0].prosody is not None


def test_symbolic_aliases_are_xml_escaped():
    result = ssmd.to_ssml("++<unsafe & text>++")

    assert "&lt;unsafe &amp; text&gt;" in result
    assert "<unsafe" not in result


@pytest.mark.parametrize(
    "source", ["C++ is a language.", "a >> 2", "x > y", "a < b", "foo-bar", "--option", "2 + 2"]
)
def test_operator_text_is_not_overconsumed(source):
    segments = ssmd.parse_segments(source)

    assert "".join(segment.text for segment in segments) == source
    assert all(segment.prosody is None for segment in segments)


def test_doubled_delimiters_take_precedence_over_single_forms():
    cases = [
        ("++loud++", "x-loud"),
        (">>fast>>", "x-fast"),
        ("^^high^^", "x-high"),
        ("--soft--", "x-soft"),
    ]

    for source, expected in cases:
        segment = next(segment for segment in ssmd.parse_segments(source) if segment.text)
        assert expected in {segment.prosody.volume, segment.prosody.rate, segment.prosody.pitch}


def test_capability_filtering_matches_explicit_prosody():
    symbolic = ssmd.to_ssml("++loud++", capabilities="minimal")
    explicit = ssmd.to_ssml('[loud]{volume="x-loud"}', capabilities="minimal")

    assert symbolic == explicit


def test_symbolic_aliases_escape_and_unescape_without_semantics():
    source = "Use ++this++ literally."
    escaped = ssmd.escape_ssmd_syntax(source)

    assert escaped != source
    assert ssmd.unescape_ssmd_syntax(escaped) == source
    assert ssmd.Document(source, escape_syntax=True).to_text() == source
    assert all(segment.prosody is None for segment in ssmd.parse_segments(escaped))


def test_selective_prosody_escaping_leaves_emphasis_untouched():
    source = "*emphasis* and ++literal++"
    escaped = ssmd.escape_ssmd_syntax(source, patterns=["prosody"])

    assert "*emphasis*" in escaped
    assert "++literal++" not in escaped


def test_from_ssml_keeps_explicit_prosody_serialization():
    result = ssmd.from_ssml('<speak><prosody volume="loud">text</prosody></speak>')

    assert '[text]{volume="loud"}' in result

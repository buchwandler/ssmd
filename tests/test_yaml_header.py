"""Tests for YAML header parsing in SSMD."""

import pytest

import ssmd
from ssmd.rendering import RenderError


def test_yaml_header_parsed_and_removed():
    text = """---
voice:
  languageCode: en-us
  name: en-US-Standard-B
  ssmlGender: MALE
audioConfig:
  audioEncoding: MP3
author: Jane Doe
chapter: 3
---
Hello world.
"""
    doc = ssmd.Document(text, parse_yaml_header=True)
    assert doc.header is not None
    assert doc.header["voice"]["languageCode"] == "en-us"
    assert doc.header["audioConfig"]["audioEncoding"] == "MP3"
    assert doc.header["author"] == "Jane Doe"
    assert "---" not in doc.ssmd
    assert doc.ssmd.strip() == "Hello world."


def test_yaml_header_ignored_when_disabled():
    text = """---
voice:
  languageCode: en-us
---
Hello world.
"""
    doc = ssmd.Document(text, parse_yaml_header=False)
    assert doc.header is None
    assert doc.ssmd.lstrip().startswith("---")
    assert "languageCode" in doc.ssmd


def test_yaml_header_parse_sentences_disabled_preserves_header():
    text = """---
title: Demo
---
Hello world.
"""
    sentences = ssmd.parse_sentences(text, parse_yaml_header=False, use_spacy=False)
    assert sentences
    combined = "\n".join(sentence.to_ssmd() for sentence in sentences)
    assert "---" in combined
    assert "title" in combined


def test_yaml_header_parse_sentences_enabled_strips_header():
    text = """---
title: Demo
---
Hello world.
"""
    sentences = ssmd.parse_sentences(text, parse_yaml_header=True, use_spacy=False)
    combined = "\n".join(sentence.to_ssmd() for sentence in sentences)
    assert "---" not in combined
    assert "Hello world." in combined


def test_yaml_header_supports_dots_end_marker():
    text = """---
voice:
  languageCode: en-us
...
Hello world.
"""
    doc = ssmd.Document(text, parse_yaml_header=True)
    assert doc.header is not None
    assert doc.header["voice"]["languageCode"] == "en-us"
    assert doc.ssmd.strip() == "Hello world."


def test_yaml_header_extension_templates_are_not_executed() -> None:
    text = """---
ssmd_version: "0.9"
heading:
  - level_1:
      pause_before: 300ms
      emphasis: strong
      pause: 300ms
extensions:
  - cheerful:
      value: '<google:style name="cheerful">{text}</google:style>'
---
[Welcome]{ext="cheerful"}
"""
    doc = ssmd.Document(text, parse_yaml_header=True)
    assert doc.header is not None
    assert "extensions" in doc.header

    with pytest.raises(RenderError) as error:
        doc.to_ssml(target="generic")
    assert any(item.code == "header.extension_template_unsafe" for item in error.value.diagnostics)


def test_yaml_header_extension_template_requires_trusted_registry() -> None:
    text = """---
extensions:
  - custom:
      value: "<custom></custom>"
---
[Hello]{ext="custom"}
"""
    doc = ssmd.Document(text, parse_yaml_header=True)
    ssml = doc.to_ssml(target="generic")

    assert "Hello" in ssml
    assert "custom" not in ssml
    assert any(item.code == "render.unsupported.extension" for item in doc.render_diagnostics)

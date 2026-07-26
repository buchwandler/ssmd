"""Tests for packaged runtime resources and metadata consistency."""

import importlib.resources as resources
from pathlib import Path

import tomllib

from ssmd.capabilities import get_preset
from ssmd.segment import xsampa_to_ipa


def test_packaged_capability_data_available():
    data_dir = resources.files("ssmd").joinpath("data")

    for filename in (
        "amazon-alexa.json",
        "amazon-polly.json",
        "blank.json",
        "google-home.json",
        "ibm-watson.json",
        "microsoft-azure.json",
        "microsoft-cortana.json",
    ):
        assert data_dir.joinpath(filename).is_file()
    assert get_preset("google").ssml_green


def test_xsampa_known_conversion():
    assert xsampa_to_ipa("t@meItoU") == "təmeɪtoʊ"


def test_project_metadata_is_consistently_mit():
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = metadata["project"]

    assert project["keywords"] == ["ssml", "ssmd", "tts", "text-to-speech"]
    assert "License :: OSI Approved :: MIT License" in project["classifiers"]
    assert not any("Apache Software License" in value for value in project["classifiers"])

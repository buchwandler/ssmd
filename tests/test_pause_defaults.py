"""Tests for pause-default parsing and serialization."""

from ssmd.config import normalize_config
from ssmd.durations import duration_milliseconds, parse_duration


def test_pause_duration_normalization():
    assert parse_duration("1.50s") == "1.5s"
    assert duration_milliseconds("1.5s") == 1500
    config = normalize_config({"pause_defaults": {"enabled": True, "sentence": "250ms"}})
    assert config.pause_defaults.to_dict() == {"enabled": True, "sentence": "250ms"}

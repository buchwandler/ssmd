"""Tests for local SSMD configuration."""

from ssmd.config import (
    atomic_save_config,
    dotted_get,
    dotted_set,
    dotted_unset,
    load_raw_config,
    normalize_config,
    resolve_config_path,
    starter_config,
    validate_config,
)


def test_config_path_precedence(monkeypatch, tmp_path):
    env_path = tmp_path / "env.yaml"
    monkeypatch.setenv("SSMD_CONFIG", str(env_path))
    assert resolve_config_path()[0] == env_path
    option_path = tmp_path / "option.yaml"
    assert resolve_config_path(option_path)[0] == option_path


def test_atomic_config_and_dotted_mutation(tmp_path):
    path = tmp_path / "nested" / "config.yaml"
    raw = starter_config()
    dotted_set(raw, "authoring.default_voice_provider", "kokoro")
    atomic_save_config(path, raw)
    loaded = load_raw_config(path)
    assert dotted_get(loaded, "authoring.default_voice_provider") == "kokoro"
    assert dotted_unset(loaded, "authoring.default_voice_provider") is True
    assert "default_voice_provider" not in loaded["authoring"]


def test_config_validation_and_normalization():
    raw = starter_config()
    raw["pause_defaults"] = {"enabled": True, "sentence": "250ms"}
    assert not [issue for issue in validate_config(raw) if issue.severity == "error"]
    assert normalize_config(raw).pause_defaults.sentence == "250ms"
    raw["schema"] = "ssmd.config.v99"
    assert any(issue.code == "config.schema_unsupported" for issue in validate_config(raw))

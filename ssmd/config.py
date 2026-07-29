"""Local SSMD authoring configuration.

The configuration file is intentionally separate from the portable SSMD
document.  This module provides path resolution, typed normalization,
validation, dotted-key mutation, and atomic persistence for that file.
"""

from __future__ import annotations

import copy
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

import click
import yaml

from ssmd.durations import parse_duration

CONFIG_SCHEMA = "ssmd.config.v1"
MATERIALIZE_VOICE_MODES = ("never", "when-needed", "always")
MATERIALIZE_PAUSE_MODES = ("never", "when-enabled", "always")
GENDERS = ("male", "female", "neutral")


class ConfigError(ValueError):
    """A configuration error with a stable machine-readable code."""

    def __init__(self, message: str, *, code: str = "config.invalid") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ConfigIssue:
    """A config validation issue."""

    code: str
    severity: Literal["error", "warn"]
    message: str
    path: str | None = None


@dataclass(frozen=True)
class MaterializeConfig:
    """Header materialization policy."""

    voice_bindings: Literal["never", "when-needed", "always"] = "when-needed"
    pause_defaults: Literal["never", "when-enabled", "always"] = "when-enabled"


@dataclass(frozen=True)
class AuthoringConfig:
    """Authoring defaults."""

    default_voice_provider: str | None = None
    materialize: MaterializeConfig = field(default_factory=MaterializeConfig)


@dataclass(frozen=True)
class VoiceInventoryEntry:
    """One locally available provider voice."""

    provider: str
    voice_id: str
    language: str | None = None
    gender: Literal["male", "female", "neutral"] | None = None
    description: str | None = None
    tags: tuple[str, ...] = ()
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/YAML-safe representation."""
        return {
            "provider": self.provider,
            "id": self.voice_id,
            "language": self.language,
            "gender": self.gender,
            "description": self.description,
            "tags": list(self.tags),
            "enabled": self.enabled,
        }


@dataclass(frozen=True)
class PauseDefaults:
    """Document-level pause defaults."""

    enabled: bool = False
    sentence: str | None = None
    paragraph: str | None = None
    voice_change: str | None = None

    def to_dict(self, *, include_none: bool = False) -> dict[str, Any]:
        """Return normalized pause values."""
        values: dict[str, Any] = {"enabled": self.enabled}
        for key in ("sentence", "paragraph", "voice_change"):
            value = getattr(self, key)
            if include_none or value is not None:
                values[key] = value
        return values


@dataclass(frozen=True)
class SSMDUserConfig:
    """Immutable normalized SSMD user configuration."""

    schema: str = CONFIG_SCHEMA
    authoring: AuthoringConfig = field(default_factory=AuthoringConfig)
    voice_inventory: Mapping[str, Mapping[str, VoiceInventoryEntry]] = field(default_factory=dict)
    voice_bindings: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    pause_defaults: PauseDefaults = field(default_factory=PauseDefaults)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON/YAML-safe representation."""
        inventory: dict[str, dict[str, Any]] = {}
        for provider in sorted(self.voice_inventory):
            inventory[provider] = {}
            for voice_id in sorted(self.voice_inventory[provider]):
                entry = self.voice_inventory[provider][voice_id]
                values = entry.to_dict()
                values.pop("provider", None)
                values.pop("id", None)
                inventory[provider][voice_id] = values

        bindings = {
            provider: {
                reference: self.voice_bindings[provider][reference]
                for reference in sorted(self.voice_bindings[provider])
            }
            for provider in sorted(self.voice_bindings)
        }
        return {
            "schema": self.schema,
            "authoring": {
                "default_voice_provider": self.authoring.default_voice_provider,
                "materialize": {
                    "voice_bindings": self.authoring.materialize.voice_bindings,
                    "pause_defaults": self.authoring.materialize.pause_defaults,
                },
            },
            "voice_inventory": inventory,
            "voice_bindings": bindings,
            "pause_defaults": self.pause_defaults.to_dict(),
        }


def starter_config(*, minimal: bool = False) -> dict[str, Any]:
    """Return a fresh starter config mapping."""
    if minimal:
        return {"schema": CONFIG_SCHEMA}
    return {
        "schema": CONFIG_SCHEMA,
        "authoring": {
            "default_voice_provider": None,
            "materialize": {
                "voice_bindings": "when-needed",
                "pause_defaults": "when-enabled",
            },
        },
        "voice_inventory": {},
        "voice_bindings": {},
        "pause_defaults": {"enabled": False},
    }


def resolve_config_path(config: str | Path | None = None) -> tuple[Path, str]:
    """Resolve config path using CLI, environment, then Click defaults."""
    if config is not None:
        return Path(config).expanduser(), "option"
    env_path = os.environ.get("SSMD_CONFIG")
    if env_path:
        return Path(env_path).expanduser(), "environment"
    return Path(click.get_app_dir("ssmd", roaming=False)) / "config.yaml", "default"


def load_raw_config(path: str | Path) -> dict[str, Any]:
    """Load a raw mapping, returning an empty mapping for a missing file."""
    config_path = Path(path)
    if not config_path.exists():
        return {}
    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Unable to read config: {exc}", code="config.yaml_invalid") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigError("Config root must be a mapping", code="config.root_not_mapping")
    return dict(loaded)


def _mapping(value: Any, path: str, issues: list[ConfigIssue]) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    issues.append(
        ConfigIssue("config.mapping_expected", "error", f"{path} must be a mapping", path)
    )
    return {}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Coerce an arbitrary value to a read-only mapping view for normalization."""
    return value if isinstance(value, Mapping) else {}


def validate_config(raw: Mapping[str, Any]) -> list[ConfigIssue]:  # noqa: C901
    """Validate config syntax and semantic references without mutating it."""
    issues: list[ConfigIssue] = []
    schema = raw.get("schema", CONFIG_SCHEMA)
    if schema != CONFIG_SCHEMA:
        issues.append(
            ConfigIssue(
                "config.schema_unsupported",
                "error",
                f"Unsupported config schema: {schema}",
                "schema",
            )
        )

    known = {"schema", "authoring", "voice_inventory", "voice_bindings", "pause_defaults"}
    for key in raw:
        if key not in known:
            issues.append(
                ConfigIssue("config.unknown_key", "warn", f"Unknown config key: {key}", key)
            )

    authoring = _mapping(raw.get("authoring", {}), "authoring", issues)
    materialize = _mapping(authoring.get("materialize", {}), "authoring.materialize", issues)
    for key, allowed in (
        ("voice_bindings", MATERIALIZE_VOICE_MODES),
        ("pause_defaults", MATERIALIZE_PAUSE_MODES),
    ):
        value = materialize.get(key, "when-needed" if key == "voice_bindings" else "when-enabled")
        if value not in allowed:
            issues.append(
                ConfigIssue(
                    "config.materialize_mode_invalid",
                    "error",
                    f"authoring.materialize.{key} must be one of {', '.join(allowed)}",
                    f"authoring.materialize.{key}",
                )
            )

    inventory = _mapping(raw.get("voice_inventory", {}), "voice_inventory", issues)
    for provider, voices in inventory.items():
        if not isinstance(provider, str) or not provider:
            issues.append(
                ConfigIssue(
                    "config.voice_provider_invalid",
                    "error",
                    "Provider names must be non-empty strings",
                )
            )
            continue
        for voice_id, entry in _mapping(voices, f"voice_inventory.{provider}", issues).items():
            if not isinstance(voice_id, str) or not voice_id:
                issues.append(
                    ConfigIssue(
                        "config.voice_id_invalid", "error", "Voice IDs must be non-empty strings"
                    )
                )
                continue
            values = _mapping(entry, f"voice_inventory.{provider}.{voice_id}", issues)
            gender = values.get("gender")
            if gender is not None and gender not in GENDERS:
                issues.append(
                    ConfigIssue(
                        "config.gender_invalid",
                        "error",
                        f"Invalid gender for {voice_id}",
                        f"voice_inventory.{provider}.{voice_id}.gender",
                    )
                )
            tags = values.get("tags", [])
            if not isinstance(tags, list) or any(
                not isinstance(tag, str) or not tag for tag in tags
            ):
                issues.append(
                    ConfigIssue(
                        "config.tags_invalid",
                        "error",
                        f"Tags for {voice_id} must be non-empty strings",
                        f"voice_inventory.{provider}.{voice_id}.tags",
                    )
                )
            elif len(tags) != len(set(tags)):
                issues.append(
                    ConfigIssue(
                        "config.tags_duplicate",
                        "error",
                        f"Tags for {voice_id} must be unique",
                        f"voice_inventory.{provider}.{voice_id}.tags",
                    )
                )
            if "enabled" in values and not isinstance(values["enabled"], bool):
                issues.append(
                    ConfigIssue(
                        "config.enabled_invalid",
                        "error",
                        f"enabled for {voice_id} must be boolean",
                        f"voice_inventory.{provider}.{voice_id}.enabled",
                    )
                )

    bindings = _mapping(raw.get("voice_bindings", {}), "voice_bindings", issues)
    for provider, provider_bindings in bindings.items():
        if not isinstance(provider, str) or not provider:
            issues.append(
                ConfigIssue(
                    "config.voice_provider_invalid",
                    "error",
                    "Binding providers must be non-empty strings",
                )
            )
            continue
        for reference, target in _mapping(
            provider_bindings, f"voice_bindings.{provider}", issues
        ).items():
            if (
                not isinstance(reference, str)
                or not reference
                or not isinstance(target, str)
                or not target
            ):
                issues.append(
                    ConfigIssue(
                        "config.binding_invalid",
                        "error",
                        "Binding references and targets must be non-empty strings",
                        f"voice_bindings.{provider}",
                    )
                )
                continue
            target_entry = _mapping(
                inventory.get(provider, {}), f"voice_inventory.{provider}", issues
            ).get(target)
            if target_entry is None:
                issues.append(
                    ConfigIssue(
                        "config.binding_target_unknown",
                        "warn",
                        f"Binding target is not in the inventory: {provider}/{target}",
                        f"voice_bindings.{provider}.{reference}",
                    )
                )
            elif isinstance(target_entry, Mapping) and target_entry.get("enabled", True) is False:
                issues.append(
                    ConfigIssue(
                        "config.binding_target_disabled",
                        "warn",
                        f"Binding target is disabled: {provider}/{target}",
                        f"voice_bindings.{provider}.{reference}",
                    )
                )

    pauses = _mapping(raw.get("pause_defaults", {}), "pause_defaults", issues)
    if "enabled" in pauses and not isinstance(pauses["enabled"], bool):
        issues.append(
            ConfigIssue(
                "config.pause_enabled_invalid",
                "error",
                "pause_defaults.enabled must be boolean",
                "pause_defaults.enabled",
            )
        )
    timing_keys = ("sentence", "paragraph", "voice_change")
    for key in timing_keys:
        if key in pauses:
            try:
                parse_duration(pauses[key])
            except (TypeError, ValueError) as exc:
                issues.append(
                    ConfigIssue(
                        "config.pause_duration_invalid", "error", str(exc), f"pause_defaults.{key}"
                    )
                )
    if pauses.get("enabled") is True and not any(
        pauses.get(key) is not None for key in timing_keys
    ):
        issues.append(
            ConfigIssue(
                "config.pause_defaults_missing_values",
                "error",
                "Enabled pause_defaults requires at least one timing value",
                "pause_defaults",
            )
        )
    if pauses.get("enabled") is False and any(pauses.get(key) is not None for key in timing_keys):
        issues.append(
            ConfigIssue(
                "config.pause_defaults_disabled_with_values",
                "warn",
                "Disabled pause_defaults contains timing values",
                "pause_defaults",
            )
        )
    return issues


def _proxy_nested(values: Mapping[str, Mapping[str, Any]]) -> MappingProxyType:
    return MappingProxyType({key: MappingProxyType(dict(value)) for key, value in values.items()})


def normalize_config(
    raw: Mapping[str, Any] | None = None, *, effective: bool = False
) -> SSMDUserConfig:
    """Normalize raw config into immutable public dataclasses."""
    source: dict[str, Any] = copy.deepcopy(dict(raw or {}))
    if effective:
        defaults = starter_config()
        defaults.update({key: value for key, value in source.items() if key not in defaults})
        for section in ("authoring", "voice_inventory", "voice_bindings", "pause_defaults"):
            if isinstance(source.get(section), Mapping):
                defaults[section] = {**defaults.get(section, {}), **source[section]}
        source = defaults

    authoring_raw = _as_mapping(source.get("authoring"))
    materialize_raw = _as_mapping(authoring_raw.get("materialize"))
    materialize = MaterializeConfig(
        voice_bindings=materialize_raw.get("voice_bindings", "when-needed"),
        pause_defaults=materialize_raw.get("pause_defaults", "when-enabled"),
    )
    authoring = AuthoringConfig(authoring_raw.get("default_voice_provider"), materialize)

    inventory: dict[str, dict[str, VoiceInventoryEntry]] = {}
    inventory_raw = _as_mapping(source.get("voice_inventory"))
    for provider, voices in inventory_raw.items():
        if not isinstance(voices, Mapping):
            continue
        inventory[provider] = {}
        for voice_id, values in voices.items():
            values = values if isinstance(values, Mapping) else {}
            inventory[provider][voice_id] = VoiceInventoryEntry(
                provider=provider,
                voice_id=voice_id,
                language=values.get("language"),
                gender=values.get("gender"),
                description=values.get("description"),
                tags=tuple(values.get("tags", ())),
                enabled=values.get("enabled", True),
            )

    binding_values: dict[str, dict[str, str]] = {}
    bindings_raw = _as_mapping(source.get("voice_bindings"))
    for provider, values in bindings_raw.items():
        if isinstance(values, Mapping):
            binding_values[provider] = dict(values)

    pauses_raw = _as_mapping(source.get("pause_defaults"))
    pauses = PauseDefaults(
        enabled=pauses_raw.get("enabled", False),
        sentence=parse_duration(pauses_raw["sentence"])
        if pauses_raw.get("sentence") is not None
        else None,
        paragraph=parse_duration(pauses_raw["paragraph"])
        if pauses_raw.get("paragraph") is not None
        else None,
        voice_change=parse_duration(pauses_raw["voice_change"])
        if pauses_raw.get("voice_change") is not None
        else None,
    )
    return SSMDUserConfig(
        schema=source.get("schema", CONFIG_SCHEMA),
        authoring=authoring,
        voice_inventory=_proxy_nested(inventory),
        voice_bindings=_proxy_nested(binding_values),
        pause_defaults=pauses,
    )


def load_config(path: str | Path, *, effective: bool = False) -> SSMDUserConfig:
    """Load and normalize a config file."""
    raw = load_raw_config(path)
    issues = validate_config(raw)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        raise ConfigError(errors[0].message, code=errors[0].code)
    return normalize_config(raw, effective=effective)


def atomic_save_config(path: str | Path, data: Mapping[str, Any]) -> None:
    """Write config atomically, preserving an existing file mode."""
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    mode = config_path.stat().st_mode if config_path.exists() else None
    content = yaml.safe_dump(
        dict(data), allow_unicode=True, default_flow_style=False, sort_keys=False
    )
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=config_path.parent, delete=False
        ) as handle:
            temporary_name = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temporary_name, mode)
        os.replace(temporary_name, config_path)
    except OSError as exc:
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
        raise ConfigError(f"Unable to write config: {exc}", code="config.write_failed") from exc


def dotted_get(data: Mapping[str, Any], key: str) -> Any:
    """Read a dotted key from a mapping."""
    value: Any = data
    for part in key.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise KeyError(key)
        value = value[part]
    return value


def dotted_set(data: dict[str, Any], key: str, value: Any) -> None:
    """Set a dotted key, creating intermediate mappings."""
    parts = key.split(".")
    if any(not part for part in parts):
        raise KeyError(key)
    target = data
    for part in parts[:-1]:
        current = target.get(part)
        if not isinstance(current, dict):
            current = {}
            target[part] = current
        target = current
    target[parts[-1]] = value


def dotted_unset(data: dict[str, Any], key: str) -> bool:
    """Remove a dotted key and prune empty parent mappings."""
    parts = key.split(".")

    def remove(target: dict[str, Any], index: int) -> bool:
        part = parts[index]
        if part not in target:
            return False
        if index == len(parts) - 1:
            del target[part]
        elif (
            isinstance(target[part], dict) and remove(target[part], index + 1) and not target[part]
        ):
            del target[part]
        return True

    return remove(data, 0)


__all__ = [
    "AuthoringConfig",
    "ConfigError",
    "ConfigIssue",
    "MaterializeConfig",
    "PauseDefaults",
    "SSMDUserConfig",
    "VoiceInventoryEntry",
    "atomic_save_config",
    "dotted_get",
    "dotted_set",
    "dotted_unset",
    "load_config",
    "load_raw_config",
    "normalize_config",
    "resolve_config_path",
    "starter_config",
    "validate_config",
]

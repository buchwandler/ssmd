"""Voice inventory, reference extraction, and binding resolution."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from ssmd.config import SSMDUserConfig, VoiceInventoryEntry
from ssmd.frontmatter import parse_front_matter
from ssmd.parser import parse_spans, parse_voice_blocks


@dataclass(frozen=True)
class VoiceReferenceUse:
    """A voice reference and its source locations."""

    reference: str
    count: int
    lines: tuple[int, ...]


@dataclass(frozen=True)
class VoiceResolution:
    """One resolved logical or direct voice reference."""

    provider: str
    reference: str
    resolved_voice: str
    source: Literal["cli", "header", "config", "direct"]


@dataclass(frozen=True)
class VoiceMaterializationPlan:
    """The bindings that create should add to a document header."""

    provider: str | None
    used_references: tuple[VoiceReferenceUse, ...]
    resolved: tuple[VoiceResolution, ...]
    unresolved: tuple[str, ...]
    header_bindings: Mapping[str, Mapping[str, str]]


def inventory_entries(
    config: SSMDUserConfig,
    *,
    provider: str | None = None,
    language: str | None = None,
    gender: str | None = None,
    tag: str | None = None,
    include_disabled: bool = False,
) -> list[VoiceInventoryEntry]:
    """Return deterministic inventory entries matching filters."""
    entries: list[VoiceInventoryEntry] = []
    providers = [provider] if provider is not None else sorted(config.voice_inventory)
    for provider_name in providers:
        for entry in config.voice_inventory.get(provider_name, {}).values():
            if not include_disabled and not entry.enabled:
                continue
            if language is not None and entry.language != language:
                continue
            if gender is not None and entry.gender != gender:
                continue
            if tag is not None and tag not in entry.tags:
                continue
            entries.append(entry)
    return sorted(entries, key=lambda item: (item.provider, item.voice_id))


def _line_for_position(text: str, position: int) -> int:
    return text.count("\n", 0, max(position, 0)) + 1


def extract_voice_references(text: str) -> tuple[VoiceReferenceUse, ...]:
    """Extract voice references using parser output, never a body regex."""
    front_matter = parse_front_matter(text)
    body = front_matter.body if front_matter.present else text
    positions: dict[str, list[int]] = defaultdict(list)

    cursor = 0
    for directive, block_text in parse_voice_blocks(body):
        if directive.voice and directive.voice.name:
            position = body.find(block_text, cursor)
            if position < 0:
                position = cursor
            positions[directive.voice.name].append(_line_for_position(body, position))
            cursor = max(cursor, position + len(block_text))

    # Inline annotations are exposed by parse_spans and retain their parsed attrs.
    spans = parse_spans(body, parse_yaml_header=False)
    for annotation in spans.annotations:
        if annotation.kind == "div":
            continue
        reference = annotation.attrs.get("voice")
        if reference:
            position = annotation.char_start
            positions[reference].append(_line_for_position(body, position))

    return tuple(
        VoiceReferenceUse(reference, len(lines), tuple(sorted(lines)))
        for reference, lines in sorted(positions.items())
    )


def _providers_for_reference(
    reference: str,
    config: SSMDUserConfig,
    *,
    provider: str | None,
    header_bindings: Mapping[str, Mapping[str, str]],
    cli_bindings: Mapping[str, Mapping[str, str]],
) -> list[str]:
    if provider is not None:
        return [provider]
    ordered: list[str] = []
    preferred = config.authoring.default_voice_provider
    if preferred:
        ordered.append(preferred)
    for values in (cli_bindings, header_bindings, config.voice_bindings):
        for candidate in values:
            if reference in values[candidate] and candidate not in ordered:
                ordered.append(candidate)
    for candidate, entries in config.voice_inventory.items():
        if reference in entries and candidate not in ordered:
            ordered.append(candidate)
    return ordered


def resolve_voice(
    reference: str,
    config: SSMDUserConfig,
    *,
    provider: str | None = None,
    header_bindings: Mapping[str, Mapping[str, str]] | None = None,
    cli_bindings: Mapping[str, Mapping[str, str]] | None = None,
) -> VoiceResolution | None:
    """Resolve a reference using CLI, header, config, then direct inventory."""
    header = header_bindings or {}
    cli = cli_bindings or {}
    candidates = _providers_for_reference(
        reference, config, provider=provider, header_bindings=header, cli_bindings=cli
    )
    for candidate in candidates:
        if reference in cli.get(candidate, {}):
            return VoiceResolution(candidate, reference, cli[candidate][reference], "cli")
        if reference in header.get(candidate, {}):
            return VoiceResolution(candidate, reference, header[candidate][reference], "header")
        if reference in config.voice_bindings.get(candidate, {}):
            return VoiceResolution(
                candidate, reference, config.voice_bindings[candidate][reference], "config"
            )
        entry = config.voice_inventory.get(candidate, {}).get(reference)
        if entry is not None and entry.enabled:
            return VoiceResolution(candidate, reference, reference, "direct")
    return None


def materialization_plan(
    text: str,
    config: SSMDUserConfig,
    *,
    provider: str | None = None,
    header_bindings: Mapping[str, Mapping[str, str]] | None = None,
    cli_bindings: Mapping[str, Mapping[str, str]] | None = None,
) -> VoiceMaterializationPlan:
    """Plan only the non-direct bindings required by references in *text*."""
    header = header_bindings or {}
    cli = cli_bindings or {}
    uses = extract_voice_references(text)
    selected_provider = provider or config.authoring.default_voice_provider
    if selected_provider is None:
        candidates = {
            candidate
            for use in uses
            for candidate in _providers_for_reference(
                use.reference,
                config,
                provider=None,
                header_bindings=header,
                cli_bindings=cli,
            )
        }
        if len(candidates) == 1:
            selected_provider = next(iter(candidates))

    resolved: list[VoiceResolution] = []
    unresolved: list[str] = []
    additions: dict[str, dict[str, str]] = defaultdict(dict)
    for use in uses:
        resolution = resolve_voice(
            use.reference,
            config,
            provider=selected_provider,
            header_bindings=header,
            cli_bindings=cli,
        )
        if resolution is None:
            unresolved.append(use.reference)
            continue
        resolved.append(resolution)
        if resolution.source not in {"direct", "header"}:
            additions[resolution.provider][resolution.reference] = resolution.resolved_voice

    if config.authoring.materialize.voice_bindings == "never":
        additions = defaultdict(dict)
    elif config.authoring.materialize.voice_bindings == "always":
        for provider_name, values in config.voice_bindings.items():
            additions[provider_name].update(values)

    header_values = {
        provider_name: dict(sorted(values.items()))
        for provider_name, values in sorted(additions.items())
        if values
    }
    return VoiceMaterializationPlan(
        selected_provider,
        uses,
        tuple(resolved),
        tuple(sorted(set(unresolved))),
        header_values,
    )


__all__ = [
    "VoiceMaterializationPlan",
    "VoiceReferenceUse",
    "VoiceResolution",
    "extract_voice_references",
    "inventory_entries",
    "materialization_plan",
    "resolve_voice",
]

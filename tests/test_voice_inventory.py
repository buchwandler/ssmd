"""Tests for voice inventory and parser-backed references."""

from ssmd.config import normalize_config
from ssmd.voices import extract_voice_references, inventory_entries, resolve_voice


def test_inventory_sorting_and_reference_resolution():
    config = normalize_config(
        {
            "authoring": {"default_voice_provider": "kokoro"},
            "voice_inventory": {
                "kokoro": {
                    "af_sarah": {"language": "en-US", "tags": ["warm"]},
                    "af_bella": {"language": "en-US", "enabled": False},
                }
            },
            "voice_bindings": {"kokoro": {"moderator": "af_sarah"}},
        }
    )
    assert [entry.voice_id for entry in inventory_entries(config)] == ["af_sarah"]
    assert resolve_voice("moderator", config).resolved_voice == "af_sarah"
    refs = extract_voice_references('<div voice="moderator">\nHello.\n</div>')
    assert refs[0].reference == "moderator"
    assert refs[0].count == 1

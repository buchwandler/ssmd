"""Utility functions for SSMD processing."""

import html
import re
from collections.abc import Callable
from typing import Any


def escape_xml(text: str) -> str:
    """Escape XML special characters.

    Args:
        text: Input text to escape

    Returns:
        Text with XML entities escaped
    """
    return html.escape(text, quote=True)


def unescape_xml(text: str) -> str:
    """Unescape XML entities.

    Args:
        text: Text with XML entities

    Returns:
        Unescaped text
    """
    return html.unescape(text)


def format_ssmd_attr(key: str, value: str) -> str:
    """Format a key/value pair for SSMD annotations."""
    raw_value = str(value)
    quote = "'" if '"' in raw_value and "'" not in raw_value else '"'
    escaped = raw_value.replace("\\", "\\\\")
    escaped = escaped.replace("{", "\\{").replace("}", "\\}")
    if quote == '"':
        escaped = escaped.replace('"', '\\"')
    else:
        escaped = escaped.replace("'", "\\'")
    return f"{key}={quote}{escaped}{quote}"


def format_xml(xml_text: str, pretty: bool = True) -> str:
    """Format XML with optional pretty printing.

    Args:
        xml_text: XML string to format
        pretty: Enable pretty printing

    Returns:
        Formatted XML string
    """
    if not pretty:
        return xml_text

    try:
        from xml.dom import minidom

        dom = minidom.parseString(xml_text)
        formatted = dom.toprettyxml(indent="  ", encoding=None)
        lines = [line for line in formatted.splitlines() if line.strip()]
        if lines and lines[0].startswith("<?xml"):
            lines = lines[1:]
        return "\n".join(lines)
    except Exception:
        # Fallback: return as-is if parsing fails
        return xml_text


def parse_yaml_header(text: str) -> tuple[dict[str, Any] | None, str]:
    """Compatibility wrapper around :func:`ssmd.frontmatter.parse_front_matter`."""
    from ssmd.frontmatter import parse_front_matter

    result = parse_front_matter(text)
    return (result.data if result.present else None), result.body


def _normalize_heading_levels(
    levels: list[Any],
) -> dict[int, list[tuple[str, str | dict[str, str]]]]:
    heading_levels: dict[int, list[tuple[str, str | dict[str, str]]]] = {}
    for entry in levels:
        if not isinstance(entry, dict):
            continue
        for level_key, config in entry.items():
            if not isinstance(level_key, str) or not level_key.startswith("level_"):
                continue
            try:
                level = int(level_key.split("_", 1)[1])
            except (IndexError, ValueError):
                continue
            if not isinstance(config, dict):
                continue

            effects: list[tuple[str, str | dict[str, str]]] = []
            if "pause_before" in config:
                effects.append(("pause_before", str(config["pause_before"])))
            if "emphasis" in config:
                effects.append(("emphasis", str(config["emphasis"])))
            if "pause" in config:
                effects.append(("pause", str(config["pause"])))

            prosody: dict[str, str] = {}
            for key in ("volume", "rate", "pitch"):
                if key in config:
                    prosody[key] = str(config[key])
            if prosody:
                effects.append(("prosody", prosody))

            if effects:
                heading_levels[level] = effects

    return heading_levels


def _normalize_extensions(
    entries: list[Any],
) -> dict[str, Callable[[str], str]]:
    extensions: dict[str, Callable[[str], str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for name, config in entry.items():
            if not name:
                continue
            if isinstance(config, dict):
                value = config.get("value")
            else:
                value = config
            if not isinstance(value, str):
                continue
            if "{text}" not in value:
                raise ValueError(f"Extension template for '{name}' must include '{{text}}'.")

            template = value

            def _handler(text: str, template: str = template) -> str:
                return template.replace("{text}", text)

            extensions[str(name)] = _handler

    return extensions


def build_config_from_header(header: dict[str, Any]) -> dict[str, Any]:
    config: dict[str, Any] = {}
    heading_entries = header.get("heading")
    if isinstance(heading_entries, list):
        heading_levels = _normalize_heading_levels(heading_entries)
        if heading_levels:
            config["heading_levels"] = heading_levels

    extension_entries = header.get("extensions")
    if isinstance(extension_entries, list):
        extensions = _normalize_extensions(extension_entries)
        if extensions:
            config["extensions"] = extensions

    return config


def extract_sentences(ssml: str) -> list[str]:
    """Extract sentences from SSML.

    Looks for <s> tags or falls back to <p> tags or <speak> content.

    Args:
        ssml: SSML string

    Returns:
        List of SSML sentence strings
    """

    def _local_name(tag: str) -> str:
        return tag.split("}")[-1]

    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(ssml)

        s_elements = [elem for elem in root.iter() if _local_name(elem.tag) == "s"]
        if s_elements:
            return [ET.tostring(elem, encoding="unicode") for elem in s_elements]

        p_elements = [elem for elem in root.iter() if _local_name(elem.tag) == "p"]
        if p_elements:
            return [ET.tostring(elem, encoding="unicode") for elem in p_elements]

        parts: list[str] = []
        if root.text:
            parts.append(root.text)
        for child in root:
            parts.append(ET.tostring(child, encoding="unicode"))
            if child.tail:
                parts.append(child.tail)
        clean = "".join(parts).strip()
        return [clean] if clean else []
    except Exception:
        # First try to extract <s> tags (fallback regex, including attributes)
        s_tag_pattern = re.compile(r"<s\b[^>]*>(.*?)</s>", re.DOTALL)
        sentences = s_tag_pattern.findall(ssml)

        if sentences:
            return sentences

        # Fallback: extract <p> tags
        p_tag_pattern = re.compile(r"<p\b[^>]*>(.*?)</p>", re.DOTALL)
        paragraphs = p_tag_pattern.findall(ssml)

        if paragraphs:
            return paragraphs

        # Last resort: remove <speak> wrapper and return as single sentence
        clean = re.sub(r"</?speak>", "", ssml).strip()
        return [clean] if clean else []


# Unicode private use area characters for placeholders
# Using \uf000+ range which is not transformed by phrasplit/spaCy
# (The \ue000-\ue00f range gets converted to dots/ellipses by some NLP tools)
_PLACEHOLDER_MAP = {
    "*": "\uf000",  # ASTERISK
    "_": "\uf001",  # UNDERSCORE
    "[": "\uf002",  # LEFT BRACKET
    "]": "\uf003",  # RIGHT BRACKET
    ".": "\uf004",  # DOT
    "@": "\uf005",  # AT SIGN
    "#": "\uf006",  # HASH
    "~": "\uf007",  # TILDE
    "+": "\uf008",  # PLUS
    "-": "\uf009",  # HYPHEN
    "<": "\uf00a",  # LESS THAN
    ">": "\uf00b",  # GREATER THAN
    "^": "\uf00c",  # CARET
}

# Reverse map for unescaping
_REVERSE_PLACEHOLDER_MAP = {v: k for k, v in _PLACEHOLDER_MAP.items()}


def escape_ssmd_syntax(
    text: str,
    patterns: list[str] | None = None,
) -> str:
    """Escape SSMD syntax patterns to prevent interpretation as markup.

    Note:
        Escaping is reversible but not length-preserving. Any offsets derived from
        escaped text should be mapped against the unescaped clean text instead.

    This is useful when processing plain text or markdown that may contain
    characters that coincidentally match SSMD syntax patterns. Uses placeholder
    replacement which is reversed after SSML processing.

    Args:
        text: Input text that may contain SSMD-like patterns
        patterns: List of pattern types to escape. If None, escapes all.
        Valid values: 'emphasis', 'prosody', 'annotations', 'breaks', 'marks',
            'headings', 'directives'

    Returns:
        Text with SSMD patterns replaced with placeholders

    Example:
        >>> text = "This *word* should not be emphasized"
        >>> escape_ssmd_syntax(text)
        'This \\uf000word\\uf000 should not be emphasized'

        >>> text = 'Visit [our site]{src="https://example.com"}'
        >>> escaped = escape_ssmd_syntax(text)
        >>> # Placeholders prevent SSMD interpretation

        >>> # Selective escaping
        >>> _ = escape_ssmd_syntax(text, patterns=['emphasis', 'breaks'])
    """
    if patterns is None:
        # Escape all patterns by default
        patterns = [
            "emphasis",
            "prosody",
            "annotations",
            "breaks",
            "marks",
            "headings",
            "directives",
        ]

    result = text

    # Process patterns in specific order (most specific first)
    # Replace special characters with placeholders

    if "directives" in patterns:
        # Directives at line start: <div ...>
        result = re.sub(
            r"^(\s*)<div\s+",
            lambda m: m.group(1) + _PLACEHOLDER_MAP["<"] + "div ",
            result,
            flags=re.MULTILINE,
        )
        result = re.sub(
            r"^(\s*)</div>",
            lambda m: m.group(1) + _PLACEHOLDER_MAP["<"] + "/div>",
            result,
            flags=re.MULTILINE,
        )

    if "headings" in patterns:
        # Headings at line start: #, ##, ###
        result = re.sub(
            r"^(#{1,6})(\s)",
            lambda m: _PLACEHOLDER_MAP["#"] * len(m.group(1)) + m.group(2),
            result,
            flags=re.MULTILINE,
        )

    if "prosody" in patterns:
        # Escape doubled forms before their single-delimiter counterparts.
        prosody_patterns = (
            (r"(?<!\+)\+\+([^+\n]+?)\+\+(?!\+)", "+", 2),
            (r"(?<!>)>>([^>\n]+?)>>(?!>)", ">", 2),
            (r"(?<!\^)\^\^([^\^\n]+?)\^\^(?!\^)", "^", 2),
            (r"(?<!-)--([^-\n]+?)--(?!-)", "-", 2),
            (r"(?<!<)<<([^<\n]+?)<<(?!<)", "<", 2),
            (r"(?<!_)__([^_\n]+?)__(?!_)", "_", 2),
            (r"(?<!~)~([^~\n]+?)~(?!~)", "~", 1),
            (r"(?<![\w-])-([^-\n]+?)-(?![\w-])", "-", 1),
            (r"(?<!\+)\+([^+\n]+?)\+(?!\+)", "+", 1),
            (r"(?<!<)<([^<\n]+?)<(?!<)", "<", 1),
            (r"(?<!>)>([^>\n]+?)>(?!>)", ">", 1),
            (r"(?<!\^)\^([^\^\n]+?)\^(?!\^)", "^", 1),
        )
        for pattern, delimiter, count in prosody_patterns:

            def replace_prosody(
                match: re.Match[str],
                delimiter: str = delimiter,
                count: int = count,
            ) -> str:
                placeholder = _PLACEHOLDER_MAP[delimiter] * count
                return placeholder + match.group(1) + placeholder

            result = re.sub(pattern, replace_prosody, result)

    if "emphasis" in patterns:
        # Strong emphasis: **text**
        result = re.sub(
            r"\*\*([^*]+)\*\*",
            lambda m: _PLACEHOLDER_MAP["*"] * 2 + m.group(1) + _PLACEHOLDER_MAP["*"] * 2,
            result,
        )
        # Moderate emphasis: *text*
        result = re.sub(
            r"\*([^*\n]+)\*",
            lambda m: _PLACEHOLDER_MAP["*"] + m.group(1) + _PLACEHOLDER_MAP["*"],
            result,
        )
        # Reduced emphasis/pitch: _text_ (but not in middle of words)
        result = re.sub(
            r"(?<!\w)_([^_\n]+)_(?!\w)",
            lambda m: _PLACEHOLDER_MAP["_"] + m.group(1) + _PLACEHOLDER_MAP["_"],
            result,
        )

    if "annotations" in patterns:
        # Annotations: [text]{params} - replace the brackets
        result = re.sub(
            r"\[([^\]]+)\]\{([^}]+)\}",
            lambda m: (
                _PLACEHOLDER_MAP["["] + m.group(1) + _PLACEHOLDER_MAP["]"] + "{" + m.group(2) + "}"
            ),
            result,
        )

    if "breaks" in patterns:
        # Breaks: ...n, ...w, ...c, ...s, ...p, ...500ms, ...5s
        result = re.sub(
            r"\.\.\.((?:[nwcsp]|\d+(?:ms|s)))(?=\s|$|[.!?,;:])",
            lambda m: _PLACEHOLDER_MAP["."] * 3 + m.group(1),
            result,
        )

    if "marks" in patterns:
        # Marks: @word
        # Require whitespace boundaries to avoid matching handles or emails
        result = re.sub(
            r"(?<!\S)@(\w+)(?=\s|$)",
            lambda m: _PLACEHOLDER_MAP["@"] + m.group(1),
            result,
        )

    return result


def unescape_ssmd_syntax(text: str, *, xml_safe: bool = False) -> str:
    """Remove placeholder escaping from SSMD syntax.

    This is used internally to replace placeholders with original characters
    after TTS processing.

    Args:
        text: Text with placeholder-escaped SSMD syntax
        xml_safe: If True, keep XML special characters escaped when restoring
            placeholders (e.g., ``<`` becomes ``&lt;``).

    Returns:
        Text with placeholders replaced by original characters

    Example:
        >>> unescape_ssmd_syntax("This \\uf000word\\uf000 is escaped")
        'This *word* is escaped'
    """
    replacements = dict(_REVERSE_PLACEHOLDER_MAP)
    if xml_safe:
        replacements[_PLACEHOLDER_MAP["<"]] = "&lt;"
        replacements[_PLACEHOLDER_MAP[">"]] = "&gt;"

    result = text
    # Replace all placeholders with their original characters
    for placeholder, original in replacements.items():
        result = result.replace(placeholder, original)
    return result

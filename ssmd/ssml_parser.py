"""SSML to SSMD converter - reverse conversion."""

import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any

from ssmd.formatter import format_ssmd
from ssmd.parser import parse_sentences
from ssmd.ssml_conversions import SSML_BREAK_STRENGTH_MAP
from ssmd.utils import (
    _PLACEHOLDER_MAP,
    escape_ssmd_syntax,
    format_ssmd_attr,
    unescape_ssmd_syntax,
)

if TYPE_CHECKING:
    from ssmd.capabilities import TTSCapabilities


class SSMLParser:
    """Convert SSML to SSMD markdown format.

    This class provides the reverse conversion from SSML XML to the more
    human-readable SSMD markdown syntax. Literal text in the SSML is
    placeholder-escaped before reparsing so characters that look like SSMD
    markup (``*``, ``[...]``, ``@``, ``...2s``) survive verbatim.

    Reverse conversion is best-effort: unknown vendor-specific tags are
    flattened to their children (their semantics are dropped), and inline
    annotations whose content itself contains ``[...]`` markup may be lossy.
    Prefer directive (``<div>``) blocks for nested content.

    Example:
        >>> parser = SSMLParser()
        >>> ssml = '<speak><emphasis>Hello</emphasis> world</speak>'
        >>> ssmd = parser.to_ssmd(ssml)
        >>> print(ssmd)
        '*Hello* world'
    """

    # Standard locales that can be simplified (locale -> language code)
    STANDARD_LOCALES = {
        "en-US": "en",
        "en-GB": "en-GB",  # Keep non-US English locales
        "de-DE": "de",
        "fr-FR": "fr",
        "es-ES": "es",
        "it-IT": "it",
        "pt-PT": "pt",
        "ru-RU": "ru",
        "zh-CN": "zh",
        "ja-JP": "ja",
        "ko-KR": "ko",
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize SSML parser.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

    def _format_attr(self, key: str, value: str) -> str:
        return format_ssmd_attr(key, value)

    def _format_attrs(self, pairs: list[tuple[str, str]]) -> str:
        return " ".join(self._format_attr(key, value) for key, value in pairs)

    def _wrap_directive(self, content: str, attrs: str) -> str:
        content = content.strip()
        return f"<div {attrs}>{{DIRECTIVE_NEWLINE}}{content}{{DIRECTIVE_NEWLINE}}</div>"

    def _element_namespace(self, element: ET.Element) -> str | None:
        if element.tag.startswith("{"):
            return element.tag.split("}")[0][1:]
        return None

    def _local_tag(self, element: ET.Element) -> str:
        """Return an element's local tag name, ignoring any XML namespace."""
        return element.tag.split("}")[-1]

    def _find_child(self, element: ET.Element, name: str) -> ET.Element | None:
        """Find the first child whose local tag matches ``name``.

        Resolves tags namespace-agnostically so vendor SSML that declares the
        SSML namespace (e.g. ``<ssml:desc>``) is still matched.
        """
        for child in element:
            if self._local_tag(child) == name:
                return child
        return None

    def _escape_text(self, text: str) -> str:
        """Escape literal SSML text so it is not reparsed as SSMD markup.

        ``escape_ssmd_syntax`` protects complete SSMD patterns (emphasis
        pairs, annotations, marks, breaks, headings, directives). Isolated
        brackets are additionally placeholder-escaped so a literal ``]`` cannot
        terminate an enclosing annotation when this text becomes annotation
        content. Placeholders are restored by ``unescape_ssmd_syntax`` at the
        end of ``to_ssmd``.
        """
        text = escape_ssmd_syntax(text)
        return text.replace("[", _PLACEHOLDER_MAP["["]).replace(
            "]", _PLACEHOLDER_MAP["]"]
        )

    def _annotation(self, content: str, attrs: str) -> str:
        """Wrap ``content``/``attrs`` as an inline or block annotation.

        Inline form ``[content]{attrs}`` is used when the content is short,
        single-line, and free of ``[``/``]`` (literal or placeholder-escaped),
        because SSMD inline annotation content cannot represent a literal
        ``]`` or nested ``[...]`` markup.

        Block (multi-line/long) content uses the directive (``<div>``) form,
        whose content is not bracket-delimited. Short content that still
        contains a bracket degrades to the escaped text (the annotation
        semantics are dropped) so the bracket survives without corrupting
        surrounding SSMD.
        """
        stripped = content.strip()
        is_block = "\n" in stripped or len(stripped) > 80
        has_bracket = (
            "[" in stripped
            or "]" in stripped
            or _PLACEHOLDER_MAP["["] in stripped
            or _PLACEHOLDER_MAP["]"] in stripped
        )
        if is_block:
            return self._wrap_directive(content, attrs)
        if has_bracket:
            return content
        return f"[{content}]{{{attrs}}}"

    def to_ssmd(
        self, ssml: str, *, capabilities: "TTSCapabilities | str | None" = None
    ) -> str:
        """Convert SSML to SSMD format.

        Args:
            ssml: SSML XML string
            capabilities: Optional TTS capabilities (preset name or object)

        Returns:
            SSMD markdown string with proper formatting (each sentence on new line)

        Example:
            >>> parser = SSMLParser()
            >>> parser.to_ssmd('<speak><emphasis>Hello</emphasis></speak>')
            '*Hello*'
        """
        # Parse the input first; only wrap in <speak> if it is not already a
        # single root element. Parsing first (rather than a naive
        # startswith('<speak') check) handles XML declarations and processing
        # instructions that are already well-formed.
        try:
            root = ET.fromstring(ssml)
        except ET.ParseError:
            # Bare text and fragments without a root element are wrapped as a
            # convenience.
            try:
                root = ET.fromstring(f"<speak>{ssml}</speak>")
            except ET.ParseError as e:
                raise ValueError(f"Invalid SSML XML: {e}") from e

        # Process the root element
        result = self._process_element(root)

        # Clean up whitespace
        result = self._clean_whitespace(result)

        # Restore directive and sentence newlines (protected during whitespace cleaning)
        result = (
            result.replace("{DIRECTIVE_NEWLINE}", "\n")
            .replace("{SENTENCE_NEWLINE}", "\n")
            .strip()
        )

        # Parse into sentences and format with proper line breaks
        sentences = parse_sentences(
            result.strip(),
            capabilities=capabilities,
            strict_parse=capabilities is not None,
        )
        formatted = format_ssmd(sentences)
        # Restore placeholder-escaped literal characters that were protected
        # above from being reparsed as SSMD markup.
        return unescape_ssmd_syntax(formatted)

    def _process_element(self, element: ET.Element) -> str:
        """Process an XML element and its children recursively.

        Args:
            element: XML element to process

        Returns:
            SSMD formatted string
        """
        tag = element.tag.split("}")[-1]  # Remove namespace if present
        namespace = self._element_namespace(element)

        # Handle different SSML tags
        if tag == "speak":
            return self._process_children(element)
        elif tag == "p":
            content = self._process_children(element)
            # Paragraphs are separated by double newlines
            return f"{content}\n\n"
        elif tag == "s":
            # Sentences - preserve explicit line breaks
            return f"{self._process_children(element)}{{SENTENCE_NEWLINE}}"
        elif tag == "emphasis":
            return self._process_emphasis(element)
        elif tag == "break":
            return self._process_break(element)
        elif tag == "prosody":
            return self._process_prosody(element)
        elif tag == "lang":
            return self._process_language(element)
        elif tag == "voice":
            return self._process_voice(element)
        elif tag == "phoneme":
            return self._process_phoneme(element)
        elif tag == "sub":
            return self._process_substitution(element)
        elif tag == "say-as":
            return self._process_say_as(element)
        elif tag == "audio":
            return self._process_audio(element)
        elif tag == "mark":
            return self._process_mark(element)
        elif tag == "effect" and namespace == "https://amazon.com/ssml":
            return self._process_amazon_effect(element)
        else:
            # Unknown/vendor-specific tag: drop the tag's semantics and keep
            # only its children. This is intentional flattening (see above).
            return self._process_children(element)

    def _process_children(self, element: ET.Element) -> str:
        """Process all children of an element.

        Args:
            element: Parent element

        Returns:
            Combined SSMD string from all children
        """
        result = []

        # Add text before first child
        if element.text:
            result.append(self._escape_text(element.text))

        # Process each child
        for child in element:
            result.append(self._process_element(child))
            # Add text after child
            if child.tail:
                result.append(self._escape_text(child.tail))

        result_text = "".join(result)
        return re.sub(r"\s+\n\n\s+", "\n\n", result_text)

    def _process_emphasis(self, element: ET.Element) -> str:
        """Convert <emphasis> to *text*, **text**, or _text_.

        Args:
            element: emphasis element

        Returns:
            SSMD emphasis syntax
        """
        content = self._process_children(element)
        level = element.get("level", "moderate")

        if level in ("strong", "x-strong"):
            return f"**{content}**"
        elif level == "reduced":
            return f"_{content}_"
        elif level == "none":
            # Level "none" is rare - use explicit annotation
            return self._annotation(content, self._format_attr("emphasis", "none"))
        else:  # moderate or default
            return f"*{content}*"

    def _process_break(self, element: ET.Element) -> str:
        """Convert <break> to ... notation.

        Args:
            element: break element

        Returns:
            SSMD break syntax with spaces
        """
        time = element.get("time")
        strength = element.get("strength")

        if time:
            # Parse time value (e.g., "500ms", "2s")
            match = re.match(r"(\d+(?:\.\d+)?)(ms|s)", time)
            if match:
                # Breaks have spaces before and after per SSMD spec
                return f" ...{time} "
            # Fallback to 1s if time format is invalid
            return " ...1s "

        elif strength:
            marker = SSML_BREAK_STRENGTH_MAP.get(strength, "...s")
            return f" {marker} "

        # Default to sentence break
        return " ...s "

    def _process_prosody(self, element: ET.Element) -> str:
        """Convert <prosody> to directive or inline annotation.

        Args:
            element: prosody element

        Returns:
            SSMD prosody syntax
        """
        content = self._process_children(element)
        volume = element.get("volume")
        rate = element.get("rate")
        pitch = element.get("pitch")

        # Filter out "medium" default values (ssml-maker adds these)
        if volume == "medium":
            volume = None
        if rate == "medium":
            rate = None
        if pitch == "medium":
            pitch = None

        if not any([volume, rate, pitch]):
            return content

        pairs: list[tuple[str, str]] = []

        if volume:
            pairs.append(("volume", volume))

        if rate:
            pairs.append(("rate", rate))

        if pitch:
            pairs.append(("pitch", pitch))

        if not pairs:
            return content

        attrs = self._format_attrs(pairs)
        return self._annotation(content, attrs)

    def _process_language(self, element: ET.Element) -> str:
        """Convert <lang> to directive or inline annotation.

        Args:
            element: lang element

        Returns:
            SSMD language syntax
        """
        content = self._process_children(element)
        lang = element.get("{http://www.w3.org/XML/1998/namespace}lang") or element.get(
            "lang"
        )

        if not lang:
            return content

        simplified = self.STANDARD_LOCALES.get(lang, lang)
        lang_attr = self._format_attr("lang", simplified)
        return self._annotation(content, lang_attr)

    def _process_voice(self, element: ET.Element) -> str:
        """Convert <voice> to directive or annotation syntax.

        Uses directive syntax (<div ...>) for multi-line content,
        and annotation syntax ([text]{voice="name"}) for single-line content.

        Args:
            element: voice element

        Returns:
            SSMD voice syntax
        """
        content = self._process_children(element)

        # Get voice attributes
        name = element.get("name")
        language = element.get("language")
        gender = element.get("gender")
        variant = element.get("variant")

        # Build voice attributes. Directive form is selected automatically by
        # _annotation when the content is multi-line or contains brackets.
        parts = []
        if name:
            parts.append(self._format_attr("voice", name))
        if language:
            parts.append(self._format_attr("voice-lang", language))
        if gender:
            parts.append(self._format_attr("gender", gender))
        if variant:
            parts.append(self._format_attr("variant", variant))

        if not parts:
            return content
        attrs = " ".join(parts)
        return self._annotation(content, attrs)

    def _process_phoneme(self, element: ET.Element) -> str:
        """Convert <phoneme> to [text]{ph="..." alphabet="..."}.

        Args:
            element: phoneme element

        Returns:
            SSMD phoneme syntax
        """
        content = self._process_children(element)
        alphabet = element.get("alphabet", "ipa")
        ph = element.get("ph", "")

        # Use explicit format: [text]{ph="value" alphabet="type"}
        attrs = self._format_attrs([("ph", ph), ("alphabet", alphabet)])
        return self._annotation(content, attrs)

    def _process_substitution(self, element: ET.Element) -> str:
        """Convert <sub> to [text]{sub="alias"}.

        Args:
            element: sub element

        Returns:
            SSMD substitution syntax
        """
        content = self._process_children(element)
        alias = element.get("alias", "")

        if alias:
            return self._annotation(content, self._format_attr("sub", alias))

        return content

    def _process_say_as(self, element: ET.Element) -> str:
        """Convert <say-as> to [text]{as="type"}.

        Args:
            element: say-as element

        Returns:
            SSMD say-as syntax
        """
        content = self._process_children(element)
        interpret_as = element.get("interpret-as", "")
        format_attr = element.get("format")
        detail_attr = element.get("detail")

        # Build annotation string
        parts = [self._format_attr("as", interpret_as)]

        if format_attr:
            parts.append(self._format_attr("format", format_attr))
        if detail_attr:
            parts.append(self._format_attr("detail", detail_attr))

        annotation = " ".join(parts)

        if interpret_as:
            return self._annotation(content, annotation)

        return content

    def _process_audio(self, element: ET.Element) -> str:
        """Convert <audio> to [desc]{src="url" ...}.

        The ``<desc>`` child is resolved namespace-agnostically. Single-sided
        clips (``clipBegin`` only or ``clipEnd`` only) are preserved, and
        fallback content is processed recursively so nested markup survives.

        Args:
            element: audio element

        Returns:
            SSMD audio syntax with attributes
        """
        src = element.get("src", "")

        # Get advanced attributes
        clip_begin = element.get("clipBegin")
        clip_end = element.get("clipEnd")
        speed = element.get("speed")
        repeat_count = element.get("repeatCount")
        repeat_dur = element.get("repeatDur")
        sound_level = element.get("soundLevel")

        # Description from <desc> (resolved namespace-agnostically).
        desc_elem = self._find_child(element, "desc")
        description = ""
        has_desc_tag = False
        if desc_elem is not None:
            has_desc_tag = True
            description = self._process_children(desc_elem).strip()

        # Fallback content (rendered if the audio source is unavailable).
        # Process child elements recursively so nested markup survives instead
        # of only concatenating raw tails.
        fallback_parts: list[str] = []
        if element.text:
            fallback_parts.append(self._escape_text(element.text))
        for child in element:
            if child is desc_elem:
                if child.tail:
                    fallback_parts.append(self._escape_text(child.tail))
                continue
            fallback_parts.append(self._process_element(child))
            if child.tail:
                fallback_parts.append(self._escape_text(child.tail))
        fallback = re.sub(r"\s+", " ", "".join(fallback_parts)).strip()

        # If there's no <desc> tag but there is fallback content,
        # treat the fallback as description
        if not has_desc_tag and fallback:
            description = fallback

        if not src:
            return description if description else fallback

        pairs = [("src", src)]

        if clip_begin or clip_end:
            pairs.append(("clip", f"{clip_begin or ''}-{clip_end or ''}"))
        if speed:
            pairs.append(("speed", speed))
        if repeat_count:
            pairs.append(("repeat", repeat_count))
        if repeat_dur:
            pairs.append(("repeatDur", repeat_dur))
        if sound_level:
            pairs.append(("level", sound_level))
        if has_desc_tag and fallback:
            pairs.append(("alt", fallback))

        annotation = self._format_attrs([(key, str(value)) for key, value in pairs])

        if description:
            return self._annotation(description, annotation)
        return f"[]{{{annotation}}}"

    def _process_mark(self, element: ET.Element) -> str:
        """Convert <mark> to @name.

        Args:
            element: mark element

        Returns:
            SSMD mark syntax with spaces
        """
        name = element.get("name", "")

        if name:
            # Marks have space before and after
            return f" @{name} "

        return ""

    def _process_amazon_effect(self, element: ET.Element) -> str:
        """Convert Amazon effects to [text]{ext="name"}.

        Args:
            element: amazon:effect element

        Returns:
            SSMD extension syntax
        """
        content = self._process_children(element)
        name = element.get("name", "")

        # Map Amazon effect names to SSMD extensions
        effect_map = {
            "whispered": "whisper",
            "drc": "drc",
        }

        ext_name = effect_map.get(name, name)

        if ext_name:
            return self._annotation(content, self._format_attr("ext", ext_name))

        return content

    def _clean_whitespace(self, text: str) -> str:
        """Clean up excessive whitespace while preserving paragraph breaks.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        # Preserve paragraph breaks (double newlines). Normalization is
        # narrowed: runs of spaces/tabs are collapsed and whitespace around
        # newlines is trimmed, but single newlines are preserved so literal
        # line breaks and directive content are not flattened to one space.
        text = text.strip("\n")
        parts = re.split(r"\n\n+", text)

        cleaned_parts = []
        for part in parts:
            part = re.sub(r"[ \t]+", " ", part)
            part = re.sub(r" *\n *", "\n", part)
            part = re.sub(r"\n{3,}", "\n\n", part)
            cleaned = part.strip()
            if cleaned:
                cleaned_parts.append(cleaned)

        # Join with double newlines for paragraphs
        return "\n\n".join(cleaned_parts)

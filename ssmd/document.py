"""SSMD Document - Main document container with rich TTS features."""

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, overload

from ssmd.config import PauseDefaults
from ssmd.formatter import format_ssmd
from ssmd.frontmatter import parse_front_matter, serialize_front_matter
from ssmd.paragraph import Paragraph
from ssmd.parser import parse_paragraphs, parse_sentences
from ssmd.types import ParsedResult, SentenceDetectionConfig, SentenceDetectionDiagnostics
from ssmd.utils import build_config_from_header, format_xml

if TYPE_CHECKING:
    from ssmd.capabilities import TTSCapabilities
    from ssmd.sentence import Sentence


class Document:
    """Main SSMD document container with incremental building and editing.

    This is the primary interface for working with SSMD documents. It provides
    a clean, document-centric API for creating, editing, and exporting TTS content.

    The Document stores content as fragments (pieces of text) with separators
    between them, allowing efficient incremental building and editing while
    preserving the document structure.

    Example:
        Basic usage::

            import ssmd

            # Create and build a document
            doc = ssmd.Document()
            doc.add_sentence("Hello world!")
            doc.add_sentence("This is SSMD.")

            # Export to different formats
            ssml = doc.to_ssml()
            text = doc.to_text()

            # Iterate for streaming TTS
            for sentence in doc.sentences():
                tts_engine.speak(sentence)

        Advanced usage::

            # Load from SSML
            doc = ssmd.Document.from_ssml("<speak>Hello</speak>")

            # Edit the document
            doc[0] = "Modified content"
            doc.add_paragraph("New paragraph")

            # Access raw content
            print(doc.ssmd)  # Raw SSMD markdown
    """

    def __init__(
        self,
        content: str = "",
        config: dict[str, Any] | None = None,
        capabilities: "TTSCapabilities | str | None" = None,
        escape_syntax: bool = False,
        escape_patterns: list[str] | None = None,
        parse_yaml_header: bool = True,
        strict: bool = False,
    ) -> None:
        """Initialize a new SSMD document.

        Args:
            content: Optional initial SSMD content
            config: Configuration dictionary with options:
                - skip (list): Processor names to skip
                - output_speak_tag (bool): Wrap in <speak> tags (default: True)
                - pretty_print (bool): Format XML output (default: False)
                - auto_sentence_tags (bool): Auto-wrap sentences (default: False)
                - heading_levels (dict): Custom heading configurations
                - extensions (dict): Registered extension handlers
                - namespaces (dict): XML namespaces to add to the <speak> tag
                - sentence_model_size (str): Exact spaCy model tier for sentence
                  detection ("sm", "md", "lg", "trf"). Unset selects automatically.
                - sentence_spacy_model (str): Exact package name, which takes
                  precedence over sentence_model_size
                - sentence_use_spacy (bool): If False, use fast regex splitting
                  instead of spaCy. Default: True
            capabilities: TTS capabilities (TTSCapabilities instance or
                preset name). Presets: 'espeak', 'pyttsx3', 'google',
                'polly', 'azure', 'minimal', 'full'
            escape_syntax: If True, escape SSMD-like syntax in content to
                prevent interpretation as markup. Useful for plain text or
                markdown that may coincidentally contain SSMD patterns.
            escape_patterns: List of specific pattern types to escape when
                escape_syntax=True. If None, escapes all patterns.
                Valid values: 'emphasis', 'annotations', 'breaks', 'marks',
                'headings', 'directives'
            parse_yaml_header: If True (the default), parse YAML front matter
                and store it on doc.header while stripping it from the SSMD
                body. If False, YAML front matter is preserved as content.
            strict: If True, emit warnings and apply ssml-green validation
                rules where possible.

        Example:
            >>> doc = ssmd.Document("Hello *world*!")
            >>> doc = ssmd.Document(capabilities='pyttsx3')
            >>> doc = ssmd.Document("Text", config={'auto_sentence_tags': True})
            >>> # Fast sentence detection (no spaCy required)
            >>> doc = ssmd.Document(config={'sentence_use_spacy': False})
            >>> # High quality sentence detection
            >>> doc = ssmd.Document(config={'sentence_model_size': 'lg'})
            >>> # Escape SSMD syntax for plain text/markdown
            >>> doc = ssmd.Document("*literal*", escape_syntax=True)
            >>> # Selective escaping
            >>> doc = ssmd.Document(
            ...     "*literal*",
            ...     escape_syntax=True,
            ...     escape_patterns=['emphasis', 'annotations']
            ... )
        """
        self._fragments: list[str] = []
        self._separators: list[str] = []
        self._config = config or {}
        self._capabilities = capabilities
        self._capabilities_obj: TTSCapabilities | None = None  # Resolved capabilities
        self._cached_ssml: str | None = None
        self._cached_sentences: list[str] | None = None
        self._cached_paragraphs: list[Paragraph] | None = None
        self._escape_syntax = escape_syntax
        self._escape_patterns = escape_patterns
        self._strict = strict
        self._parse_yaml_header = parse_yaml_header
        self.header: dict[str, Any] | None = None
        self.warnings: list[str] = []
        self.sentence_detection_diagnostics: SentenceDetectionDiagnostics | None = None

        # Add initial content if provided
        if content:
            header_config: dict[str, Any] = {}
            if parse_yaml_header:
                front_matter = parse_front_matter(content)
                if front_matter.present:
                    self.header = front_matter.data
                    header_config = build_config_from_header(front_matter.data)
                    content = front_matter.body
                content = content.lstrip("\n")
            if escape_syntax:
                from ssmd.utils import escape_ssmd_syntax

                content = escape_ssmd_syntax(content, patterns=escape_patterns)
            self._config.update(header_config)
            self._fragments.append(content)

    @classmethod
    def from_ssml(
        cls,
        ssml: str,
        config: dict[str, Any] | None = None,
        capabilities: "TTSCapabilities | str | None" = None,
    ) -> "Document":
        """Create a Document from SSML string.

        Args:
            ssml: SSML XML string
            config: Optional configuration parameters
            capabilities: Optional TTS capabilities

        Returns:
            New Document instance with converted content

        Example:
            >>> ssml = '<speak><emphasis>Hello</emphasis> world</speak>'
            >>> doc = ssmd.Document.from_ssml(ssml)
            >>> doc.ssmd
            '*Hello* world\\n'
        """
        from ssmd.ssml_parser import SSMLParser

        parser = SSMLParser(config or {})
        ssmd_content = parser.to_ssmd(ssml, capabilities=capabilities)
        return cls(ssmd_content, config, capabilities, parse_yaml_header=False)

    @classmethod
    def from_text(
        cls,
        text: str,
        config: dict[str, Any] | None = None,
        capabilities: "TTSCapabilities | str | None" = None,
        parse_yaml_header: bool = True,
        strict: bool = False,
    ) -> "Document":
        """Create a Document from plain text.

        This is essentially the same as Document(text), but provides
        a symmetric API with from_ssml().

        Args:
            text: Plain text or SSMD content
            config: Optional configuration parameters
            capabilities: Optional TTS capabilities

        Returns:
            New Document instance

        Example:
            >>> doc = ssmd.Document.from_text("Hello world")
            >>> doc.ssmd
            'Hello world'
        """
        return cls(
            text,
            config,
            capabilities,
            parse_yaml_header=parse_yaml_header,
            strict=strict,
        )

    # ═══════════════════════════════════════════════════════════
    # BUILDING METHODS
    # ═══════════════════════════════════════════════════════════

    def add(self, text: str) -> "Document":
        """Append text without separator.

        Use this when you want to append content immediately after
        the previous content with no spacing.

        Args:
            text: SSMD text to append

        Returns:
            Self for method chaining

        Example:
            >>> doc = ssmd.Document("Hello")
            >>> _ = doc.add(" world")
            >>> doc.ssmd
            'Hello world'
        """
        if not text:
            return self

        self._invalidate_cache()

        if not self._fragments:
            self._fragments.append(text)
        else:
            self._separators.append("")
            self._fragments.append(text)

        return self

    def add_sentence(self, text: str) -> "Document":
        """Append text with newline separator.

        Use this to add a new sentence on a new line.

        Args:
            text: SSMD text to append

        Returns:
            Self for method chaining

        Example:
            >>> doc = ssmd.Document("First sentence.")
            >>> _ = doc.add_sentence("Second sentence.")
            >>> doc.ssmd
            'First sentence.\\nSecond sentence.'
        """
        if not text:
            return self

        self._invalidate_cache()

        if not self._fragments:
            self._fragments.append(text)
        else:
            self._separators.append("\n")
            self._fragments.append(text)

        return self

    def add_paragraph(self, text: str) -> "Document":
        """Append text with double newline separator.

        Use this to start a new paragraph.

        Args:
            text: SSMD text to append

        Returns:
            Self for method chaining

        Example:
            >>> doc = ssmd.Document("First paragraph.")
            >>> _ = doc.add_paragraph("Second paragraph.")
            >>> doc.ssmd
            'First paragraph.\\n\\nSecond paragraph.'
        """
        if not text:
            return self

        self._invalidate_cache()

        if not self._fragments:
            self._fragments.append(text)
        else:
            self._separators.append("\n\n")
            self._fragments.append(text)

        return self

    # ═══════════════════════════════════════════════════════════
    # EXPORT METHODS
    # ═══════════════════════════════════════════════════════════

    def to_ssml(self) -> str:
        """Export document to SSML format.

        Returns:
            SSML XML string

        Example:
            >>> doc = ssmd.Document("Hello *world*!")
            >>> doc.to_ssml()
            '<speak><p>Hello <emphasis>world</emphasis>!</p></speak>'
        """
        if self._cached_ssml is None:
            ssmd_content = self.ssmd

            # Get resolved capabilities
            capabilities = self._get_capabilities()

            # Get config options
            output_speak_tag = self._config.get("output_speak_tag", True)
            auto_sentence_tags = self._config.get("auto_sentence_tags", False)
            pretty_print = self._config.get("pretty_print", False)
            extensions = self._config.get("extensions")
            heading_levels = self._config.get("heading_levels")

            sentence_config = self._sentence_detection_config()

            # Parse SSMD into sentences (with placeholders if escape_syntax=True)
            sentences = parse_sentences(
                ssmd_content,
                capabilities=capabilities,
                model_size=sentence_config.model_size,
                spacy_model=sentence_config.spacy_model,
                use_spacy=sentence_config.use_spacy,
                heading_levels=heading_levels,
                extensions=extensions,
            )
            self.sentence_detection_diagnostics = sentences.diagnostics

            namespaces = self._collect_namespaces(sentences, extensions, capabilities)

            # Build SSML from sentences
            ssml_parts: list[str] = []
            paragraph_parts: list[str] = []
            paragraph_enabled = not capabilities or capabilities.paragraph

            def flush_paragraph() -> None:
                if not paragraph_parts:
                    return
                paragraph_content = " ".join(paragraph_parts).strip()
                if paragraph_enabled:
                    ssml_parts.append(f"<p>{paragraph_content}</p>")
                else:
                    ssml_parts.append(paragraph_content)
                paragraph_parts.clear()

            for sentence in sentences:
                sentence_ssml = sentence.to_ssml(
                    capabilities=capabilities,
                    extensions=extensions,
                    wrap_sentence=auto_sentence_tags,
                    warnings=self.warnings if self._strict else None,
                )
                if paragraph_enabled:
                    paragraph_parts.append(sentence_ssml)
                    if sentence.is_paragraph_end:
                        flush_paragraph()
                else:
                    ssml_parts.append(sentence_ssml)

            if paragraph_enabled:
                flush_paragraph()

            if paragraph_enabled:
                ssml = "".join(ssml_parts)
            else:
                ssml = " ".join(ssml_parts)

            # Wrap in <speak> tags if configured
            if output_speak_tag:
                if "amazon:" in ssml and "amazon" not in namespaces and "xmlns:amazon" not in ssml:
                    namespaces = {
                        **namespaces,
                        "amazon": "https://amazon.com/ssml",
                    }
                namespace_attrs = self._format_namespace_attrs(namespaces)
                ssml = f"<speak{namespace_attrs}>{ssml}</speak>"

            # Unescape placeholders AFTER generating SSML
            # (restore original characters in output)
            if self._escape_syntax:
                from ssmd.utils import unescape_ssmd_syntax

                ssml = unescape_ssmd_syntax(ssml, xml_safe=True)

            # Pretty print if configured
            if pretty_print:
                ssml = format_xml(ssml, pretty=True)

            self._cached_ssml = ssml
        return self._cached_ssml

    def to_ssmd(self, *, include_header: bool = False) -> str:
        """Export document to SSMD format with proper formatting.

        Returns SSMD with proper line breaks (each sentence on a new line).

        Returns:
            SSMD markdown string with proper formatting

        Example:
            >>> doc = ssmd.Document.from_ssml('<speak><emphasis>Hi</emphasis></speak>')
            >>> doc.to_ssmd()
            '*Hi*'
        """
        raw_ssmd = self.ssmd
        if not raw_ssmd.strip():
            return self.source if include_header and self.header is not None else raw_ssmd

        # Parse into sentences and format with proper line breaks
        sentences = self._parse_sentence_objects()
        formatted = format_ssmd(sentences).rstrip("\n")
        if self._escape_syntax:
            from ssmd.utils import unescape_ssmd_syntax

            formatted = unescape_ssmd_syntax(formatted)
        if include_header and self.header is not None:
            return serialize_front_matter(self.header, formatted)
        return formatted

    @property
    def source(self) -> str:
        """Return deterministic SSMD including the parsed header, when present."""
        body = self.to_ssmd()
        if self.header is None:
            return body
        return serialize_front_matter(self.header, body)

    @property
    def voice_bindings(self) -> dict[str, dict[str, str]]:
        """Return document voice bindings without exposing header mutation."""
        values = self.header.get("voice_bindings", {}) if self.header else {}
        if not isinstance(values, dict):
            return {}
        return {
            str(provider): dict(bindings)
            for provider, bindings in values.items()
            if isinstance(bindings, dict)
        }

    @property
    def pause_defaults(self) -> PauseDefaults | None:
        """Return normalized document pause defaults, if declared."""
        values = self.header.get("pause_defaults") if self.header else None
        if not isinstance(values, dict):
            return None
        return PauseDefaults(
            enabled=values.get("enabled", False),
            sentence=values.get("sentence"),
            paragraph=values.get("paragraph"),
            voice_change=values.get("voice_change"),
        )

    def to_text(self) -> str:
        """Export document to plain text (strips all markup).

        Returns:
            Plain text string with all SSMD markup removed

        Example:
            >>> doc = ssmd.Document("Hello *world* @marker!")
            >>> doc.to_text()
            'Hello world @marker!'
        """
        sentences = self._parse_sentence_objects()
        text_parts = []
        for sentence in sentences:
            text_parts.append(sentence.to_text())
        text = " ".join(text_parts)
        if self._escape_syntax:
            from ssmd.utils import unescape_ssmd_syntax

            text = unescape_ssmd_syntax(text)
        return text

    # ═══════════════════════════════════════════════════════════
    # PROPERTIES
    # ═══════════════════════════════════════════════════════════

    @property
    def ssmd(self) -> str:
        """Get raw SSMD content.

        Returns the complete SSMD document by joining all fragments
        with their separators.

        Returns:
            SSMD markdown string
        """
        if not self._fragments:
            return ""

        if len(self._fragments) == 1:
            return self._fragments[0]

        result = self._fragments[0]
        for i, separator in enumerate(self._separators):
            result += separator + self._fragments[i + 1]
        return result

    @property
    def config(self) -> dict[str, Any]:
        """Get configuration dictionary.

        Returns:
            Configuration dict
        """
        return self._config

    @config.setter
    def config(self, value: dict[str, Any]) -> None:
        """Set configuration dictionary.

        Args:
            value: New configuration dict
        """
        self._config = value
        self._capabilities_obj = None  # Reset resolved capabilities
        self._invalidate_cache()

    @property
    def capabilities(self) -> "TTSCapabilities | str | None":
        """Get TTS capabilities.

        Returns:
            TTSCapabilities instance, preset name, or None
        """
        return self._capabilities

    @capabilities.setter
    def capabilities(self, value: "TTSCapabilities | str | None") -> None:
        """Set TTS capabilities.

        Args:
            value: TTSCapabilities instance, preset name, or None
        """
        self._capabilities = value
        self._capabilities_obj = None  # Reset resolved capabilities
        self._invalidate_cache()

    # ═══════════════════════════════════════════════════════════
    # ITERATION
    # ═══════════════════════════════════════════════════════════

    def sentences(self, as_documents: bool = False) -> "Iterator[str | Document]":
        """Iterate through sentence-level SSML chunks.

        Sentences are always returned as explicit ``<s>``-wrapped SSML fragments
        so the streaming interface remains stable regardless of paragraph tags.

        Args:
            as_documents: If True, yield Document objects instead of strings.
                Each sentence will be wrapped in its own Document instance.

        Yields:
            SSML sentence strings (str), or Document objects if as_documents=True

        Example:
            >>> doc = ssmd.Document("First. Second. Third.")
            >>> for _sentence in doc.sentences():
            ...     pass

            >>> for sentence_doc in doc.sentences(as_documents=True):
            ...     ssml = sentence_doc.to_ssml()
            ...     ssmd = sentence_doc.to_ssmd()
        """
        self._populate_sentence_cache()

        for sentence in self._cached_sentences or []:
            if as_documents:
                yield Document.from_ssml(
                    sentence,
                    config=self._config,
                    capabilities=self._capabilities,
                )
            else:
                yield sentence

    def paragraphs(self, as_documents: bool = False) -> "Iterator[str | Document]":
        """Iterate through paragraph-level SSML chunks.

        Paragraphs are returned with ``<p>`` tags when supported by capabilities.

        Args:
            as_documents: If True, yield Document objects instead of strings.

        Yields:
            SSML paragraph strings (str), or Document objects if as_documents=True
        """
        self._populate_paragraph_cache()
        capabilities = self._get_capabilities()
        extensions = self._config.get("extensions")
        auto_sentence_tags = self._config.get("auto_sentence_tags", False)
        paragraph_enabled = not capabilities or capabilities.paragraph

        for paragraph in self._cached_paragraphs or []:
            sentence_parts: list[str] = []
            for sentence in paragraph.sentences:
                sentence_parts.append(
                    sentence.to_ssml(
                        capabilities=capabilities,
                        extensions=extensions,
                        wrap_sentence=auto_sentence_tags,
                        warnings=self.warnings if self._strict else None,
                    )
                )
            content = " ".join(part for part in sentence_parts if part).strip()
            if not content:
                continue
            paragraph_ssml = f"<p>{content}</p>" if paragraph_enabled else content
            if self._escape_syntax:
                from ssmd.utils import unescape_ssmd_syntax

                paragraph_ssml = unescape_ssmd_syntax(paragraph_ssml, xml_safe=True)

            if as_documents:
                yield Document.from_ssml(
                    paragraph_ssml,
                    config=self._config,
                    capabilities=self._capabilities,
                )
            else:
                yield paragraph_ssml

    # ═══════════════════════════════════════════════════════════
    # LIST-LIKE INTERFACE (operates on SSML sentences)
    # ═══════════════════════════════════════════════════════════

    def __len__(self) -> int:
        """Return number of sentences in the document.

        Returns:
            Number of sentences

        Example:
            >>> doc = ssmd.Document("First sentence. Second sentence.")
            >>> len(doc)
            2
        """
        if self._cached_sentences is not None:
            return len(self._cached_sentences)
        return len(self._parse_sentence_objects())

    @overload
    def __getitem__(self, index: int) -> str: ...

    @overload
    def __getitem__(self, index: slice) -> list[str]: ...

    def __getitem__(self, index: int | slice) -> str | list[str]:
        """Get sentence(s) by index.

        Args:
            index: Sentence index or slice

        Returns:
            SSML sentence string or list of strings

        Raises:
            IndexError: If index is out of range

        Example:
            >>> doc = ssmd.Document("First. Second. Third.")
            >>> _ = doc[0]  # First sentence SSML
            >>> _ = doc[-1]  # Last sentence SSML
            >>> _ = doc[0:2]  # First two sentences
        """
        self._populate_sentence_cache()
        return (self._cached_sentences or [])[index]

    def __setitem__(self, index: int, value: str) -> None:
        """Replace sentence at index.

        This reconstructs the document with the modified sentence.

        Args:
            index: Sentence index
            value: New SSMD content for this sentence

        Raises:
            IndexError: If index is out of range

        Example:
            >>> doc = ssmd.Document("First. Second. Third.")
            >>> doc[0] = "Modified first sentence."
        """
        self._populate_sentence_cache()

        sentences = self._cached_sentences or []
        self._rebuild_from_sentence_ssml(
            sentences,
            replacement_index=index,
            replacement_ssmd=value,
        )

    def __delitem__(self, index: int) -> None:
        """Delete sentence at index.

        Args:
            index: Sentence index

        Raises:
            IndexError: If index is out of range

        Example:
            >>> doc = ssmd.Document("First. Second. Third.")
            >>> del doc[1]  # Remove second sentence
        """
        self._populate_sentence_cache()

        sentences = self._cached_sentences or []
        remaining_sentences = [
            sentence_ssml for i, sentence_ssml in enumerate(sentences) if i != index
        ]
        self._rebuild_from_sentence_ssml(remaining_sentences)

    def __iter__(self) -> "Iterator[str | Document]":
        """Iterate through sentences.

        Yields:
            SSML sentence strings

        Example:
            >>> doc = ssmd.Document("First. Second.")
            >>> for _sentence in doc:
            ...     pass
        """
        return self.sentences(as_documents=False)

    def __iadd__(self, other: "str | Document") -> "Document":
        """Support += operator for appending content.

        Args:
            other: String or Document to append

        Returns:
            Self for chaining

        Example:
            >>> doc = ssmd.Document("Hello")
            >>> doc += " world"
            >>> other = ssmd.Document("More")
            >>> doc += other
        """
        if isinstance(other, Document):
            # Append another document's content
            return self.add(other.ssmd)
        else:
            # Append string
            return self.add(other)

    # ═══════════════════════════════════════════════════════════
    # EDITING METHODS
    # ═══════════════════════════════════════════════════════════

    def insert(self, index: int, text: str, separator: str = "") -> "Document":
        """Insert text at specific fragment index.

        Args:
            index: Position to insert (0 = beginning)
            text: SSMD text to insert
            separator: Separator to use ("", "\\n", or "\\n\\n")

        Returns:
            Self for method chaining

        Example:
            >>> doc = ssmd.Document("Hello world")
            >>> _ = doc.insert(0, "Start: ", "")
            >>> doc.ssmd
            'Start: Hello world'
        """
        if not text:
            return self

        self._invalidate_cache()

        if not self._fragments:
            self._fragments.append(text)
        elif index == 0:
            # Insert at beginning
            self._fragments.insert(0, text)
            if len(self._fragments) > 1:
                self._separators.insert(0, separator)
        elif index >= len(self._fragments):
            # Append at end
            self._separators.append(separator)
            self._fragments.append(text)
        else:
            # Insert in middle
            self._fragments.insert(index, text)
            self._separators.insert(index, separator)

        return self

    def remove(self, index: int) -> "Document":
        """Remove fragment at index.

        This is the same as `del doc[index]` but returns self for chaining.

        Args:
            index: Fragment index to remove

        Returns:
            Self for method chaining

        Raises:
            IndexError: If index is out of range

        Example:
            >>> doc = ssmd.Document("First. Second. Third.")
            >>> _ = doc.remove(1)
        """
        del self[index]
        return self

    def clear(self) -> "Document":
        """Remove all content from the document.

        Returns:
            Self for method chaining

        Example:
            >>> doc = ssmd.Document("Hello world")
            >>> _ = doc.clear()
            >>> doc.ssmd
            ''
        """
        self._fragments.clear()
        self._separators.clear()
        self._invalidate_cache()
        return self

    def replace(self, old: str, new: str, count: int = -1) -> "Document":
        """Replace text across all fragments.

        Args:
            old: Text to find
            new: Text to replace with
            count: Maximum replacements (-1 = all)

        Returns:
            Self for method chaining

        Example:
            >>> doc = ssmd.Document("Hello world. Hello again.")
            >>> _ = doc.replace("Hello", "Hi")
            >>> doc.ssmd
            'Hi world. Hi again.'
        """
        self._invalidate_cache()

        replacements_made = 0
        for i, fragment in enumerate(self._fragments):
            if count == -1:
                self._fragments[i] = fragment.replace(old, new)
            else:
                remaining = count - replacements_made
                if remaining <= 0:
                    break
                self._fragments[i] = fragment.replace(old, new, remaining)
                replacements_made += self._fragments[i].count(new) - fragment.count(new)

        return self

    # ═══════════════════════════════════════════════════════════
    # ADVANCED METHODS
    # ═══════════════════════════════════════════════════════════

    def merge(self, other: "Document", separator: str = "\n\n") -> "Document":
        """Merge another document into this one.

        Args:
            other: Document to merge
            separator: Separator to use between documents

        Returns:
            Self for method chaining

        Example:
            >>> doc1 = ssmd.Document("First document.")
            >>> doc2 = ssmd.Document("Second document.")
            >>> _ = doc1.merge(doc2)
            >>> doc1.ssmd
            'First document.\\n\\nSecond document.'
        """
        if not other._fragments:
            return self

        self._invalidate_cache()

        if not self._fragments:
            self._fragments = other._fragments.copy()
            self._separators = other._separators.copy()
        else:
            self._separators.append(separator)
            self._fragments.extend(other._fragments)
            self._separators.extend(other._separators)

        return self

    def split(self) -> list["Document"]:
        """Split document into individual sentence Documents.

        Returns:
            List of Document objects, one per sentence

        Example:
            >>> doc = ssmd.Document("First. Second. Third.")
            >>> sentences = doc.split()
            >>> len(sentences)
            3
            >>> sentences[0].ssmd
            'First.\\n'
        """
        return [
            Document.from_ssml(
                str(sentence_ssml),  # Ensure it's a string
                config=self._config,
                capabilities=self._capabilities,
            )
            for sentence_ssml in self.sentences(as_documents=False)
        ]

    def get_fragment(self, index: int) -> str:
        """Get raw fragment by index (not sentence).

        This accesses the internal fragment storage directly,
        which may be different from sentence boundaries.

        Args:
            index: Fragment index

        Returns:
            Raw SSMD fragment string

        Raises:
            IndexError: If index is out of range

        Example:
            >>> doc = ssmd.Document()
            >>> _ = doc.add("First")
            >>> _ = doc.add_sentence("Second")
            >>> doc.get_fragment(0)
            'First'
            >>> doc.get_fragment(1)
            'Second'
        """
        return self._fragments[index]

    # ═══════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ═══════════════════════════════════════════════════════════

    def _rebuild_from_sentence_ssml(
        self,
        sentences: list[str],
        *,
        replacement_index: int | None = None,
        replacement_ssmd: str | None = None,
    ) -> None:
        """Rebuild fragments from SSML sentence list.

        Args:
            sentences: List of SSML sentence strings
            replacement_index: Optional index to replace with SSMD content
            replacement_ssmd: SSMD content to use at replacement_index
        """
        from ssmd.ssml_parser import SSMLParser

        parser = SSMLParser(self._config)
        new_fragments: list[str] = []
        new_separators: list[str] = []

        for i, sentence_ssml in enumerate(sentences):
            if replacement_index is not None and i == replacement_index:
                if replacement_ssmd is not None:
                    new_fragments.append(replacement_ssmd)
                else:
                    new_fragments.append(
                        parser.to_ssmd(sentence_ssml, capabilities=self._capabilities)
                    )
            else:
                new_fragments.append(parser.to_ssmd(sentence_ssml, capabilities=self._capabilities))

            if i < len(sentences) - 1:
                new_separators.append("\n")

        self._fragments = new_fragments
        self._separators = new_separators
        self._invalidate_cache()

    def _sentence_detection_config(
        self,
    ) -> SentenceDetectionConfig:
        """Return one exact sentence-detection configuration for all parse paths."""
        return SentenceDetectionConfig(
            use_spacy=self._config.get("sentence_use_spacy"),
            spacy_model=self._config.get("sentence_spacy_model"),
            model_size=self._config.get("sentence_model_size"),
        )

    def _parse_sentence_objects(self) -> ParsedResult["Sentence"]:
        sentence_config = self._sentence_detection_config()
        sentences = parse_sentences(
            self.ssmd,
            capabilities=self._get_capabilities(),
            model_size=sentence_config.model_size,
            spacy_model=sentence_config.spacy_model,
            use_spacy=sentence_config.use_spacy,
            heading_levels=self._config.get("heading_levels"),
            extensions=self._config.get("extensions"),
            parse_yaml_header=self._parse_yaml_header,
            strict_parse=self._strict,
        )
        self.sentence_detection_diagnostics = sentences.diagnostics
        return sentences

    def _parse_paragraph_objects(self) -> ParsedResult[Paragraph]:
        sentence_config = self._sentence_detection_config()
        paragraphs = parse_paragraphs(
            self.ssmd,
            capabilities=self._get_capabilities(),
            heading_levels=self._config.get("heading_levels"),
            extensions=self._config.get("extensions"),
            use_spacy=sentence_config.use_spacy,
            spacy_model=sentence_config.spacy_model,
            model_size=sentence_config.model_size,
            parse_yaml_header=self._parse_yaml_header,
            strict_parse=self._strict,
        )
        self.sentence_detection_diagnostics = paragraphs.diagnostics
        return paragraphs

    def _populate_sentence_cache(self) -> None:
        if self._cached_sentences is not None:
            return

        capabilities = self._get_capabilities()
        extensions = self._config.get("extensions")
        sentence_objects = self._parse_sentence_objects()
        sentence_ssml: list[str] = []
        for sentence in sentence_objects:
            sentence_ssml.append(
                sentence.to_ssml(
                    capabilities=capabilities,
                    extensions=extensions,
                    wrap_sentence=True,
                    warnings=self.warnings if self._strict else None,
                )
            )

        if self._escape_syntax:
            from ssmd.utils import unescape_ssmd_syntax

            sentence_ssml = [
                unescape_ssmd_syntax(sentence, xml_safe=True) for sentence in sentence_ssml
            ]

        self._cached_sentences = sentence_ssml

    def _populate_paragraph_cache(self) -> None:
        if self._cached_paragraphs is None:
            self._cached_paragraphs = self._parse_paragraph_objects()

    def _get_capabilities(self) -> "TTSCapabilities | None":
        """Get resolved TTSCapabilities object.

        Returns:
            TTSCapabilities instance or None
        """
        if self._capabilities_obj is None and self._capabilities is not None:
            from ssmd.capabilities import TTSCapabilities, get_preset

            if isinstance(self._capabilities, str):
                self._capabilities_obj = get_preset(self._capabilities)
            elif isinstance(self._capabilities, TTSCapabilities):
                self._capabilities_obj = self._capabilities
        return self._capabilities_obj

    def _collect_namespaces(
        self,
        sentences: list["Sentence"],
        extensions: dict | None,
        capabilities: "TTSCapabilities | None",
    ) -> dict[str, str]:
        namespaces: dict[str, str] = dict(self._config.get("namespaces") or {})

        from ssmd.segment import DEFAULT_EXTENSIONS

        ext_handlers = {**DEFAULT_EXTENSIONS, **(extensions or {})}
        used_extensions = {
            segment.extension
            for sentence in sentences
            for segment in sentence.segments
            if segment.extension
        }
        for extension_name in used_extensions:
            if capabilities and not capabilities.supports_extension(extension_name):
                continue
            handler = ext_handlers.get(extension_name)
            handler_namespaces = getattr(handler, "namespaces", None)
            if handler_namespaces:
                namespaces.update(handler_namespaces)

        return namespaces

    def _format_namespace_attrs(self, namespaces: dict[str, str]) -> str:
        if not namespaces:
            return ""
        attrs = " ".join(f'xmlns:{prefix}="{uri}"' for prefix, uri in sorted(namespaces.items()))
        return f" {attrs}"

    def _invalidate_cache(self) -> None:
        """Invalidate cached SSML and sentences."""
        self._cached_ssml = None
        self._cached_sentences = None
        self._cached_paragraphs = None
        self.sentence_detection_diagnostics = None

    def __repr__(self) -> str:
        """String representation of document.

        Returns:
            Representation string

        Example:
            >>> doc = ssmd.Document("Hello.\\nWorld.")
            >>> repr(doc)
            'Document(1 sentences, 13 chars)'
        """
        try:
            num_sentences = len(self)
            return f"Document({num_sentences} sentences, {len(self.ssmd)} chars)"
        except Exception:
            return f"Document({len(self.ssmd)} chars)"

    def __str__(self) -> str:
        """String conversion returns SSMD content.

        Returns:
            SSMD string

        Example:
            >>> doc = ssmd.Document("Hello *world*")
            >>> str(doc)
            'Hello *world*'
        """
        return self.ssmd

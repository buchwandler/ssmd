"""Explicit rendering targets for structural SSMD semantics."""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from ssmd.segment import DEFAULT_EXTENSIONS, ExtensionHandler, xsampa_to_ipa
from ssmd.spans import AnnotationSpan, Diagnostic, ParseStructureResult, StructuralEvent

if TYPE_CHECKING:
    from ssmd.capabilities import TTSCapabilities

RenderTarget = Literal["generic", "ssml-1.1", "provider"]
LossPolicy = Literal["error", "warn", "drop"]


@dataclass(frozen=True)
class RenderResult:
    """Rendered SSML and any reported semantic adaptations or losses."""

    ssml: str
    diagnostics: tuple[Diagnostic, ...] = ()


class RenderError(ValueError):
    """Raised when rendering cannot satisfy the selected loss policy."""

    def __init__(self, diagnostics: tuple[Diagnostic, ...]):
        self.diagnostics = diagnostics
        message = diagnostics[0].message if diagnostics else "SSMD rendering failed"
        super().__init__(message)


@dataclass
class _RenderState:
    target: RenderTarget
    capabilities: TTSCapabilities | None
    extensions: Mapping[str, Callable[[str], str] | ExtensionHandler]
    required_extensions: set[str]
    strict: bool
    diagnostics: list[Diagnostic] = field(default_factory=list)
    diagnostic_keys: set[tuple[str, int | None, int | None]] = field(default_factory=set)
    namespaces: dict[str, str] = field(default_factory=dict)
    policy: LossPolicy = "warn"

    def loss(self, code: str, message: str, span: object | None = None) -> None:
        source_start = getattr(span, "source_start", None)
        source_end = getattr(span, "source_end", None)
        key = (code, source_start, source_end)
        if key in self.diagnostic_keys:
            return
        self.diagnostic_keys.add(key)
        severity: Literal["error", "warning", "info"] = (
            "error"
            if self.strict or self.policy == "error"
            else "info"
            if self.policy == "drop"
            else "warning"
        )
        self.diagnostics.append(
            Diagnostic(
                code=code,
                severity=severity,
                message=message,
                source_start=source_start,
                source_end=source_end,
            )
        )


@dataclass(frozen=True)
class _Wrapper:
    span: AnnotationSpan
    open_tag: str | None = None
    close_tag: str | None = None
    handler: Callable[[str], str] | None = None

    def apply(self, content: str) -> str:
        if self.handler is not None:
            return self.handler(content)
        if self.open_tag is None:
            return content
        return f"{self.open_tag}{content}{self.close_tag or ''}"


def _escape_attr(value: str) -> str:
    return html.escape(value, quote=True)


def _tag_for(attrs: Mapping[str, str]) -> str | None:
    semantic_tag = attrs.get("tag")
    if semantic_tag not in (None, "div", "directive", "annotation"):
        return semantic_tag
    if "ext" in attrs:
        return "extension"
    if "src" in attrs:
        return "audio"
    if "sub" in attrs:
        return "sub"
    if "ph" in attrs or "ipa" in attrs or "sampa" in attrs:
        return "phoneme"
    if "as" in attrs or "say-as" in attrs:
        return "say-as"
    if any(
        key in attrs
        for key in (
            "voice",
            "voice-name",
            "voice-languages",
            "voice-lang",
            "gender",
            "age",
            "variant",
        )
    ):
        return "voice"
    if "lang" in attrs or "language" in attrs:
        return "lang"
    if any(key in attrs for key in ("volume", "rate", "pitch", "v", "r", "p", "vrp")):
        return "prosody"
    if "emphasis" in attrs:
        return "emphasis"
    return None


def _attrs(tag: str, values: Mapping[str, str]) -> str:
    return " ".join(f'{key}="{_escape_attr(value)}"' for key, value in values.items())


def _open(tag: str, values: Mapping[str, str]) -> tuple[str, str]:
    attributes = _attrs(tag, values)
    return (f"<{tag} {attributes}>", f"</{tag}>") if attributes else (f"<{tag}>", f"</{tag}>")


def _supports(state: _RenderState, feature: str, span: object) -> bool:
    caps = state.capabilities if state.target == "provider" else None
    if caps is None:
        return True
    supported = {
        "emphasis": caps.emphasis,
        "break": caps.break_tags,
        "paragraph": caps.paragraph,
        "language": caps.language,
        "phoneme": caps.phoneme,
        "substitution": caps.substitution,
        "prosody": caps.prosody,
        "say_as": caps.say_as,
        "audio": caps.audio,
        "mark": caps.mark,
    }.get(feature, True)
    if feature == "language":
        supported = supported and caps.language_scopes.get("sentence", True)
    if not supported:
        code = (
            "render.unsupported.language"
            if feature == "language"
            else f"render.unsupported.{feature}"
        )
        state.loss(
            code, f"The selected provider target does not support {feature}; it was omitted.", span
        )
    return supported


def _wrapper(span: AnnotationSpan, state: _RenderState) -> _Wrapper | None:  # noqa: C901
    attrs: Mapping[str, str] = span.attrs
    tag = _tag_for(attrs)
    if tag is None:
        state.loss(
            "conversion.ssml.element_unrepresentable",
            "Annotation has no SSML representation.",
            span,
        )
        return None

    if tag == "emphasis":
        if not _supports(state, "emphasis", span):
            return None
        level = attrs.get("emphasis", "moderate")
        emphasis_values = {} if level == "moderate" else {"level": level}
        opening, closing = _open("emphasis", emphasis_values)
        return _Wrapper(span, opening, closing)

    if tag == "lang":
        language = attrs.get("lang") or attrs.get("language")
        if language is None:
            state.loss(
                "conversion.ssml.element_unrepresentable",
                "Language annotation has no language tag.",
                span,
            )
            return None
        if not _supports(state, "language", span):
            return None
        opening, closing = _open("lang", {"xml:lang": language})
        return _Wrapper(span, opening, closing)

    if tag == "voice":
        voice_values: dict[str, str] = {}
        reference = attrs.get("voice")
        selected_name = attrs.get("voice-name") or reference
        if reference and attrs.get("voice-name") and reference != attrs["voice-name"]:
            state.loss(
                "render.voice.unresolved",
                f"Logical voice {reference!r} cannot be resolved alongside the explicit voice-name selector.",
                span,
            )
        if selected_name:
            voice_values["name"] = selected_name
        languages = (
            attrs.get("voice-languages") or attrs.get("voice-lang") or attrs.get("voice_lang")
        )
        if languages:
            voice_values["languages"] = languages
        for key in ("gender", "age", "variant"):
            if key in attrs:
                voice_values[key] = attrs[key]
        if not voice_values:
            state.loss(
                "conversion.ssml.element_unrepresentable",
                "Voice annotation has no selectors.",
                span,
            )
            return None
        opening, closing = _open("voice", voice_values)
        return _Wrapper(span, opening, closing)

    if tag == "prosody":
        prosody_values = {key: attrs[key] for key in ("volume", "rate", "pitch") if key in attrs}
        if not prosody_values and "vrp" in attrs:
            packed = attrs["vrp"]
            if re.fullmatch(r"[0-5][1-5][1-5]", packed):
                prosody_values = dict(zip(("volume", "rate", "pitch"), packed, strict=True))
        if state.target == "provider" and state.capabilities is not None:
            filtered = {}
            for key, value in prosody_values.items():
                if getattr(state.capabilities, key):
                    filtered[key] = value
                else:
                    state.loss(
                        f"render.unsupported.{key}",
                        f"The selected provider target does not support prosody {key}; it was omitted.",
                        span,
                    )
            prosody_values = filtered
        if not prosody_values:
            if attrs:
                state.loss(
                    "conversion.ssml.element_unrepresentable",
                    "Prosody annotation has no representable attributes.",
                    span,
                )
            return None
        if not _supports(state, "prosody", span):
            return None
        opening, closing = _open("prosody", prosody_values)
        return _Wrapper(span, opening, closing)

    if tag == "say-as":
        if not _supports(state, "say_as", span):
            return None
        interpret_as = attrs.get("as") or attrs.get("say-as")
        if not interpret_as:
            state.loss(
                "conversion.ssml.element_unrepresentable",
                "say-as annotation has no interpret-as value.",
                span,
            )
            return None
        say_as_values = {"interpret-as": interpret_as}
        for key in ("format", "detail"):
            if key in attrs:
                say_as_values[key] = attrs[key]
        opening, closing = _open("say-as", say_as_values)
        return _Wrapper(span, opening, closing)

    if tag == "sub":
        if not _supports(state, "substitution", span):
            return None
        opening, closing = _open("sub", {"alias": attrs["sub"]})
        return _Wrapper(span, opening, closing)

    if tag == "phoneme":
        if not _supports(state, "phoneme", span):
            return None
        phoneme = attrs.get("ph") or attrs.get("ipa") or attrs.get("sampa")
        alphabet = attrs.get("alphabet", "ipa")
        if "sampa" in attrs:
            alphabet = "x-sampa"
        if not phoneme:
            state.loss(
                "conversion.ssml.element_unrepresentable",
                "Phoneme annotation has no pronunciation.",
                span,
            )
            return None
        if alphabet.lower() in {"sampa", "x-sampa"}:
            phoneme = xsampa_to_ipa(phoneme)
        opening, closing = _open("phoneme", {"alphabet": "ipa", "ph": phoneme})
        return _Wrapper(span, opening, closing)

    if tag == "audio":
        if not _supports(state, "audio", span):
            return None
        audio_values: dict[str, str] = {"src": attrs["src"]}
        clip = attrs.get("clip")
        if clip and "-" in clip:
            begin, end = clip.split("-", 1)
            if begin:
                audio_values["clipBegin"] = begin
            if end:
                audio_values["clipEnd"] = end
        for source, destination in (
            ("speed", "speed"),
            ("repeat", "repeatCount"),
            ("repeatDur", "repeatDur"),
            ("repeatdur", "repeatDur"),
            ("level", "soundLevel"),
        ):
            if source in attrs:
                audio_values[destination] = attrs[source]
        opening, closing = _open("audio", audio_values)
        if "alt" in attrs:
            state.loss(
                "render.audio.alt_legacy",
                "The legacy alt attribute does not represent 0.9 description metadata; use desc instead.",
                span,
            )
        description = attrs.get("desc")
        if description:
            opening += f"<desc>{html.escape(description)}</desc>"
        return _Wrapper(span, opening, closing)

    if tag == "extension":
        extension_name = attrs.get("ext", "")
        handler = state.extensions.get(extension_name)
        if handler is None or (
            state.capabilities
            and state.target == "provider"
            and not state.capabilities.supports_extension(extension_name)
        ):
            state.loss(
                "render.unsupported.extension",
                f"Extension {extension_name!r} is not available for the selected rendering target.",
                span,
            )
            return None
        if isinstance(handler, ExtensionHandler):
            state.namespaces.update(handler.namespaces)
            callable_handler = handler.handler
        else:
            callable_handler = handler
        if extension_name in {"whisper", "drc"}:
            state.namespaces.setdefault("amazon", "https://amazon.com/ssml")
        return _Wrapper(span, handler=callable_handler)

    state.loss(
        "conversion.ssml.element_unrepresentable",
        f"Annotation type {tag!r} has no SSML representation.",
        span,
    )
    return None


def _event_markup(event: StructuralEvent, state: _RenderState) -> str:
    kind = event.kind
    attrs: Mapping[str, str] = event.attrs
    if kind == "break":
        if not _supports(state, "break", event):
            return ""
        values = {key: attrs[key] for key in ("time", "strength") if key in attrs}
        return f"<break{(' ' + _attrs('break', values)) if values else ''}/>"
    if kind == "mark":
        if not _supports(state, "mark", event):
            return ""
        return f'<mark name="{_escape_attr(attrs.get("name", ""))}"/>'
    return ""


def _transition_wrappers(
    current: list[_Wrapper],
    following: list[_Wrapper],
    output: list[str],
) -> list[_Wrapper]:
    common = 0
    while (
        common < len(current)
        and common < len(following)
        and current[common].span is following[common].span
    ):
        common += 1
    for wrapper in reversed(current[common:]):
        if wrapper.close_tag:
            output.append(wrapper.close_tag)
    for wrapper in following[common:]:
        if wrapper.handler is None and wrapper.open_tag:
            output.append(wrapper.open_tag)
    return following


def render_structure(  # noqa: C901
    structure: ParseStructureResult,
    *,
    target: RenderTarget = "generic",
    capabilities: TTSCapabilities | None = None,
    extensions: Mapping[str, Callable[[str], str] | ExtensionHandler] | None = None,
    namespaces: Mapping[str, str] | None = None,
    language: str | None = None,
    fallback_language: str | None = None,
    loss_policy: LossPolicy = "warn",
    strict: bool = False,
    strict_syntax: bool = False,
) -> RenderResult:
    """Render one structural parse using an explicit target and loss policy."""
    if target not in ("generic", "ssml-1.1", "provider"):
        raise ValueError("target must be 'generic', 'ssml-1.1', or 'provider'")
    if loss_policy not in ("error", "warn", "drop"):
        raise ValueError("loss_policy must be 'error', 'warn', or 'drop'")
    if target == "provider" and capabilities is None:
        raise ValueError("provider rendering requires capabilities")

    handlers: dict[str, Callable[[str], str] | ExtensionHandler] = dict(DEFAULT_EXTENSIONS)
    handlers.update(extensions or {})
    required = structure.header.get("requires", {})
    required_extensions = required.get("extensions", []) if isinstance(required, Mapping) else []
    state = _RenderState(
        target=target,
        capabilities=capabilities,
        extensions=handlers,
        required_extensions=(
            {item for item in required_extensions if isinstance(item, str)}
            if isinstance(required_extensions, list)
            else set()
        ),
        strict=strict or target == "ssml-1.1",
        namespaces=dict(namespaces or {}),
        policy=loss_policy,
    )
    state.diagnostics.extend(structure.diagnostics)
    state.diagnostic_keys.update(
        (item.code, item.source_start, item.source_end) for item in structure.diagnostics
    )
    if (state.strict or strict_syntax) and any(
        item.severity == "error" for item in structure.diagnostics
    ):
        raise RenderError(tuple(state.diagnostics))
    root_language = language or structure.header.get("language") or fallback_language
    if (
        target == "provider"
        and capabilities
        and root_language
        and (not capabilities.language or not capabilities.language_scopes.get("root", True))
    ):
        state.loss(
            "render.unsupported.language",
            "The selected provider target does not support a root language; it was omitted.",
        )
        root_language = None
    if target == "ssml-1.1" and not root_language:
        state.loss(
            "render.language.required", "The ssml-1.1 target requires an explicit root language."
        )

    text = structure.clean_text
    paragraph_ranges: list[tuple[int, int]] = []
    cursor = 0
    for match in re.finditer(r"\n{2,}", text):
        paragraph_ranges.append((cursor, match.start()))
        cursor = match.end()
    paragraph_ranges.append((cursor, len(text)))

    annotations = [
        item
        for item in (structure.effective_annotations or structure.annotations)
        if item.char_end > item.char_start
    ]
    events_by_pos: dict[int, list[StructuralEvent]] = {}
    for event in structure.events:
        if event.kind in {"break", "mark"}:
            events_by_pos.setdefault(event.pos, []).append(event)

    paragraph_supported = target != "provider" or capabilities is None or capabilities.paragraph
    if not paragraph_supported and len(paragraph_ranges) > 1:
        state.loss(
            "render.unsupported.paragraph",
            "The selected provider target does not support paragraphs.",
        )

    rendered_paragraphs: list[str] = []

    for paragraph_start, paragraph_end in paragraph_ranges:
        paragraph_annotations = [
            item
            for item in annotations
            if item.char_start < paragraph_end and item.char_end > paragraph_start
        ]
        paragraph_events = {
            pos: values
            for pos, values in events_by_pos.items()
            if paragraph_start <= pos <= paragraph_end
        }
        positions = {paragraph_start, paragraph_end}
        for annotation in paragraph_annotations:
            positions.add(max(paragraph_start, annotation.char_start))
            positions.add(min(paragraph_end, annotation.char_end))
        positions.update(paragraph_events)
        points = sorted(positions)
        pieces: list[str] = []
        active_wrappers: list[_Wrapper] = []

        def wrapped_handlers(content: str, wrappers: list[_Wrapper]) -> str:
            for wrapper in reversed(wrappers):
                if wrapper.handler is not None:
                    content = wrapper.apply(content)
            return content

        for index, position in enumerate(points):
            following = points[index + 1] if index + 1 < len(points) else position
            at_position = paragraph_events.get(position, [])
            for event in at_position:
                if event.anchor == "after":
                    event_wrappers = [
                        wrapper for wrapper in active_wrappers if wrapper.span.char_end > position
                    ]
                    active_wrappers = _transition_wrappers(active_wrappers, event_wrappers, pieces)
                    pieces.append(wrapped_handlers(_event_markup(event, state), event_wrappers))

            next_wrappers: list[_Wrapper] = []
            if following > position:
                active = [
                    item
                    for item in paragraph_annotations
                    if item.char_start <= position and item.char_end >= following
                ]
                active.sort(
                    key=lambda item: (item.char_start, -item.char_end, item.source_start or 0)
                )
                next_wrappers = [
                    wrapper for item in active if (wrapper := _wrapper(item, state)) is not None
                ]
            active_wrappers = _transition_wrappers(active_wrappers, next_wrappers, pieces)

            for event in at_position:
                if event.anchor == "before":
                    pieces.append(wrapped_handlers(_event_markup(event, state), active_wrappers))
            if following > position:
                content = html.escape(text[position:following], quote=False)
                pieces.append(wrapped_handlers(content, active_wrappers))

        _transition_wrappers(active_wrappers, [], pieces)
        rendered = "".join(pieces)
        if target == "provider" and capabilities is not None and not capabilities.paragraph:
            rendered_paragraphs.append(rendered)
        else:
            rendered_paragraphs.append(f"<p>{rendered}</p>")

    if target == "provider" and capabilities is not None and not capabilities.paragraph:
        body = " ".join(rendered_paragraphs)
    else:
        body = "".join(rendered_paragraphs)

    for extension_name in state.required_extensions:
        if extension_name not in handlers:
            state.loss(
                "render.unsupported.extension",
                f"Required extension {extension_name!r} is not registered in the trusted renderer registry.",
            )

    diagnostics = tuple(state.diagnostics)
    blocking = tuple(
        item
        for item in diagnostics
        if (state.strict and item.severity == "error")
        or (loss_policy == "error" and item.code.startswith(("render.", "conversion.")))
    )
    if blocking:
        raise RenderError(blocking)

    root_attrs: list[str] = []
    if target == "ssml-1.1":
        root_attrs.extend(
            [
                'xmlns="http://www.w3.org/2001/10/synthesis"',
                'version="1.1"',
                f'xml:lang="{_escape_attr(str(root_language or ""))}"',
            ]
        )
    elif root_language:
        root_attrs.append(f'xml:lang="{_escape_attr(str(root_language))}"')
    state.namespaces.update(namespaces or {})
    root_attrs.extend(
        f'xmlns:{prefix}="{_escape_attr(uri)}"'
        for prefix, uri in sorted(state.namespaces.items())
        if prefix not in {"xml", "xmlns"}
    )
    ssml = f"<speak{' ' + ' '.join(root_attrs) if root_attrs else ''}>{body}</speak>"
    return RenderResult(ssml, diagnostics)

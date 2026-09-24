"""Source-aware syntax nodes for the SSMD 0.9 parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from ssmd.tokenizer import Token


@dataclass(frozen=True)
class Node:
    source_start: int
    source_end: int


@dataclass(frozen=True)
class TextNode(Node):
    value: str


@dataclass(frozen=True)
class EmphasisNode(Node):
    level: str
    children: tuple[Node, ...]


@dataclass(frozen=True)
class AnnotationNode(Node):
    attrs: dict[str, str]
    children: tuple[Node, ...]


@dataclass(frozen=True)
class BreakNode(Node):
    attrs: dict[str, str]


@dataclass(frozen=True)
class MarkNode(Node):
    name: str


@dataclass(frozen=True)
class ParagraphNode(Node):
    children: tuple[Node, ...]


@dataclass(frozen=True)
class HeadingNode(Node):
    level: int
    children: tuple[Node, ...]


@dataclass(frozen=True)
class DirectiveNode(Node):
    attrs: dict[str, str]
    children: tuple[Node, ...]
    fence_length: int


NodeType: TypeAlias = (
    TextNode
    | EmphasisNode
    | AnnotationNode
    | BreakNode
    | MarkNode
    | ParagraphNode
    | HeadingNode
    | DirectiveNode
)


@dataclass(frozen=True)
class DocumentNode(Node):
    children: tuple[NodeType, ...]


def _is_tight_directive_transition(previous: Node, current: Node, gap: str) -> bool:
    return (
        isinstance(previous, DirectiveNode)
        and isinstance(current, DirectiveNode)
        and not any(character in gap for character in "\r\n")
    )


def _node_from_token(token: Token) -> NodeType:
    children = tuple(_node_from_token(child) for child in token.children)
    if token.kind == "text":
        return TextNode(token.source_start, token.source_end, token.value)
    if token.kind == "emphasis":
        return EmphasisNode(token.source_start, token.source_end, token.value, children)
    if token.kind == "annotation":
        return AnnotationNode(token.source_start, token.source_end, token.attrs, children)
    if token.kind == "break":
        return BreakNode(token.source_start, token.source_end, token.attrs)
    if token.kind == "mark":
        return MarkNode(token.source_start, token.source_end, token.value)
    if token.kind == "paragraph":
        return ParagraphNode(token.source_start, token.source_end, children)
    if token.kind == "heading":
        return HeadingNode(token.source_start, token.source_end, token.level, children)
    if token.kind == "directive":
        return DirectiveNode(
            token.source_start,
            token.source_end,
            token.attrs,
            children,
            token.level,
        )
    raise ValueError(f"Unsupported SSMD token kind: {token.kind}")


def ast_from_tokens(
    tokens: tuple[Token, ...],
    *,
    source_start: int,
    source_end: int,
) -> DocumentNode:
    """Build the immutable syntax tree while retaining original source offsets."""
    return DocumentNode(
        source_start,
        source_end,
        tuple(_node_from_token(token) for token in tokens),
    )

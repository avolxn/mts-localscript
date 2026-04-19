from __future__ import annotations

from textwrap import dedent
from typing import Any

from localscript.core.schemas import KnowledgeChunk


def history_text(history: list[dict[str, Any]]) -> str:
    if not history:
        return "No prior messages."
    lines = [f"{item['role']}[{item['kind']}]: {item['content']}" for item in history[-8:]]
    return "\n".join(lines)


def knowledge_text(chunks: list[KnowledgeChunk]) -> str:
    if not chunks:
        return "No local knowledge snippets found."
    parts = []
    for chunk in chunks:
        parts.append(
            dedent(
                f"""
                Source: {chunk.source}
                Title: {chunk.title}
                Content:
                {chunk.content}
                """
            ).strip()
        )
    return "\n\n".join(parts)


def bullet_text(items: tuple[str, ...]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def normalize_code(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [str(item).rstrip("\n") for item in value if str(item).strip()]
        return "\n".join(parts).strip()
    return str(value).strip()

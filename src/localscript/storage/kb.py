from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from localscript.core.schemas import KnowledgeChunk
from localscript.storage.sqlite import SQLiteStore


@dataclass(slots=True)
class LocalKnowledgeBase:
    data_dir: Path
    store: SQLiteStore

    def rebuild(self) -> None:
        chunks = list(build_document_chunks(self.data_dir))
        self.store.reset_kb()
        self.store.upsert_kb_chunks(chunks)

    def search(self, query: str, limit: int = 5) -> list[KnowledgeChunk]:
        return self.store.search_kb(query, limit=limit)


def build_document_chunks(data_dir: Path) -> Iterable[KnowledgeChunk]:
    supported = {".md", ".yaml", ".yml", ".txt"}
    for path in sorted(data_dir.rglob("*")):
        if path.suffix.lower() not in supported or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for index, chunk in enumerate(split_document(path, text), start=1):
            yield KnowledgeChunk(
                chunk_id=f"{path.name}-{index}",
                source=str(path.relative_to(data_dir.parent)),
                title=chunk["title"],
                content=chunk["content"],
                kind=path.suffix.lower().lstrip("."),
            )


def split_document(path: Path, text: str, max_chars: int = 1400) -> list[dict[str, str]]:
    lines = text.splitlines()
    chunks: list[dict[str, str]] = []
    current_title = path.stem
    buffer: list[str] = []
    for line in lines:
        if line.startswith("#") or line.endswith(":") and len(line) < 80:
            if buffer:
                chunks.extend(_flush_buffer(current_title, buffer, max_chars))
                buffer = []
            current_title = line.strip("# ").strip()
            continue
        buffer.append(line)
    if buffer:
        chunks.extend(_flush_buffer(current_title, buffer, max_chars))
    return [chunk for chunk in chunks if chunk["content"].strip()]


def _flush_buffer(title: str, buffer: list[str], max_chars: int) -> list[dict[str, str]]:
    text = "\n".join(buffer).strip()
    if not text:
        return []
    items: list[dict[str, str]] = []
    start = 0
    while start < len(text):
        window = text[start : start + max_chars]
        if len(window) == max_chars:
            last_break = window.rfind("\n\n")
            if last_break > max_chars // 2:
                window = window[:last_break]
        items.append({"title": title, "content": window.strip()})
        start += max(len(window), 1)
    return items

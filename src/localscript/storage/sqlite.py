from __future__ import annotations

import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from localscript.core.schemas import KnowledgeChunk, SessionRecord, now_iso

FTS_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
MISSING = object()


class SQLiteStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    clarification_question TEXT,
                    execution_brief TEXT,
                    latest_code TEXT,
                    latest_summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS kb_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    kind TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts
                USING fts5(chunk_id UNINDEXED, source, title, content, kind)
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(sessions)").fetchall()
            }
            if "execution_brief" not in columns:
                connection.execute("ALTER TABLE sessions ADD COLUMN execution_brief TEXT")

    def reset_kb(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM kb_chunks")
            connection.execute("DELETE FROM kb_fts")

    def upsert_kb_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        with self._connect() as connection:
            for chunk in chunks:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO kb_chunks (chunk_id, source, title, content, kind)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.chunk_id,
                        chunk.source,
                        chunk.title,
                        chunk.content,
                        chunk.kind,
                    ),
                )
                connection.execute(
                    """
                    INSERT OR REPLACE INTO kb_fts (rowid, chunk_id, source, title, content, kind)
                    VALUES (
                        COALESCE((SELECT rowid FROM kb_fts WHERE chunk_id = ?), NULL),
                        ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        chunk.chunk_id,
                        chunk.chunk_id,
                        chunk.source,
                        chunk.title,
                        chunk.content,
                        chunk.kind,
                    ),
                )

    def search_kb(self, query: str, limit: int = 5) -> list[KnowledgeChunk]:
        sanitized = self._fts_query(query)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT chunk_id, source, title, content, kind, bm25(kb_fts) AS score
                FROM kb_fts
                WHERE kb_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (sanitized, limit),
            ).fetchall()
            return [
                KnowledgeChunk(
                    chunk_id=row["chunk_id"],
                    source=row["source"],
                    title=row["title"],
                    content=row["content"],
                    kind=row["kind"],
                    score=float(-row["score"]),
                )
                for row in rows
            ]

    def create_session(self, prompt: str, *, status: str = "created") -> SessionRecord:
        session_id = uuid.uuid4().hex
        timestamp = now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    session_id, status, prompt, clarification_question, execution_brief, latest_code, latest_summary, created_at, updated_at
                ) VALUES (?, ?, ?, NULL, NULL, NULL, NULL, ?, ?)
                """,
                (session_id, status, prompt, timestamp, timestamp),
            )
        return self.get_session(session_id)

    def update_session(
        self,
        session_id: str,
        *,
        status: str | object = MISSING,
        clarification_question: str | None | object = MISSING,
        execution_brief: str | None | object = MISSING,
        latest_code: str | None | object = MISSING,
        latest_summary: str | None | object = MISSING,
    ) -> None:
        updates: dict[str, Any] = {"updated_at": now_iso()}
        if status is not MISSING:
            updates["status"] = status
        if clarification_question is not MISSING:
            updates["clarification_question"] = clarification_question
        if execution_brief is not MISSING:
            updates["execution_brief"] = execution_brief
        if latest_code is not MISSING:
            updates["latest_code"] = latest_code
        if latest_summary is not MISSING:
            updates["latest_summary"] = latest_summary
        assignments = ", ".join(f"{column} = ?" for column in updates)
        values = list(updates.values()) + [session_id]
        with self._connect() as connection:
            connection.execute(f"UPDATE sessions SET {assignments} WHERE session_id = ?", values)

    def append_message(self, session_id: str, *, role: str, kind: str, content: str) -> int:
        timestamp = now_iso()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages (session_id, role, kind, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, kind, content, timestamp),
            )
            return int(cursor.lastrowid)
    def get_session(self, session_id: str) -> SessionRecord:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            raise KeyError(session_id)
        return SessionRecord(
            session_id=row["session_id"],
            status=row["status"],
            prompt=row["prompt"],
            clarification_question=row["clarification_question"],
            execution_brief=row["execution_brief"],
            latest_code=row["latest_code"],
            latest_summary=row["latest_summary"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT message_id, session_id, role, kind, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY message_id
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]
    def _fts_query(self, query: str) -> str:
        tokens = [token for token in FTS_TOKEN_RE.findall(query) if token.strip()]
        if not tokens:
            return '""'
        return " OR ".join(f'"{token}"' for token in tokens[:12])

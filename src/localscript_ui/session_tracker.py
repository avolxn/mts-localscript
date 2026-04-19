from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from operator import attrgetter
from typing import Literal

from textual.signal import Signal

type SessionState = Literal["notready", "busy", "asking", "idle"]


@dataclass
class SessionDetails:
    """Tracks a concurrent session."""

    index: int
    """Index of session, used in sorting."""
    mode_name: str
    """The screen mode name."""
    title: str = ""
    """The title of the conversation."""
    subtitle: str = ""
    """The subtitle of the conversation."""
    path: str = ""
    """The project directory path."""
    state: SessionState = "notready"
    """The current state of the session."""
    summary: str = ""
    """Suplimentary information about the session."""

    updates: int = 0
    """Track updates to the session details."""
    agent_session_id: str | None = None
    """Agent/backend session id for resume-aware routing."""
    session_pk: int | None = None
    """UI database primary key for persisted session."""


@dataclass
class SavedSessionDetails:
    """Tracks a persisted resumable session."""

    session_pk: int
    """UI database primary key."""
    agent_identity: str
    """Agent identity used to relaunch the session."""
    agent_session_id: str
    """Backend/ACP session id."""
    title: str = ""
    """Session title."""
    subtitle: str = ""
    """Agent or additional description."""
    path: str = ""
    """Project directory path."""


class SessionTracker:
    """Tracks concurrent agent settings"""

    def __init__(self, signal: Signal[tuple[str, SessionDetails | None]]) -> None:
        self.sessions: dict[str, SessionDetails] = {}
        self._session_index = 0
        self.signal = signal

    @property
    def session_count(self) -> int:
        return len(self.sessions)

    def new_session(self) -> SessionDetails:
        self._session_index += 1
        mode_name = f"session-{self._session_index}"
        session_meta = SessionDetails(index=self._session_index, mode_name=mode_name, title="New Session")
        self.sessions[mode_name] = session_meta
        return session_meta

    def close_session(self, mode_name: str) -> None:
        if mode_name in self.sessions:
            del self.sessions[mode_name]
            self.signal.publish((mode_name, None))

    def get_session(self, mode_name: str) -> SessionDetails | None:
        return self.sessions.get(mode_name, None)

    def update_session(
        self,
        mode_name: str,
        title: str | None = None,
        subtitle: str | None = None,
        path: str | None = None,
        state: SessionState | None = None,
        agent_session_id: str | None = None,
        session_pk: int | None = None,
    ) -> SessionDetails:
        session_details = self.sessions[mode_name]
        if title is not None:
            session_details.title = title
        if subtitle is not None:
            session_details.subtitle = subtitle
        if path is not None:
            session_details.path = path
        if state is not None:
            session_details.state = state
        if agent_session_id is not None:
            session_details.agent_session_id = agent_session_id
        if session_pk is not None:
            session_details.session_pk = session_pk
        self.signal.publish((mode_name, session_details))
        return session_details

    @property
    def ordered_sessions(self) -> Sequence[SessionDetails]:
        return sorted(self.sessions.values(), key=attrgetter("index"))

    def __iter__(self) -> Iterable[SessionDetails]:
        return iter(self.ordered_sessions)

    def session_cursor_move(self, mode_name: str, direction: Literal[-1, +1]) -> str | None:
        mode_names = [session.mode_name for session in self.ordered_sessions]
        try:
            mode_index = mode_names.index(mode_name)
        except ValueError:
            return None
        mode_index = (mode_index + direction) % len(mode_names)
        new_mode_name = mode_names[mode_index]
        return new_mode_name

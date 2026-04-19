from __future__ import annotations

from textual import getters
from textual.app import ComposeResult

from localscript_ui.app import ToadApp
from localscript_ui.session_tracker import SavedSessionDetails, SessionDetails, SessionTracker
from localscript_ui.widgets.grid_select import GridSelect
from localscript_ui.widgets.session_summary import SessionSummary


class SessionGridSelect(GridSelect):
    FOCUS_ON_CLICK = True
    app: getters.app[ToadApp] = getters.app(ToadApp)

    def __init__(
        self,
        session_tracker: SessionTracker,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.session_tracker = session_tracker
        self.saved_sessions: list[SavedSessionDetails] = []
        super().__init__(
            id=id,
            classes=classes,
            min_column_width=36,
        )

    def allow_focus(self) -> bool:
        return True

    def on_mount(self) -> None:
        self.app.session_update_signal.subscribe(self, self.handle_session_update_signal)

    def update_current(self, current_mode: str) -> None:
        for index, session_summary in enumerate(self.query_children(SessionSummary)):
            session_summary.current = False
            if session_summary.session_details is not None:
                current = (
                    isinstance(session_summary.session_details, SessionDetails)
                    and session_summary.session_details.mode_name == current_mode
                )
                session_summary.current = current
                if current:
                    self.highlighted = index
                    break

    async def set_saved_sessions(self, saved_sessions: list[SavedSessionDetails]) -> None:
        self.saved_sessions = saved_sessions
        for widget in list(self.query_children(SessionSummary)):
            await widget.remove()
        for session in self.session_tracker.ordered_sessions:
            await self.mount(SessionSummary(session, id=session.mode_name))
        for session in self.saved_sessions:
            await self.mount(SessionSummary(session, id=f"saved-session-{session.session_pk}"))

    async def handle_session_update_signal(self, update: tuple[str, SessionDetails | None]) -> None:
        mode_name, details = update
        session_summary = self.query_one_optional(f"#{mode_name}", SessionSummary)
        if details is None:
            if session_summary is not None:
                await session_summary.remove()
            return

        if session_summary is None:
            await self.mount(SessionSummary(details, id=details.mode_name))
        else:
            session_summary.session_details = details

    def compose(self) -> ComposeResult:
        for session in self.session_tracker.ordered_sessions:
            yield SessionSummary(session, id=session.mode_name)
        for session in self.saved_sessions:
            yield SessionSummary(session, id=f"saved-session-{session.session_pk}")

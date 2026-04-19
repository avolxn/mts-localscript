from __future__ import annotations

import json

from textual import containers, getters, on, widgets
from textual.app import ComposeResult
from textual.binding import Binding
from textual.events import ScreenResume
from textual.screen import ModalScreen
from textual.widget import Widget

from localscript_ui.app import ToadApp
from localscript_ui.db import DB
from localscript_ui.session_tracker import SavedSessionDetails
from localscript_ui.widgets.grid_select import GridSelect
from localscript_ui.widgets.session_grid_select import SessionGridSelect
from localscript_ui.widgets.session_summary import SessionSummary

INSTRUCTIONS_NO_SESSIONS = "Live and saved sessions are shown here."


class SessionsScreen(ModalScreen[str | SavedSessionDetails]):
    CSS_PATH = "sessions.tcss"
    BINDINGS = [Binding("escape", "dismiss", "Dismiss")]

    app: getters.app[ToadApp] = getters.app(ToadApp)
    session_grid_select = getters.query_one(SessionGridSelect)

    def compose(self) -> ComposeResult:
        with containers.Center(id="title-container"):
            yield widgets.Label("Sessions")
        yield widgets.Static(INSTRUCTIONS_NO_SESSIONS, classes="instructions")
        yield SessionGridSelect(self.app.session_tracker)
        yield widgets.Footer()

    async def on_mount(self) -> None:
        db = DB()
        saved_sessions = await db.session_get_recent()
        open_session_ids = {
            session.agent_session_id
            for session in self.app.session_tracker.ordered_sessions
            if session.agent_session_id
        }
        open_session_pks = {
            session.session_pk
            for session in self.app.session_tracker.ordered_sessions
            if session.session_pk is not None
        }
        saved_items: list[SavedSessionDetails] = []
        if saved_sessions is not None:
            for saved_session in saved_sessions:
                if str(saved_session["agent_session_id"]) in open_session_ids:
                    continue
                if int(saved_session["id"]) in open_session_pks:
                    continue
                path = ""
                if meta_json := saved_session["meta_json"]:
                    meta = json.loads(meta_json)
                    path = str(meta.get("cwd", ""))
                saved_items.append(
                    SavedSessionDetails(
                        session_pk=int(saved_session["id"]),
                        agent_identity=str(saved_session["agent_identity"]),
                        agent_session_id=str(saved_session["agent_session_id"]),
                        title=str(saved_session["title"]),
                        subtitle=str(saved_session["agent"]),
                        path=path,
                    )
                )
        await self.session_grid_select.set_saved_sessions(saved_items)

    @property
    def focus_chain(self) -> list[Widget]:
        return [self.session_grid_select]

    def _on_screen_resume(self, event: ScreenResume) -> None:
        current_mode = self.app.screen_stack[0].id
        for instructions in self.query(".instructions"):
            instructions.display = not self.session_grid_select.children
        if current_mode is not None:
            self.session_grid_select.update_current(current_mode)

    def _on_screen_suspend(self) -> None:
        current_mode = self.app.screen_stack[0].id
        if current_mode is not None:
            self.session_grid_select.update_current(current_mode)

    @on(GridSelect.Selected)
    def on_selected(self, event: GridSelect.Selected) -> None:
        if isinstance(event.widget, SessionSummary) and event.widget.session_details is not None:
            session_details = event.widget.session_details
            if isinstance(session_details, SavedSessionDetails):
                self.dismiss(session_details)
                return
            self.dismiss(session_details.mode_name)

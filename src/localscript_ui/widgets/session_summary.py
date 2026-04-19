from __future__ import annotations

from textual import containers, getters, widgets
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.timer import Timer

from localscript_ui.session_tracker import SavedSessionDetails, SessionDetails
from localscript_ui.widgets.condensed_path import CondensedPath
from localscript_ui.widgets.throbber import ThrobberVisual


class BusyIndicator(widgets.Static):
    def render(self) -> ThrobberVisual:
        return ThrobberVisual("▔")

    def on_mount(self) -> None:
        self.auto_refresh = 1 / 4


class SessionSummary(containers.VerticalGroup):
    session_details: reactive[SessionDetails | SavedSessionDetails | None] = reactive(
        None,
        always_update=True,
        recompose=True,
    )

    title = getters.query_one(".title", widgets.Label)
    subtitle = getters.query_one(".subtitle", widgets.Label)
    current = reactive(True, toggle_class="-current", init=False, recompose=True)
    blink = reactive(False, toggle_class="-blink")

    def __init__(
        self,
        session_details: SessionDetails | SavedSessionDetails | None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.blink_timer: Timer | None = None
        self.set_reactive(SessionSummary.session_details, session_details)

    def on_mount(self) -> None:
        def do_blink() -> None:
            self.blink = not self.blink

        self.blink_timer = self.set_interval(0.5, do_blink, pause=False)

    def watch_current(self, current: bool) -> None:
        if (session_details := self.session_details) is not None:
            if current:
                self.title.update(f"✱{session_details.title}")
            else:
                self.title.update(session_details.title)

    @property
    def is_saved_session(self) -> bool:
        return isinstance(self.session_details, SavedSessionDetails)

    def compose(self) -> ComposeResult:
        if (session_details := self.session_details) is not None:
            self.remove_class(
                "-state-notready",
                "-state-busy",
                "-state-asking",
                "-state-idle",
                update=False,
            )
            if isinstance(session_details, SessionDetails):
                self.add_class(f"-state-{session_details.state}")
            else:
                self.add_class("-state-idle")

        yield BusyIndicator()
        # yield widgets.Rule(line_style="heavy")
        with containers.HorizontalGroup():
            yield widgets.Label("❯", classes="icon")
            with containers.VerticalGroup():
                if session_details is not None:
                    yield widgets.Label(
                        (f"✱{session_details.title}" if self.current else session_details.title),
                        classes="title",
                        markup=False,
                    )
                    yield widgets.Label(
                        session_details.subtitle,
                        classes="subtitle",
                        markup=False,
                    )
                    with containers.HorizontalGroup():
                        yield widgets.Label("📁 ")
                        yield CondensedPath(session_details.path)


if __name__ == "__main__":
    from textual.app import App

    session_details = SessionDetails(
        0,
        "mode",
        title="Building BMI calculator",
        subtitle="Claude Code",
    )

    class SessionApp(App):
        CSS_PATH = "../localscript_ui.tcss"
        CSS = """
        Screen {
            layout: horizontal;
        }
        """

        def compose(self) -> ComposeResult:
            yield SessionSummary(session_details, classes="-state-busy")
            yield SessionSummary(session_details, classes="-state-asking")
            yield SessionSummary(session_details, classes="-state-idle")

    SessionApp().run()

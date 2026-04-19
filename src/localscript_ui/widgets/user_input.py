from __future__ import annotations

from collections.abc import Iterable

from textual import containers
from textual.app import ComposeResult
from textual.widgets import Markdown

from localscript_ui.menus import MenuItem
from localscript_ui.widgets.non_selectable_label import NonSelectableLabel


class UserInput(containers.HorizontalGroup):
    def __init__(self, content: str) -> None:
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        yield NonSelectableLabel("❯", id="prompt")
        yield Markdown(self.content, id="content")

    def get_block_menu(self) -> Iterable[MenuItem]:
        yield from ()

    def get_block_content(self, destination: str) -> str | None:
        return self.content

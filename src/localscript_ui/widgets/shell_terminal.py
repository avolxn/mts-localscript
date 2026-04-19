from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from textual.content import Content
from textual.dom import DOMNode
from textual.message import Message

from localscript_ui.menus import MenuItem
from localscript_ui.widgets.terminal import Terminal


class ShellTerminal(Terminal):
    """Subclass of Terminal used in the Shell view."""

    @dataclass
    class Terminate(Message):
        teminal: ShellTerminal

        @property
        def control(self) -> DOMNode:
            return self.terminal

    @dataclass
    class Interrupt(Message):
        teminal: ShellTerminal

        @property
        def control(self) -> DOMNode:
            return self.terminal

    def get_block_menu(self) -> Iterable[MenuItem]:
        if not self.is_finalized:
            yield MenuItem("Interrupt", "interrupt", "i")
            yield MenuItem("Focus", f"focus_block({self.id!r})", "f")

    def get_block_content(self, destination: str) -> str | None:
        return "\n".join(line.content.plain for line in self.state.buffer.lines)

    def on_mount(self) -> None:
        self.border_title = Content(self.name)

from __future__ import annotations

from textual import containers, widgets
from textual.app import ComposeResult

from localscript_ui.acp.protocol import ToolCallContent


class ACPToolCallContent(containers.VerticalGroup):
    def __init__(
        self,
        content: list[ToolCallContent],
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self._content = content
        super().__init__(id=id, classes=classes)

    def compose(self) -> ComposeResult:
        for content in self._content:
            match content:
                case {
                    "type": "content",
                    "content": {
                        "type": "text",
                        "text": text,
                    },
                }:
                    yield widgets.Markdown(text)
                case {
                    "type": "diff",
                    "oldText": old_text,
                    "newText": new_text,
                    "path": path,
                }:
                    from localscript_ui.widgets.diff_view import DiffView

                    yield DiffView(path, path, old_text or "", new_text)

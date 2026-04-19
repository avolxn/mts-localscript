from __future__ import annotations

from textual.widgets import Input

from localscript_ui.directory_suggester import DirectorySuggester


class DirectoryInput(Input):
    def on_mount(self) -> None:
        self.suggester = DirectorySuggester()

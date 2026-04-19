from __future__ import annotations

from pydantic import BaseModel, Field

from localscript.tools.base import WorkspaceBoundTool
from localscript.tools.filesystem import search_workspace_text


class SearchTextArgs(BaseModel):
    pattern: str
    glob: str = "*.lua"
    limit: int = Field(default=20, ge=1)


class SearchTextTool(WorkspaceBoundTool[SearchTextArgs]):
    name = "search_text"
    title = "Search project text"
    description = "Search workspace files with Python regex matching."
    kind = "search"
    input_model = SearchTextArgs

    def execute(self, arguments: SearchTextArgs) -> dict[str, object]:
        return search_workspace_text(
            self.workspace_root,
            pattern=arguments.pattern,
            glob=arguments.glob,
            limit=arguments.limit,
        )

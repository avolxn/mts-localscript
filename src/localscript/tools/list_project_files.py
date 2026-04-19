from __future__ import annotations

from pydantic import BaseModel, Field

from localscript.tools.base import WorkspaceBoundTool
from localscript.tools.filesystem import list_workspace_paths


class ListProjectFilesArgs(BaseModel):
    pattern: str = ""
    limit: int = Field(default=50, ge=1)


class ListProjectFilesTool(WorkspaceBoundTool[ListProjectFilesArgs]):
    name = "list_project_files"
    title = "List project files"
    description = "List project files under the current workspace root."
    kind = "read"
    input_model = ListProjectFilesArgs

    def execute(self, arguments: ListProjectFilesArgs) -> dict[str, object]:
        return list_workspace_paths(self.workspace_root, pattern=arguments.pattern, limit=arguments.limit)

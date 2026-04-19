from __future__ import annotations

from pydantic import BaseModel, Field

from localscript.tools.base import WorkspaceBoundTool


class ReadTextFileArgs(BaseModel):
    path: str
    line: int = Field(default=1, ge=1)
    limit: int = Field(default=200, ge=1)


class ReadTextFileTool(WorkspaceBoundTool[ReadTextFileArgs]):
    name = "read_text_file"
    title = "Read text file"
    description = "Read a UTF-8 text file from the current workspace."
    kind = "read"
    input_model = ReadTextFileArgs

    def execute(self, arguments: ReadTextFileArgs) -> dict[str, object]:
        target = self.resolve_path(arguments.path)
        lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
        start = arguments.line - 1
        end = start + arguments.limit
        selected = lines[start:end]
        return {
            "path": self.relative_path(target),
            "line": start + 1,
            "content": "\n".join(selected),
        }

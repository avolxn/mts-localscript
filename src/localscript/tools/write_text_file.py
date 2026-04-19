from __future__ import annotations

from pydantic import BaseModel

from localscript.tools.base import WorkspaceBoundTool


class WriteTextFileArgs(BaseModel):
    path: str
    content: str


class WriteTextFileTool(WorkspaceBoundTool[WriteTextFileArgs]):
    name = "write_text_file"
    title = "Write text file"
    description = "Write a UTF-8 text file in the current workspace."
    kind = "edit"
    input_model = WriteTextFileArgs

    def execute(self, arguments: WriteTextFileArgs) -> dict[str, object]:
        target = self.resolve_path(arguments.path)
        before = ""
        if target.exists():
            before = target.read_text(encoding="utf-8", errors="ignore")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(arguments.content, encoding="utf-8")
        return {
            "path": self.relative_path(target),
            "bytes_written": len(arguments.content.encode("utf-8")),
            "replaced_existing": bool(before),
        }

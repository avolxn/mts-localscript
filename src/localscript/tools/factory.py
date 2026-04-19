from __future__ import annotations

from pathlib import Path

from localscript.tools.base import ToolExecutionReporter
from localscript.tools.executor import ToolExecutor
from localscript.tools.list_project_files import ListProjectFilesTool
from localscript.tools.mcp_tools import register_mcp_tools
from localscript.tools.read_text_file import ReadTextFileTool
from localscript.tools.registry import ToolRegistry
from localscript.tools.run_shell_command import RunShellCommandTool
from localscript.tools.search_text import SearchTextTool
from localscript.tools.write_text_file import WriteTextFileTool


def build_local_tooling(
    workspace_root: Path,
    reporter: ToolExecutionReporter | None = None,
    *,
    include_mcp: bool = False,
) -> tuple[ToolRegistry, ToolExecutor]:
    registry = ToolRegistry()
    registry.register(ListProjectFilesTool(workspace_root))
    registry.register(ReadTextFileTool(workspace_root))
    registry.register(WriteTextFileTool(workspace_root))
    registry.register(SearchTextTool(workspace_root))
    registry.register(RunShellCommandTool(workspace_root))
    if include_mcp:
        register_mcp_tools(registry, workspace_root)
    executor = ToolExecutor(registry, reporter=reporter)
    return registry, executor

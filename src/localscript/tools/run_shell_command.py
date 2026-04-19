from __future__ import annotations

import subprocess

from pydantic import BaseModel, Field

from localscript.tools.base import WorkspaceBoundTool


class RunShellCommandArgs(BaseModel):
    command: str
    timeout_seconds: int = Field(default=20, ge=1)


class RunShellCommandTool(WorkspaceBoundTool[RunShellCommandArgs]):
    name = "run_shell_command"
    title = "Run shell command"
    description = "Run a non-interactive shell command inside the current workspace root."
    kind = "execute"
    input_model = RunShellCommandArgs

    def execute(self, arguments: RunShellCommandArgs) -> dict[str, object]:
        completed = subprocess.run(
            arguments.command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            cwd=str(self.workspace_root),
            timeout=arguments.timeout_seconds,
        )
        return {
            "command": arguments.command,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "exit_code": completed.returncode,
        }

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from localscript.core.schemas import ValidationIssue, VerificationToolResult

DIAGNOSTIC_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+)\s+\[(?P<level>[A-Za-z]+)\]\s+(?P<message>.+?)\s+\((?P<code>[^()]+)\)$"
)
LUA_LSP_GLOBALS = ("wf", "_utils")


class LuaLspValidator:
    def __init__(self) -> None:
        self.command_path = self._require_command("lua-language-server")

    def verify(self, code: str) -> tuple[VerificationToolResult, tuple[ValidationIssue, ...]]:
        with tempfile.TemporaryDirectory(prefix="localscript-luals-") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            workspace_dir = temp_dir / "workspace"
            workspace_dir.mkdir()
            source_path = workspace_dir / "generated.lua"
            source_path.write_text(code, encoding="utf-8")
            config_path = temp_dir / ".luarc.json"
            config_path.write_text(json.dumps(self._config(), indent=2), encoding="utf-8")
            log_dir = temp_dir / "logs"
            log_dir.mkdir()
            command = [
                self.command_path,
                f"--configpath={config_path}",
                f"--logpath={log_dir}",
                f"--check={workspace_dir}",
                "--checklevel=Warning",
            ]
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=20,
            )
        issues = self._parse_stdout(completed.stdout)
        passed = completed.returncode == 0 and not issues
        if passed:
            summary = "LuaLS diagnostics passed."
        elif issues:
            summary = f"LuaLS reported {len(issues)} diagnostic(s)."
        else:
            summary = "LuaLS check failed without parseable diagnostics."
        return (
            VerificationToolResult(
                tool="lua_ls_check",
                passed=passed,
                summary=summary,
                stdout=completed.stdout.strip(),
                stderr=completed.stderr.strip(),
                metadata={
                    "command": command,
                    "diagnostic_count": len(issues),
                    "returncode": completed.returncode,
                },
            ),
            tuple(issues),
        )

    def _config(self) -> dict[str, object]:
        return {
            "runtime.version": "Lua 5.4",
            "workspace.checkThirdParty": False,
            "workspace.maxPreload": 64,
            "workspace.preloadFileSize": 64,
            "diagnostics.globals": list(LUA_LSP_GLOBALS),
            "telemetry.enable": False,
        }

    def _parse_stdout(self, stdout: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = DIAGNOSTIC_RE.match(line)
            if not match:
                continue
            level = match.group("level").lower()
            issues.append(
                ValidationIssue(
                    code=f"lua_ls:{match.group('code').strip()}",
                    message=(
                        f"{match.group('path')}:{match.group('line')}:{match.group('column')} "
                        f"{match.group('message').strip()}"
                    ),
                    category="semantics",
                    severity=self._severity(level),
                )
            )
        return issues

    @staticmethod
    def _severity(level: str) -> str:
        mapping = {
            "error": "error",
            "warning": "warning",
            "information": "info",
            "hint": "info",
        }
        return mapping.get(level.lower(), "warning")

    @staticmethod
    def _require_command(command: str) -> str:
        resolved = shutil.which(command)
        if not resolved:
            raise RuntimeError(f"Required command '{command}' is not installed or is not available in PATH.")
        return resolved

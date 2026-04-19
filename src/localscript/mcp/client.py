from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MCPClientError(RuntimeError):
    pass


@dataclass(slots=True)
class MCPServerConfig:
    name: str
    command: str
    args: list[str]
    env: dict[str, str]
    enabled: bool = True


class _MCPStdioSession:
    def __init__(self, server: MCPServerConfig, cwd: Path, timeout_seconds: float = 15.0) -> None:
        self.server = server
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds
        self._request_id = 0
        merged_env = os.environ.copy()
        merged_env.update(server.env)
        try:
            self.process = subprocess.Popen(
                [server.command, *server.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                cwd=str(cwd),
                env=merged_env,
            )
        except OSError as exc:
            raise MCPClientError(f"Failed to start MCP server '{server.name}': {exc}") from exc

    def close(self) -> None:
        process = self.process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)

    def __enter__(self) -> _MCPStdioSession:
        self._initialize()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _initialize(self) -> None:
        self.request(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {
                    "name": "localscript",
                    "version": "0.1.0",
                },
            },
        )
        self.notify("notifications/initialized", {})

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._request_id += 1
        request_id = self._request_id
        self._write(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        while True:
            line = self._readline()
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MCPClientError(
                    f"MCP server '{self.server.name}' returned invalid JSON on stdout: {line!r}"
                ) from exc
            if not isinstance(message, dict):
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise MCPClientError(f"MCP server '{self.server.name}' error: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                return {}
            return result

    def _write(self, payload: dict[str, Any]) -> None:
        stdin = self.process.stdin
        if stdin is None:
            raise MCPClientError(f"MCP server '{self.server.name}' stdin is unavailable.")
        stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        stdin.flush()

    def _readline(self) -> str:
        stdout = self.process.stdout
        if stdout is None:
            raise MCPClientError(f"MCP server '{self.server.name}' stdout is unavailable.")
        line = stdout.readline()
        if line:
            return line.strip()
        stderr = ""
        if self.process.stderr is not None:
            stderr = self.process.stderr.read().strip()
        raise MCPClientError(
            f"MCP server '{self.server.name}' exited before responding."
            + (f" stderr: {stderr}" if stderr else "")
        )


def _text_from_content(content: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in content:
        if item.get("type") == "text":
            parts.append(str(item.get("text", "")))
        else:
            parts.append(json.dumps(item, ensure_ascii=False))
    return "\n".join(part for part in parts if part.strip())


def list_mcp_tools(server: MCPServerConfig, *, cwd: Path) -> list[dict[str, Any]]:
    with _MCPStdioSession(server, cwd) as session:
        result = session.request("tools/list", {})
    tools = result.get("tools", [])
    if not isinstance(tools, list):
        return []
    normalized: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        normalized.append(
            {
                "name": str(tool.get("name", "")),
                "title": str(tool.get("title") or tool.get("name") or ""),
                "description": str(tool.get("description", "")),
                "inputSchema": tool.get("inputSchema", {}),
            }
        )
    return normalized


def call_mcp_tool(
    server: MCPServerConfig,
    *,
    cwd: Path,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    with _MCPStdioSession(server, cwd) as session:
        result = session.request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )
    content = result.get("content", [])
    normalized_content = content if isinstance(content, list) else []
    return {
        "server": server.name,
        "tool_name": tool_name,
        "content": normalized_content,
        "text": _text_from_content(normalized_content),
        "is_error": bool(result.get("isError", False)),
    }

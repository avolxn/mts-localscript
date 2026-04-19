from __future__ import annotations

from typing import Any

from localscript.tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool[Any]] = {}

    def register(self, tool: Tool[Any]) -> None:
        self._tools[tool.name] = tool

    def get(self, tool_name: str) -> Tool[Any]:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {tool_name}") from exc

    def has(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def list(self) -> list[Tool[Any]]:
        return list(self._tools.values())

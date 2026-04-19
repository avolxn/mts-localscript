from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel

ToolArgsT = TypeVar("ToolArgsT", bound=BaseModel)


class ToolExecutionReporter(Protocol):
    def start(
        self,
        *,
        tool_name: str,
        title: str,
        kind: str,
        arguments: dict[str, Any],
    ) -> str: ...

    def complete(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
        title: str,
        kind: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
        content: str,
    ) -> None: ...

    def fail(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
        title: str,
        kind: str,
        arguments: dict[str, Any],
        error: str,
    ) -> None: ...


class Tool(ABC, Generic[ToolArgsT]):
    name: str
    title: str
    description: str
    kind: str
    input_model: type[ToolArgsT]

    def parse_arguments(self, arguments: dict[str, Any]) -> ToolArgsT:
        return self.input_model.model_validate(arguments)

    def render_result(self, result: dict[str, Any]) -> str:
        return json.dumps(result, ensure_ascii=False, indent=2)

    def authorize(self, *, tool_call_id: str, arguments: ToolArgsT) -> None:
        return None

    @abstractmethod
    def execute(self, arguments: ToolArgsT) -> dict[str, Any]:
        raise NotImplementedError


class WorkspaceBoundTool(Tool[ToolArgsT], ABC):
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()

    def resolve_path(self, path: str) -> Path:
        target = (self.workspace_root / path).resolve()
        if self.workspace_root not in target.parents and target != self.workspace_root:
            raise ValueError(f"Path escapes workspace root: {path}")
        return target

    def relative_path(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.workspace_root))

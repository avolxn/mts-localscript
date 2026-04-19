from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from localscript.tools.base import Tool, ToolExecutionReporter
from localscript.tools.registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, reporter: ToolExecutionReporter | None = None) -> None:
        self.registry = registry
        self.reporter = reporter
        self._counter = 0
        self._bound_tools: dict[str, Callable[..., dict[str, Any]]] = {}

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self.registry.get(tool_name)
        tool_call_id = self._start(tool.name, tool.title, tool.kind, arguments)
        try:
            parsed_arguments = tool.parse_arguments(arguments)
            tool.authorize(tool_call_id=tool_call_id, arguments=parsed_arguments)
            result = tool.execute(parsed_arguments)
            self._complete(
                tool_call_id, tool.name, tool.title, tool.kind, arguments, result, tool.render_result(result)
            )
            return result
        except ValidationError as exc:
            message = exc.json()
            self._fail(tool_call_id, tool.name, tool.title, tool.kind, arguments, message)
            raise ValueError(f"Invalid arguments for tool {tool_name}.") from exc
        except Exception as exc:
            self._fail(tool_call_id, tool.name, tool.title, tool.kind, arguments, str(exc))
            raise

    def bind(self, tool_name: str) -> Callable[..., dict[str, Any]]:
        if tool_name in self._bound_tools:
            return self._bound_tools[tool_name]

        tool = self.registry.get(tool_name)

        def run_bound_tool(**kwargs: Any) -> dict[str, Any]:
            return self.execute(tool.name, kwargs)

        run_bound_tool.__name__ = tool.name
        run_bound_tool.__qualname__ = tool.name
        run_bound_tool.__doc__ = self._docstring_for(tool)
        run_bound_tool.__annotations__ = self._annotations_for(tool)
        run_bound_tool.__signature__ = self._signature_for(tool)
        self._bound_tools[tool_name] = run_bound_tool
        return run_bound_tool

    def _start(self, tool_name: str, title: str, kind: str, arguments: dict[str, Any]) -> str:
        self._counter += 1
        if self.reporter is None:
            return f"{tool_name}-{self._counter}"
        return self.reporter.start(tool_name=tool_name, title=title, kind=kind, arguments=arguments)

    def _complete(
        self,
        tool_call_id: str,
        tool_name: str,
        title: str,
        kind: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
        content: str,
    ) -> None:
        if self.reporter is None:
            return
        self.reporter.complete(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            title=title,
            kind=kind,
            arguments=arguments,
            result=result,
            content=content,
        )

    def _fail(
        self,
        tool_call_id: str,
        tool_name: str,
        title: str,
        kind: str,
        arguments: dict[str, Any],
        error: str,
    ) -> None:
        if self.reporter is None:
            return
        self.reporter.fail(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            title=title,
            kind=kind,
            arguments=arguments,
            error=error,
        )

    @staticmethod
    def _docstring_for(tool: Tool[Any]) -> str:
        lines = [tool.description, "", "Args:"]
        for name, field in tool.input_model.model_fields.items():
            description = field.description or "No description provided."
            lines.append(f"    {name}: {description}")
        return "\n".join(lines)

    @staticmethod
    def _annotations_for(tool: Tool[Any]) -> dict[str, Any]:
        annotations: dict[str, Any] = {}
        for name, field in tool.input_model.model_fields.items():
            annotations[name] = field.annotation if field.annotation is not None else Any
        annotations["return"] = dict[str, Any]
        return annotations

    @staticmethod
    def _signature_for(tool: Tool[Any]) -> inspect.Signature:
        parameters: list[inspect.Parameter] = []
        for name, field in tool.input_model.model_fields.items():
            annotation = field.annotation if field.annotation is not None else Any
            default = inspect.Parameter.empty if field.is_required() else field.default
            parameters.append(
                inspect.Parameter(
                    name=name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=annotation,
                )
            )
        return inspect.Signature(parameters=parameters, return_annotation=dict[str, Any])

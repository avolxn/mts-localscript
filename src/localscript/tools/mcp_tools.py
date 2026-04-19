from __future__ import annotations

import json
import keyword
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, create_model

from localscript.mcp import MCPServerConfig, call_mcp_tool, list_servers
from localscript.tools.base import Tool
from localscript.tools.registry import ToolRegistry

TOOL_NAME_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_]")


def register_mcp_tools(registry: ToolRegistry, workspace_root: Path) -> None:
    workspace_root = workspace_root.resolve()
    enabled_servers = [
        server for server in list_servers(workspace_root) if server.get("enabled", True) and server.get("tools")
    ]
    all_enabled_tools: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for server in enabled_servers:
        for tool in server.get("tools", []):
            if tool.get("enabled", True):
                all_enabled_tools.append((server, tool))

    duplicate_counts: dict[str, int] = {}
    for _server, tool in all_enabled_tools:
        tool_name = str(tool["name"])
        duplicate_counts[tool_name] = duplicate_counts.get(tool_name, 0) + 1

    for server, tool in all_enabled_tools:
        actual_name = str(tool["name"])
        runtime_name = actual_name
        if duplicate_counts.get(actual_name, 0) > 1:
            runtime_name = f"{_slug(server['name'])}__{_slug(actual_name)}"
        registry.register(
            MCPDynamicTool(
                workspace_root=workspace_root,
                runtime_name=runtime_name,
                server=MCPServerConfig(
                    name=server["name"],
                    command=server["command"],
                    args=list(server.get("args", [])),
                    env=dict(server.get("env", {})),
                    enabled=bool(server.get("enabled", True)),
                ),
                tool_payload=tool,
            )
        )


class MCPDynamicTool(Tool[BaseModel]):
    kind = "fetch"

    def __init__(
        self,
        *,
        workspace_root: Path,
        runtime_name: str,
        server: MCPServerConfig,
        tool_payload: dict[str, Any],
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.server = server
        self.actual_tool_name = str(tool_payload["name"])
        self.name = runtime_name
        self.title = str(tool_payload.get("title") or self.actual_tool_name)
        description = str(
            tool_payload.get("custom_description")
            or tool_payload.get("summary")
            or tool_payload.get("description", "")
        ).strip()
        if description:
            self.description = f"{description} (MCP server: {server.name})"
        else:
            self.description = f"MCP tool '{self.actual_tool_name}' from server '{server.name}'."
        self.input_model = model_from_input_schema(
            model_name=f"MCPTool_{_slug(server.name)}_{_slug(self.actual_tool_name)}_Args",
            input_schema=tool_payload.get("inputSchema", {}),
        )

    def execute(self, arguments: BaseModel) -> dict[str, object]:
        return call_mcp_tool(
            self.server,
            cwd=self.workspace_root,
            tool_name=self.actual_tool_name,
            arguments=arguments.model_dump(exclude_none=True),
        )

    def render_result(self, result: dict[str, Any]) -> str:
        text = str(result.get("text", "")).strip()
        if text:
            return text
        return json.dumps(result, ensure_ascii=False, indent=2)


def model_from_input_schema(*, model_name: str, input_schema: dict[str, Any]) -> type[BaseModel]:
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))
    if not isinstance(properties, dict):
        return create_model(model_name)

    field_definitions: dict[str, tuple[Any, Any]] = {}
    for raw_name, payload in properties.items():
        if not isinstance(payload, dict):
            payload = {}
        field_name = _python_identifier(raw_name)
        annotation = _annotation_from_schema(payload)
        description = str(payload.get("description", "")).strip() or None
        default = ... if raw_name in required else payload.get("default", None)
        field_definitions[field_name] = (annotation, Field(default=default, description=description))
    return create_model(model_name, **field_definitions)


def _annotation_from_schema(schema: dict[str, Any]) -> Any:
    schema_type = schema.get("type")
    if schema_type == "string":
        return str
    if schema_type == "integer":
        return int
    if schema_type == "number":
        return float
    if schema_type == "boolean":
        return bool
    if schema_type == "array":
        return list[Any]
    if schema_type == "object":
        return dict[str, Any]
    return Any


def _slug(value: str) -> str:
    slug = TOOL_NAME_TOKEN_RE.sub("_", value.strip())
    slug = slug.strip("_")
    return slug or "mcp"


def _python_identifier(value: str) -> str:
    identifier = _slug(value)
    if not identifier:
        identifier = "field"
    if identifier[0].isdigit():
        identifier = f"field_{identifier}"
    if keyword.iskeyword(identifier):
        identifier = f"{identifier}_value"
    return identifier

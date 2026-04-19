from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from localscript.mcp.client import MCPClientError, MCPServerConfig, list_mcp_tools


def ensure_config_dir(workspace_root: Path) -> Path:
    config_dir = workspace_root / ".localscript"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def config_path_for_workspace(workspace_root: Path) -> Path:
    return ensure_config_dir(workspace_root) / "mcp.json"


def load_config(workspace_root: Path) -> dict[str, Any]:
    path = config_path_for_workspace(workspace_root)
    if not path.exists():
        return {"servers": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    servers = payload.get("servers", [])
    if not isinstance(servers, list):
        raise ValueError("Invalid MCP config: 'servers' must be a list.")
    normalized_servers: list[dict[str, Any]] = []
    for item in servers:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        command = str(item.get("command", "")).strip()
        if not name or not command:
            continue
        args = item.get("args", [])
        env = item.get("env", {})
        normalized_servers.append(
            {
                "name": name,
                "enabled": bool(item.get("enabled", True)),
                "command": command,
                "args": [str(arg) for arg in args] if isinstance(args, list) else [],
                "env": {str(key): str(value) for key, value in env.items()} if isinstance(env, dict) else {},
                "tools": _normalize_tools(item.get("tools", [])),
            }
        )
    return {"servers": normalized_servers}


def save_config(workspace_root: Path, config: dict[str, Any]) -> Path:
    path = config_path_for_workspace(workspace_root)
    payload = {"servers": config.get("servers", [])}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def list_servers(workspace_root: Path) -> list[dict[str, Any]]:
    return list(load_config(workspace_root).get("servers", []))


def add_server(workspace_root: Path, *, name: str, command: str, args: list[str]) -> Path:
    config = load_config(workspace_root)
    servers = [server for server in config["servers"] if server["name"] != name]
    servers.append(
        {
            "name": name,
            "enabled": True,
            "command": command,
            "args": list(args),
            "env": {},
            "tools": [],
        }
    )
    config["servers"] = sorted(servers, key=lambda server: server["name"])
    save_config(workspace_root, config)
    refresh_server_tools(workspace_root, name=name)
    return config_path_for_workspace(workspace_root)


def remove_server(workspace_root: Path, *, name: str) -> Path:
    config = load_config(workspace_root)
    config["servers"] = [server for server in config["servers"] if server["name"] != name]
    return save_config(workspace_root, config)


def enable_server(workspace_root: Path, *, name: str) -> Path:
    return _set_enabled(workspace_root, name=name, enabled=True)


def disable_server(workspace_root: Path, *, name: str) -> Path:
    return _set_enabled(workspace_root, name=name, enabled=False)


def enable_tool(workspace_root: Path, *, server_name: str, tool_name: str) -> Path:
    return _set_tool_enabled(workspace_root, server_name=server_name, tool_name=tool_name, enabled=True)


def disable_tool(workspace_root: Path, *, server_name: str, tool_name: str) -> Path:
    return _set_tool_enabled(workspace_root, server_name=server_name, tool_name=tool_name, enabled=False)


def set_tool_custom_description(
    workspace_root: Path,
    *,
    server_name: str,
    tool_name: str,
    description: str,
) -> Path:
    config = load_config(workspace_root)
    for server in config["servers"]:
        if server["name"] != server_name:
            continue
        for tool in server.get("tools", []):
            if tool["name"] == tool_name:
                tool["custom_description"] = description.strip()
                return save_config(workspace_root, config)
        raise KeyError(f"{server_name}:{tool_name}")
    raise KeyError(server_name)


def clear_tool_custom_description(
    workspace_root: Path,
    *,
    server_name: str,
    tool_name: str,
) -> Path:
    config = load_config(workspace_root)
    for server in config["servers"]:
        if server["name"] != server_name:
            continue
        for tool in server.get("tools", []):
            if tool["name"] == tool_name:
                tool.pop("custom_description", None)
                return save_config(workspace_root, config)
        raise KeyError(f"{server_name}:{tool_name}")
    raise KeyError(server_name)


def refresh_server_tools(workspace_root: Path, *, name: str | None = None) -> Path:
    config = load_config(workspace_root)
    for server in config["servers"]:
        if name is not None and server["name"] != name:
            continue
        discovered = _discover_tools(
            workspace_root,
            MCPServerConfig(
                name=server["name"],
                command=server["command"],
                args=list(server.get("args", [])),
                env=dict(server.get("env", {})),
                enabled=bool(server.get("enabled", True)),
            ),
        )
        existing_states = {tool["name"]: bool(tool.get("enabled", True)) for tool in server.get("tools", [])}
        custom_descriptions = {
            tool["name"]: str(tool.get("custom_description", "")).strip()
            for tool in server.get("tools", [])
            if str(tool.get("custom_description", "")).strip()
        }
        server["tools"] = [
            {
                "name": tool["name"],
                "title": tool.get("title", tool["name"]),
                "summary": summarize_tool_description(str(tool.get("description", ""))),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema", {}),
                "enabled": existing_states.get(tool["name"], True),
                "custom_description": custom_descriptions.get(tool["name"], ""),
            }
            for tool in discovered
        ]
    return save_config(workspace_root, config)


def _set_enabled(workspace_root: Path, *, name: str, enabled: bool) -> Path:
    config = load_config(workspace_root)
    found = False
    for server in config["servers"]:
        if server["name"] == name:
            server["enabled"] = enabled
            found = True
            break
    if not found:
        raise KeyError(name)
    return save_config(workspace_root, config)


def _set_tool_enabled(
    workspace_root: Path,
    *,
    server_name: str,
    tool_name: str,
    enabled: bool,
) -> Path:
    config = load_config(workspace_root)
    for server in config["servers"]:
        if server["name"] != server_name:
            continue
        for tool in server.get("tools", []):
            if tool["name"] == tool_name:
                tool["enabled"] = enabled
                return save_config(workspace_root, config)
        raise KeyError(f"{server_name}:{tool_name}")
    raise KeyError(server_name)


def _discover_tools(workspace_root: Path, server: MCPServerConfig) -> list[dict[str, Any]]:
    try:
        return list_mcp_tools(server, cwd=workspace_root)
    except MCPClientError:
        return []


def _normalize_tools(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        normalized.append(
            {
                "name": name,
                "title": str(item.get("title", name)),
                "summary": str(item.get("summary", summarize_tool_description(str(item.get("description", ""))))),
                "description": str(item.get("description", "")),
                "inputSchema": item.get("inputSchema", {}) if isinstance(item.get("inputSchema", {}), dict) else {},
                "enabled": bool(item.get("enabled", True)),
                "custom_description": str(item.get("custom_description", "")).strip(),
            }
        )
    return normalized


def summarize_tool_description(description: str, *, max_length: int = 160) -> str:
    text = " ".join(part.strip() for part in description.splitlines() if part.strip())
    if not text:
        return ""
    first_sentence = text
    for sentence_delimiter in (". ", "!\n", "?\n", "!\r", "?\r"):
        if sentence_delimiter in first_sentence:
            first_sentence = first_sentence.split(sentence_delimiter, 1)[0].strip()
            if sentence_delimiter.startswith("."):
                first_sentence += "."
            break
    for delimiter in (". ", "\n", " IMPORTANT", " You MUST", " Each result includes:"):
        if delimiter in text:
            text = text.split(delimiter, 1)[0].strip()
            break
    if len(first_sentence) < len(text) or text == first_sentence.rstrip("."):
        text = first_sentence
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"

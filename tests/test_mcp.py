from __future__ import annotations

from pathlib import Path

import localscript.mcp.config as mcp_config
from localscript.mcp.config import (
    add_server,
    clear_tool_custom_description,
    config_path_for_workspace,
    disable_server,
    disable_tool,
    enable_server,
    enable_tool,
    list_servers,
    load_config,
    refresh_server_tools,
    remove_server,
    set_tool_custom_description,
    summarize_tool_description,
)
from localscript.tools import build_local_tooling


def test_mcp_config_roundtrip(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        mcp_config,
        "list_mcp_tools",
        lambda server, *, cwd: [
            {
                "name": "search_issues",
                "title": "Search Issues",
                "description": "Search repository issues",
                "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
            {
                "name": "create_issue",
                "title": "Create Issue",
                "description": "Create a repository issue",
                "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}}},
            },
        ],
    )
    add_server(
        tmp_path,
        name="github",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
    )
    config_path = config_path_for_workspace(tmp_path)
    assert config_path.exists()
    servers = list_servers(tmp_path)
    assert servers == [
        {
            "name": "github",
            "enabled": True,
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {},
            "tools": [
                {
                    "name": "search_issues",
                    "title": "Search Issues",
                    "summary": "Search repository issues",
                    "description": "Search repository issues",
                    "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
                    "enabled": True,
                    "custom_description": "",
                },
                {
                    "name": "create_issue",
                    "title": "Create Issue",
                    "summary": "Create a repository issue",
                    "description": "Create a repository issue",
                    "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}}},
                    "enabled": True,
                    "custom_description": "",
                },
            ],
        }
    ]

    disable_server(tmp_path, name="github")
    assert load_config(tmp_path)["servers"][0]["enabled"] is False

    enable_server(tmp_path, name="github")
    assert load_config(tmp_path)["servers"][0]["enabled"] is True

    disable_tool(tmp_path, server_name="github", tool_name="create_issue")
    assert load_config(tmp_path)["servers"][0]["tools"][1]["enabled"] is False

    enable_tool(tmp_path, server_name="github", tool_name="create_issue")
    assert load_config(tmp_path)["servers"][0]["tools"][1]["enabled"] is True

    set_tool_custom_description(
        tmp_path,
        server_name="github",
        tool_name="create_issue",
        description="Create a GitHub issue in the current repository.",
    )
    assert load_config(tmp_path)["servers"][0]["tools"][1]["custom_description"] == (
        "Create a GitHub issue in the current repository."
    )

    clear_tool_custom_description(tmp_path, server_name="github", tool_name="create_issue")
    assert load_config(tmp_path)["servers"][0]["tools"][1]["custom_description"] == ""

    refresh_server_tools(tmp_path, name="github")
    assert len(load_config(tmp_path)["servers"][0]["tools"]) == 2

    remove_server(tmp_path, name="github")
    assert list_servers(tmp_path) == []


def test_local_tooling_registers_enabled_mcp_tools(monkeypatch, tmp_path: Path) -> None:
    add_server(tmp_path, name="demo", command="demo-mcp", args=["serve"])
    import localscript.mcp.config as mcp_config_module
    import localscript.tools.mcp_tools as mcp_tools_module

    monkeypatch.setattr(
        mcp_config_module,
        "list_mcp_tools",
        lambda server, *, cwd: [
            {
                "name": "demo_tool",
                "title": "Demo Tool",
                "description": "Demo description",
                "inputSchema": {"type": "object", "properties": {"value": {"type": "integer"}}},
            }
        ],
    )
    refresh_server_tools(tmp_path, name="demo")
    monkeypatch.setattr(
        mcp_tools_module,
        "call_mcp_tool",
        lambda server, *, cwd, tool_name, arguments: {
            "server": server.name,
            "tool_name": tool_name,
            "content": [{"type": "text", "text": "ok"}],
            "text": "ok",
            "is_error": False,
        },
    )
    _registry, executor = build_local_tooling(tmp_path, include_mcp=True)

    called = executor.execute("demo_tool", {"value": 1})
    assert called["text"] == "ok"

    set_tool_custom_description(
        tmp_path,
        server_name="demo",
        tool_name="demo_tool",
        description="Custom demo MCP tool.",
    )
    _registry, _executor = build_local_tooling(tmp_path, include_mcp=True)
    assert _registry.get("demo_tool").description == "Custom demo MCP tool. (MCP server: demo)"

    disable_tool(tmp_path, server_name="demo", tool_name="demo_tool")
    _registry, _executor = build_local_tooling(tmp_path, include_mcp=True)
    assert not _registry.has("demo_tool")


def test_mcp_tool_description_is_summarized() -> None:
    description = (
        "Resolves a package/product name to a Context7-compatible library ID and returns matching libraries.\n\n"
        "You MUST call this function before query-docs. IMPORTANT: do not call more than 3 times."
    )
    summary = summarize_tool_description(description)
    assert summary == "Resolves a package/product name to a Context7-compatible library ID and returns matching libraries."

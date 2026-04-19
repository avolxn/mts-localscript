from __future__ import annotations

import asyncio
import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from localscript.core import Settings
from localscript.core.schemas import SessionRecord
from localscript.modes import GeneralMode, LuaCodegenMode, build_general_mode, build_lua_codegen_mode
from localscript.tools import ToolExecutionReporter, build_local_tooling
from localscript_ui import jsonrpc
from localscript_ui.acp import protocol
from localscript_ui.agent_schema import Agent as AgentData

MODE_GENERAL = "general"
MODE_LUA_CODEGEN = "lua_codegen"


def build_agent_definition(command: str | None = None) -> AgentData:
    resolved_command = command or f"{sys.executable} -m localscript acp"
    return {
        "identity": "localscript.localhost",
        "name": "LocalScript",
        "short_name": "localscript",
        "url": "https://github.com/",
        "protocol": "acp",
        "type": "coding",
        "author_name": "avolxn",
        "author_url": "",
        "publisher_name": "LocalScript",
        "publisher_url": "",
        "description": (
            "Local ACP backend for LocalScript. "
            "Includes a general workspace agent mode and the Lua multi-agent codegen mode."
        ),
        "tags": ["local", "lua", "multi-agent"],
        "help": (
            "Modes:\n"
            "- `general`: project-aware coding/chat mode with local tools.\n"
            "- `lua_codegen`: LocalScript multi-agent Lua generation pipeline.\n"
        ),
        "welcome": (
            "Switch modes with `Ctrl+O`, by clicking the mode label in the bottom bar, "
            "or with `/mode general` and `/mode lua_codegen`."
        ),
        "run_command": {"*": resolved_command},
        "actions": {},
    }


@dataclass(slots=True)
class ACPState:
    session_id: str
    cwd: Path
    current_mode_id: str = MODE_GENERAL
    general_session_id: str | None = None
    codegen_session_id: str | None = None
    codegen_step_index: int = 0


class ACPToolReporter(ToolExecutionReporter):
    def __init__(self, backend: LocalScriptACPBackend, session_id: str) -> None:
        self.backend = backend
        self.session_id = session_id
        self._counter = 0

    def start(
        self,
        *,
        tool_name: str,
        title: str,
        kind: str,
        arguments: dict[str, Any],
    ) -> str:
        self._counter += 1
        tool_call_id = f"{tool_name}-{self._counter}"
        self.backend.notify(
            self.session_id,
            {
                "sessionUpdate": "tool_call",
                "toolCallId": tool_call_id,
                "title": title,
                "kind": kind,
                "status": "in_progress",
                "rawInput": arguments,
            },
        )
        return tool_call_id

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
    ) -> None:
        self.backend.notify(
            self.session_id,
            {
                "sessionUpdate": "tool_call_update",
                "toolCallId": tool_call_id,
                "title": title,
                "kind": kind,
                "status": "completed",
                "rawInput": arguments,
                "rawOutput": result,
                "content": [self.backend.text_tool_content(content)],
            },
        )

    def fail(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
        title: str,
        kind: str,
        arguments: dict[str, Any],
        error: str,
    ) -> None:
        self.backend.notify(
            self.session_id,
            {
                "sessionUpdate": "tool_call_update",
                "toolCallId": tool_call_id,
                "title": title,
                "kind": kind,
                "status": "failed",
                "rawInput": arguments,
                "content": [self.backend.text_tool_content(error)],
            },
        )


class LocalScriptACPBackend:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        general_mode: GeneralMode | None = None,
        codegen_mode: LuaCodegenMode | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.general_mode = general_mode or build_general_mode(self.settings)
        self.codegen_mode = codegen_mode or build_lua_codegen_mode(self.settings)
        self.server = jsonrpc.Server()
        self.server.expose_instance(self)
        self._sessions: dict[str, ACPState] = {}
        self._write_lock = asyncio.Lock()
        self._session_lock = asyncio.Lock()

    @staticmethod
    def available_modes() -> list[protocol.SessionMode]:
        return [
            {
                "id": MODE_GENERAL,
                "name": "General",
                "description": "Project-aware assistant with local file and shell tools.",
            },
            {
                "id": MODE_LUA_CODEGEN,
                "name": "Lua Codegen",
                "description": "LocalScript multi-agent Lua generation pipeline.",
            },
        ]

    def modes_state(self, current_mode_id: str) -> protocol.SessionModeState:
        return {
            "currentModeId": current_mode_id,
            "availableModes": self.available_modes(),
        }

    def models_state(self) -> protocol.SessionModelState:
        return {
            "currentModelId": self.settings.model,
            "availableModels": [
                {
                    "modelId": self.settings.model,
                    "name": self.settings.model,
                    "description": "Configured LocalScript Ollama model.",
                }
            ],
        }

    def notify(self, session_id: str, update: protocol.SessionUpdate) -> None:
        asyncio.create_task(self._write_json({"jsonrpc": "2.0", "method": "session/update", "params": {"sessionId": session_id, "update": update}}))

    def notify_available_commands(self, session_id: str) -> None:
        self.notify(
            session_id,
            {
                "sessionUpdate": "available_commands_update",
                "availableCommands": [
                    {
                        "name": "mode",
                        "description": "Switch agent mode",
                        "input": {"hint": "<general|lua_codegen>"},
                    }
                ],
            },
        )

    @staticmethod
    def text_content(text: str) -> protocol.TextContent:
        return {"type": "text", "text": text}

    def text_tool_content(self, text: str) -> protocol.ToolCallContentContent:
        return {"type": "content", "content": self.text_content(text)}

    async def _write_json(self, payload: dict[str, Any]) -> None:
        async with self._write_lock:
            print(json.dumps(payload, ensure_ascii=False), flush=True)

    @staticmethod
    def _prompt_to_text(prompt: list[protocol.ContentBlock]) -> str:
        parts: list[str] = []
        for block in prompt:
            match block:
                case {"type": "text", "text": text}:
                    parts.append(str(text))
                case {"type": "resource", "resource": {"uri": uri, "text": text}}:
                    parts.append(f"\n[resource: {uri}]\n{text}")
        return "\n\n".join(part for part in parts if part.strip()).strip()

    def _get_session(self, session_id: str) -> ACPState:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise jsonrpc.JSONRPCError(f"Unknown session: {session_id}") from exc

    @jsonrpc.expose("initialize")
    def initialize(
        self,
        protocolVersion: int,
        clientCapabilities: protocol.ClientCapabilities,
        clientInfo: protocol.Implementation,
    ) -> protocol.InitializeResponse:
        return {
            "protocolVersion": protocolVersion,
            "agentCapabilities": {
                "loadSession": False,
                "promptCapabilities": {
                    "audio": False,
                    "embeddedContent": True,
                    "image": False,
                },
            },
            "authMethods": [],
        }

    @jsonrpc.expose("session/new")
    def session_new(self, cwd: str, mcpServers: list[protocol.McpServer]) -> protocol.NewSessionResponse:
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = ACPState(session_id=session_id, cwd=Path(cwd).expanduser().resolve())
        self.notify_available_commands(session_id)
        return {
            "sessionId": session_id,
            "modes": self.modes_state(MODE_GENERAL),
            "models": self.models_state(),
        }

    @jsonrpc.expose("session/load")
    def session_load(self, cwd: str, mcpServers: list[protocol.McpServer], sessionId: str) -> protocol.LoadSessionResponse:
        session = self._get_session(sessionId)
        session.cwd = Path(cwd).expanduser().resolve()
        self.notify_available_commands(sessionId)
        return {"modes": self.modes_state(session.current_mode_id)}

    @jsonrpc.expose("session/set_mode")
    def session_set_mode(self, sessionId: str, modeId: str) -> protocol.SetSessionModeResponse:
        session = self._get_session(sessionId)
        if modeId not in {MODE_GENERAL, MODE_LUA_CODEGEN}:
            raise jsonrpc.JSONRPCError(f"Unknown mode: {modeId}")
        session.current_mode_id = modeId
        self.notify(sessionId, {"sessionUpdate": "current_mode_update", "currentModeId": modeId})
        self.notify_available_commands(sessionId)
        return {}

    async def _run_general_mode(self, session: ACPState, prompt_text: str) -> str:
        reporter = ACPToolReporter(self, session.session_id)
        registry, executor = build_local_tooling(session.cwd, reporter=reporter, include_mcp=True)
        result = await self.general_mode.run_async(
            localscript_session_id=session.general_session_id,
            prompt_text=prompt_text,
            tool_registry=registry,
            tool_executor=executor,
        )
        session.general_session_id = result.localscript_session_id
        return result.assistant_message.strip()

    def _codegen_plan(self, state: str) -> protocol.Plan:
        entries: list[protocol.PlanEntry] = [
            {"content": "Translate and clarify the request", "status": "completed" if state != "running" else "in_progress"},
            {"content": "Build local context and constraints", "status": "completed" if state == "done" else "pending"},
            {"content": "Draft, review, repair, and validate Lua", "status": "completed" if state == "done" else "pending"},
        ]
        if state == "running":
            entries[1]["status"] = "pending"
            entries[2]["status"] = "pending"
        return {"sessionUpdate": "plan", "entries": entries}

    @staticmethod
    def _codegen_step_for_stage(stage_name: str) -> int:
        if stage_name.startswith("clarifier"):
            return 0
        if stage_name in {"kb_search", "context_agent"}:
            return 1
        return 2

    def _notify_codegen_progress(self, session: ACPState, stage_name: str, event: str) -> None:
        step_index = self._codegen_step_for_stage(stage_name)
        if event == "completed":
            session.codegen_step_index = max(session.codegen_step_index, step_index + 1)
            return

        session.codegen_step_index = max(session.codegen_step_index, step_index)
        step_statuses = ["pending", "pending", "pending"]
        for index in range(min(session.codegen_step_index, len(step_statuses))):
            step_statuses[index] = "completed"
        if step_index < len(step_statuses):
            step_statuses[step_index] = "in_progress"

        entries: list[protocol.PlanEntry] = [
            {"content": "Translate and clarify the request", "status": step_statuses[0]},
            {"content": "Build local context and constraints", "status": step_statuses[1]},
            {"content": "Draft, review, repair, and validate Lua", "status": step_statuses[2]},
        ]
        self.notify(session.session_id, {"sessionUpdate": "plan", "entries": entries})

    @staticmethod
    def _format_codegen_result(result: SessionRecord) -> str:
        parts: list[str] = []
        if result.execution_brief and result.status != "waiting_for_clarification":
            parts.append(f"Execution brief:\n{result.execution_brief.strip()}")
        if result.latest_summary:
            parts.append(result.latest_summary.strip())
        if result.latest_code:
            parts.append(f"```lua\n{result.latest_code.rstrip()}\n```")
        return "\n\n".join(part for part in parts if part).strip()

    async def _run_codegen_mode(self, session: ACPState, prompt_text: str) -> str:
        session.codegen_step_index = 0
        self.notify(session.session_id, self._codegen_plan("running"))
        if session.codegen_session_id is None:
            result = await self.codegen_mode.start_session_async(
                prompt_text,
                interactive=True,
                workspace_root=session.cwd,
                progress_callback=lambda stage_name, event: self._notify_codegen_progress(session, stage_name, event),
            )
            session.codegen_session_id = result.session_id
            if result.status == "waiting_for_clarification":
                return result.clarification_question or "Clarification required."
        else:
            result = await self.codegen_mode.reply_to_session_async(
                session.codegen_session_id,
                prompt_text,
                workspace_root=session.cwd,
                progress_callback=lambda stage_name, event: self._notify_codegen_progress(session, stage_name, event),
            )
        self.notify(session.session_id, self._codegen_plan("done"))
        session.codegen_step_index = 3
        return self._format_codegen_result(result)

    @jsonrpc.expose("session/prompt")
    async def session_prompt(
        self,
        prompt: list[protocol.ContentBlock],
        sessionId: str,
    ) -> protocol.SessionPromptResponse:
        session = self._get_session(sessionId)
        prompt_text = self._prompt_to_text(prompt)
        if not prompt_text:
            raise jsonrpc.JSONRPCError("Prompt is empty.")

        if prompt_text.startswith("/mode "):
            requested_mode = prompt_text.partition(" ")[2].strip()
            if requested_mode not in {MODE_GENERAL, MODE_LUA_CODEGEN}:
                self.notify(
                    sessionId,
                    {
                        "sessionUpdate": "agent_message_chunk",
                        "content": self.text_content("Unknown mode. Use `/mode general` or `/mode lua_codegen`."),
                    },
                )
                return {"stopReason": "end_turn"}
            self.session_set_mode(sessionId, requested_mode)
            self.notify(
                sessionId,
                {
                    "sessionUpdate": "agent_message_chunk",
                    "content": self.text_content(f"Mode changed to `{requested_mode}`."),
                },
            )
            return {"stopReason": "end_turn"}

        async with self._session_lock:
            if session.current_mode_id == MODE_LUA_CODEGEN:
                self.notify(
                    sessionId,
                    {
                        "sessionUpdate": "agent_thought_chunk",
                        "content": self.text_content("Running LocalScript multi-agent Lua pipeline."),
                    },
                )
                response_text = await self._run_codegen_mode(session, prompt_text)
            else:
                self.notify(
                    sessionId,
                    {
                        "sessionUpdate": "agent_thought_chunk",
                        "content": self.text_content("Running general project mode with local tools."),
                    },
                )
                response_text = await self._run_general_mode(session, prompt_text)

        if response_text:
            self.notify(
                sessionId,
                {
                    "sessionUpdate": "agent_message_chunk",
                    "content": self.text_content(response_text),
                },
            )
        return {"stopReason": "end_turn"}

    async def serve_forever(self) -> None:
        while True:
            line = await asyncio.to_thread(sys.stdin.buffer.readline)
            if not line:
                return
            line = line.strip()
            if not line:
                continue
            request = json.loads(line.decode("utf-8"))
            response = await self.server.call(request)
            if response is not None:
                await self._write_json(response)


def main() -> None:
    asyncio.run(LocalScriptACPBackend().serve_forever())

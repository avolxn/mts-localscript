from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from textwrap import dedent
from typing import Any

from localscript.agents.interface import BaseAgent
from localscript.tools import ToolExecutor, ToolRegistry


@dataclass(slots=True)
class GeneralAgentResult:
    assistant_message: str
    emitted_messages: list[dict[str, Any]]


class GeneralAgent(BaseAgent[GeneralAgentResult]):
    name = "general"
    response_model = None
    system = (
        "You are the GeneralAgent in LocalScript. "
        "You operate as a ReAct-style local assistant: inspect the workspace when needed, "
        "use available tools precisely, and then answer the user directly. "
        "Do not invent file contents or command outputs when tools can verify them. "
        "Keep the final answer concrete and actionable. "
        "Always respond in natural language - plain text, not JSON or structured formats. "
        "Be direct, concise, and conversational."
    )

    def run(
        self,
        messages: list[dict[str, Any]],
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
    ) -> GeneralAgentResult:
        final_response, emitted_messages = self._tool_loop(
            messages,
            tool_registry,
            tool_executor,
        )
        return GeneralAgentResult(
            assistant_message=final_response,
            emitted_messages=emitted_messages,
        )

    async def run_async(
        self,
        messages: list[dict[str, Any]],
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
    ) -> GeneralAgentResult:
        final_response, emitted_messages = await self._tool_loop_async(
            messages,
            tool_registry,
            tool_executor,
        )
        return GeneralAgentResult(
            assistant_message=final_response,
            emitted_messages=emitted_messages,
        )

    def _tool_loop(
        self,
        messages: list[dict[str, Any]],
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
    ) -> tuple[str, list[dict[str, Any]]]:
        tools = self._bind_tools(tool_registry, tool_executor)
        available = {tool.__name__: tool for tool in tools}
        active_messages = list(messages)
        emitted_messages: list[dict[str, Any]] = []
        response = self.client.chat(messages=active_messages, tools=tools)
        for _ in range(8):
            if not response.message.tool_calls:
                break
            assistant_message = response.message.model_dump()
            emitted_messages.append(dict(assistant_message))
            active_messages.append(assistant_message)
            for tool_call in response.message.tool_calls:
                function = available[tool_call.function.name]
                result = function(**tool_call.function.arguments)
                tool_message = {
                    "role": "tool",
                    "tool_name": tool_call.function.name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
                emitted_messages.append(dict(tool_message))
                active_messages.append(tool_message)
            response = self.client.chat(messages=active_messages, tools=tools)
        final_message = response.message.model_dump()
        emitted_messages.append(dict(final_message))
        return str(response.message.content).strip(), emitted_messages

    async def _tool_loop_async(
        self,
        messages: list[dict[str, Any]],
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
    ) -> tuple[str, list[dict[str, Any]]]:
        tools = self._bind_tools(tool_registry, tool_executor)
        available = {tool.__name__: tool for tool in tools}
        active_messages = list(messages)
        emitted_messages: list[dict[str, Any]] = []
        response = await self.client.chat_async(messages=active_messages, tools=tools)
        for _ in range(8):
            if not response.message.tool_calls:
                break
            assistant_message = response.message.model_dump()
            emitted_messages.append(dict(assistant_message))
            active_messages.append(assistant_message)
            for tool_call in response.message.tool_calls:
                function = available[tool_call.function.name]
                result = await asyncio.to_thread(function, **tool_call.function.arguments)
                tool_message = {
                    "role": "tool",
                    "tool_name": tool_call.function.name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
                emitted_messages.append(dict(tool_message))
                active_messages.append(tool_message)
            response = await self.client.chat_async(messages=active_messages, tools=tools)
        final_message = response.message.model_dump()
        emitted_messages.append(dict(final_message))
        return str(response.message.content).strip(), emitted_messages

    @staticmethod
    def _bind_tools(tool_registry: ToolRegistry, tool_executor: ToolExecutor) -> list[Any]:
        preferred_order = (
            "list_project_files",
            "read_text_file",
            "search_text",
            "write_text_file",
            "run_shell_command",
        )
        ordered_names = [tool_name for tool_name in preferred_order if tool_registry.has(tool_name)]
        for tool in tool_registry.list():
            if tool.name not in ordered_names:
                ordered_names.append(tool.name)
        return [tool_executor.bind(tool_name) for tool_name in ordered_names]

    def _system_prompt(self) -> str:
        return dedent(
            """
            You are a general-purpose local engineering agent running inside LocalScript.
            Use available tools precisely and answer the user directly.
            """
        ).strip()

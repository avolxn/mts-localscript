from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from localscript.agents import GeneralAgent, GeneralAgentResult, TranslatorAgent
from localscript.core.knowledge import KnowledgeBase
from localscript.core.language import detect_language
from localscript.core.settings import Settings
from localscript.ollama import OllamaClient
from localscript.storage import LocalKnowledgeBase, SQLiteStore
from localscript.tools import ToolExecutor, ToolRegistry


@dataclass(slots=True)
class GeneralModeResult:
    localscript_session_id: str
    assistant_message: str


@dataclass(slots=True)
class GeneralModeRuntime:
    settings: Settings
    store: SQLiteStore
    kb: LocalKnowledgeBase
    ollama: OllamaClient
    translator: TranslatorAgent
    general_agent: GeneralAgent
    dataset: KnowledgeBase


class GeneralMode:
    def __init__(self, runtime: GeneralModeRuntime) -> None:
        self.runtime = runtime

    async def run_async(
        self,
        *,
        localscript_session_id: str | None,
        prompt_text: str,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
    ) -> GeneralModeResult:
        resolved_session_id = self._ensure_session(localscript_session_id, prompt_text)
        existing_messages = self.runtime.store.list_messages(resolved_session_id)
        self.runtime.store.append_message(
            resolved_session_id,
            role="user",
            kind="message" if existing_messages else "prompt",
            content=prompt_text,
        )
        session_messages = self.runtime.store.list_messages(resolved_session_id)
        source_language = detect_language(prompt_text)
        prompt_for_model = prompt_text
        if source_language not in {"en", "unknown"}:
            translation = await self.runtime.translator.run_async(
                prompt_text, source_language
            )
            prompt_for_model = translation.translated_text

        llm_messages = self._build_llm_messages(
            session_messages,
            translated_user_text=prompt_for_model if prompt_for_model != prompt_text else None,
        )
        agent_result = await self.runtime.general_agent.run_async(
            llm_messages,
            tool_registry,
            tool_executor,
        )
        self._persist_agent_messages(resolved_session_id, agent_result)
        self.runtime.store.update_session(
            resolved_session_id,
            status="complete",
            latest_summary=agent_result.assistant_message.strip()[:400] or "General task completed.",
        )
        return GeneralModeResult(
            localscript_session_id=resolved_session_id,
            assistant_message=agent_result.assistant_message,
        )

    def _ensure_session(self, localscript_session_id: str | None, prompt_text: str) -> str:
        if localscript_session_id is not None:
            return localscript_session_id
        created = self.runtime.store.create_session(prompt_text, status="created")
        return created.session_id

    def _build_llm_messages(
        self,
        session_messages: list[dict[str, Any]],
        *,
        translated_user_text: str | None = None,
    ) -> list[dict[str, Any]]:
        llm_messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.runtime.general_agent._system_prompt()}
        ]
        last_user_message_id = None
        if translated_user_text is not None:
            for message in reversed(session_messages):
                if message["role"] == "user":
                    last_user_message_id = message["message_id"]
                    break
        for message in session_messages:
            mapped = self._map_store_message_to_llm(message)
            if mapped is None:
                continue
            if translated_user_text is not None and message["message_id"] == last_user_message_id and mapped["role"] == "user":
                mapped = {**mapped, "content": translated_user_text}
            llm_messages.append(mapped)
        return llm_messages

    @staticmethod
    def _map_store_message_to_llm(message: dict[str, Any]) -> dict[str, Any] | None:
        role = str(message["role"])
        kind = str(message["kind"])
        content = str(message["content"])
        if role == "tool" and kind == "tool_result":
            payload = json.loads(content)
            return {
                "role": "tool",
                "tool_name": payload["tool_name"],
                "content": json.dumps(payload["result"], ensure_ascii=False),
            }
        if role == "assistant" and kind == "tool_call":
            return json.loads(content)
        if role in {"user", "assistant"}:
            return {"role": role, "content": content}
        return None

    def _persist_agent_messages(self, session_id: str, result: GeneralAgentResult) -> None:
        for message in result.emitted_messages:
            role = str(message.get("role", "assistant"))
            if role == "tool":
                self.runtime.store.append_message(
                    session_id,
                    role="tool",
                    kind="tool_result",
                    content=json.dumps(
                        {
                            "tool_name": message.get("tool_name", ""),
                            "result": json.loads(str(message.get("content", "{}"))),
                        },
                        ensure_ascii=False,
                    ),
                )
                continue
            if message.get("tool_calls"):
                self.runtime.store.append_message(
                    session_id,
                    role="assistant",
                    kind="tool_call",
                    content=json.dumps(message, ensure_ascii=False),
                )
                continue
            self.runtime.store.append_message(
                session_id,
                role="assistant",
                kind="message",
                content=str(message.get("content", "")).strip(),
            )


def build_general_mode(settings: Settings) -> GeneralMode:
    settings.validate_runtime()
    store = SQLiteStore(settings.database_path)
    kb = LocalKnowledgeBase(settings.data_dir, store)
    kb.rebuild()
    ollama = OllamaClient(settings)
    runtime = GeneralModeRuntime(
        settings=settings,
        store=store,
        kb=kb,
        ollama=ollama,
        translator=TranslatorAgent(ollama),
        general_agent=GeneralAgent(ollama),
        dataset=KnowledgeBase.from_files(
            Path(settings.data_dir) / "localscript_rules.md",
            Path(settings.data_dir) / "public_localscript_dataset.md",
        ),
    )
    return GeneralMode(runtime)

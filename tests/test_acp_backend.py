from __future__ import annotations

import asyncio

from localscript.acp import build_agent_definition
from localscript.acp.backend import MODE_GENERAL, MODE_LUA_CODEGEN, LocalScriptACPBackend
from localscript.core.schemas import SessionRecord, now_iso
from localscript.core.settings import Settings
from localscript.modes.general import GeneralModeResult


class FakeGeneralMode:
    async def run_async(self, *, localscript_session_id, prompt_text, tool_registry, tool_executor):
        return GeneralModeResult(
            localscript_session_id=localscript_session_id or "general-session",
            assistant_message=f"general:{prompt_text}",
        )


class FakeCodegenMode:
    async def start_session_async(self, prompt, *, interactive, workspace_root, progress_callback=None):
        if progress_callback is not None:
            progress_callback("clarifier", "started")
        return SessionRecord(
            session_id="codegen-session",
            status="waiting_for_clarification",
            prompt=prompt,
            clarification_question="Need one detail?",
            execution_brief=None,
            latest_code=None,
            latest_summary="Waiting for clarification.",
            created_at=now_iso(),
            updated_at=now_iso(),
        )

    async def reply_to_session_async(self, session_id, content, *, workspace_root, progress_callback=None):
        if progress_callback is not None:
            progress_callback("clarifier_followup", "started")
            progress_callback("clarifier_followup", "completed")
            progress_callback("kb_search", "started")
            progress_callback("kb_search", "completed")
            progress_callback("coder_1", "started")
        return SessionRecord(
            session_id=session_id,
            status="complete",
            prompt="prompt",
            clarification_question=None,
            execution_brief="Use the confirmed detail and generate Lua.",
            latest_code=f"return {content!r}",
            latest_summary="Generated code passed validation.",
            created_at=now_iso(),
            updated_at=now_iso(),
        )


def test_backend_exposes_modes_and_routes_prompts(monkeypatch) -> None:
    async def run() -> None:
        backend = LocalScriptACPBackend(
            Settings(),
            general_mode=FakeGeneralMode(),
            codegen_mode=FakeCodegenMode(),
        )
        updates = []
        monkeypatch.setattr(backend, "notify", lambda session_id, update: updates.append((session_id, update)))

        session = backend.session_new(".", [])
        session_id = session["sessionId"]

        general_response = await backend.session_prompt([{"type": "text", "text": "hello"}], session_id)
        assert general_response == {"stopReason": "end_turn"}
        assert updates[-1][1]["content"]["text"] == "general:hello"

        backend.session_set_mode(session_id, MODE_LUA_CODEGEN)
        clarification_response = await backend.session_prompt([{"type": "text", "text": "build lua"}], session_id)
        assert clarification_response == {"stopReason": "end_turn"}
        assert updates[-1][1]["content"]["text"] == "Need one detail?"

        final_response = await backend.session_prompt([{"type": "text", "text": "42"}], session_id)
        assert final_response == {"stopReason": "end_turn"}
        plan_updates = [update for _, update in updates if update["sessionUpdate"] == "plan"]
        assert any(entry["status"] == "in_progress" for update in plan_updates for entry in update["entries"])
        assert any(
            [entry["status"] for entry in update["entries"]] == ["completed", "in_progress", "pending"]
            for update in plan_updates
        )
        assert any(
            [entry["status"] for entry in update["entries"]] == ["completed", "completed", "in_progress"]
            for update in plan_updates
        )
        assert "Execution brief:" in updates[-1][1]["content"]["text"]
        assert "Use the confirmed detail and generate Lua." in updates[-1][1]["content"]["text"]
        assert "```lua" in updates[-1][1]["content"]["text"]

    asyncio.run(run())


def test_build_agent_definition_points_to_localscript_acp() -> None:
    agent = build_agent_definition()
    assert agent["identity"] == "localscript.localhost"
    assert "localscript acp" in agent["run_command"]["*"]
    assert MODE_GENERAL != MODE_LUA_CODEGEN

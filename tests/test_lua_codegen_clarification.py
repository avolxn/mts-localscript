from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from localscript.core.schemas import ClarifierDecision, TranslationDecision
from localscript.modes.lua_codegen import LuaCodegenMode
from localscript.storage.sqlite import SQLiteStore


class SequenceClarifier:
    def __init__(self, decisions: list[ClarifierDecision]) -> None:
        self._decisions = list(decisions)

    def run(self, prompt: str, history: list[dict[str, object]]) -> ClarifierDecision:
        assert prompt
        assert history
        return self._decisions.pop(0)


def test_waiting_clarification_reasks_until_execution_brief_is_ready(monkeypatch, tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "localscript.db")
    session = store.create_session("Build a factorial helper", status="waiting_for_clarification")
    store.append_message(session.session_id, role="user", kind="prompt", content=session.prompt)
    store.append_message(session.session_id, role="assistant", kind="clarification", content="What should the input type be?")
    store.update_session(
        session.session_id,
        clarification_question="What should the input type be?",
        execution_brief=None,
        latest_summary="Waiting for clarification.",
    )

    mode = LuaCodegenMode(
        SimpleNamespace(
            store=store,
            clarifier=SequenceClarifier(
                [
                    ClarifierDecision(
                        need_clarification=True,
                        questions=("What should the input type be?",),
                        execution_brief="",
                    ),
                    ClarifierDecision(
                        need_clarification=False,
                        questions=(),
                        execution_brief="Implement a Lua factorial helper for non-negative integer input n.",
                    ),
                ]
            ),
        )
    )

    monkeypatch.setattr(
        mode,
        "_translate_user_text",
        lambda session_id, text, *, kind: TranslationDecision(
            source_language="en",
            target_language="en",
            translated_text=text,
        ),
    )

    executed: list[str] = []

    def fake_execute_session(session_id: str, *, clarification, **kwargs):
        executed.append(clarification.execution_brief)
        store.update_session(
            session_id,
            status="complete",
            clarification_question=None,
            execution_brief=clarification.execution_brief,
            latest_summary="Complete.",
        )
        return SimpleNamespace(final_code="return 42")

    monkeypatch.setattr(mode, "_execute_session", fake_execute_session)

    unresolved = mode.reply_to_session(session.session_id, "just do the usual thing")
    assert unresolved.status == "waiting_for_clarification"
    assert unresolved.execution_brief is None
    assert unresolved.clarification_question == "What should the input type be?"
    assert executed == []

    resolved = mode.reply_to_session(session.session_id, "The input is a non-negative integer n.")
    assert resolved.status == "complete"
    assert resolved.execution_brief == "Implement a Lua factorial helper for non-negative integer input n."
    assert resolved.clarification_question is None
    assert executed == ["Implement a Lua factorial helper for non-negative integer input n."]

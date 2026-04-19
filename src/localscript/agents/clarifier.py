from __future__ import annotations

from textwrap import dedent
from typing import Any

from pydantic import BaseModel, Field

from localscript.agents.interface import BaseAgent
from localscript.core.schemas import ClarifierDecision
from localscript.utils import history_text


class ClarifierPayload(BaseModel):
    need_clarification: bool
    questions: list[str] = Field(default_factory=list, max_length=2)
    execution_brief: str = Field(default="", max_length=500)


class ClarifierAgent(BaseAgent[ClarifierDecision]):
    name = "clarifier"
    response_model = ClarifierPayload
    system = (
        "You are the ClarifierAgent in a local multi-agent Lua coding system. "
        "Return strict JSON only. Decide whether the user must answer clarification "
        "questions before coding starts. Ask only the minimum necessary questions. "
        "Keep the response compact. Ask at most two short questions. "
        "If clarification is complete, write one short execution brief instead of a long analysis. "
        "If the user's latest answer does not actually resolve the missing information, ask again or ask a better "
        "follow-up question. Do not silently treat an unrelated answer as resolved. "
        "When enough information is available, return a concise but complete execution brief that fully replaces "
        "the original task and clarification thread for downstream agents."
    )

    def run(self, prompt: str, history: list[dict[str, Any]]) -> ClarifierDecision:
        payload = self.generate_json(prompt=self._prompt(prompt, history))
        return self._parse(payload)

    async def run_async(self, prompt: str, history: list[dict[str, Any]]) -> ClarifierDecision:
        payload = await self.generate_json_async(prompt=self._prompt(prompt, history))
        return self._parse(payload)

    def _prompt(self, prompt: str, history: list[dict[str, Any]]) -> str:
        return dedent(
            f"""
            User task:
            {prompt}

            Session history:
            {history_text(history)}

            Return JSON:
            {{
              "need_clarification": true or false,
              "questions": ["question 1", "question 2"],
              "execution_brief": "self-contained implementation brief for downstream agents; max 120 words"
            }}
            """
        ).strip()

    def _parse(self, payload: dict[str, Any]) -> ClarifierDecision:
        questions = tuple(str(item).strip() for item in payload.get("questions", []) if str(item).strip())
        return ClarifierDecision(
            need_clarification=bool(payload.get("need_clarification", False)),
            questions=questions,
            execution_brief=str(payload.get("execution_brief", "")).strip(),
        )

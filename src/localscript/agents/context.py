from __future__ import annotations

from textwrap import dedent
from typing import Any

from pydantic import BaseModel, Field

from localscript.agents.interface import BaseAgent
from localscript.core.schemas import ContextBundle, KnowledgeChunk
from localscript.utils import history_text, knowledge_text


class ContextPayload(BaseModel):
    constraints: list[str] = Field(default_factory=list)
    context: str


class ContextAgent(BaseAgent[ContextBundle]):
    name = "context"
    response_model = ContextPayload
    system = (
        "You are the ContextAgent in a local multi-agent Lua coding system. "
        "Return strict JSON only. Synthesize relevant implementation context from "
        "local knowledge snippets, user task, and the clarification result or execution brief."
    )

    def run(
        self,
        execution_brief: str,
        workspace_summary: str,
        knowledge_chunks: list[KnowledgeChunk],
        history: list[dict[str, Any]],
    ) -> ContextBundle:
        payload = self.generate_json(
            prompt=self._prompt(execution_brief, workspace_summary, knowledge_chunks, history)
        )
        return self._parse(payload, knowledge_chunks)

    async def run_async(
        self,
        execution_brief: str,
        workspace_summary: str,
        knowledge_chunks: list[KnowledgeChunk],
        history: list[dict[str, Any]],
    ) -> ContextBundle:
        payload = await self.generate_json_async(
            prompt=self._prompt(execution_brief, workspace_summary, knowledge_chunks, history)
        )
        return self._parse(payload, knowledge_chunks)

    def _prompt(
        self,
        execution_brief: str,
        workspace_summary: str,
        knowledge_chunks: list[KnowledgeChunk],
        history: list[dict[str, Any]],
    ) -> str:
        return dedent(
            f"""
            Execution brief:
            {execution_brief}

            Workspace context:
            {workspace_summary or "No additional workspace context."}

            Session history:
            {history_text(history)}

            Local knowledge snippets:
            {knowledge_text(knowledge_chunks)}

            Return JSON:
            {{
              "constraints": ["technical constraints and environment rules"],
              "context": "compact paragraph that combines the useful local context"
            }}
            """
        ).strip()

    def _parse(self, payload: dict[str, Any], knowledge_chunks: list[KnowledgeChunk]) -> ContextBundle:
        return ContextBundle(
            constraints=tuple(str(item).strip() for item in payload.get("constraints", []) if str(item).strip()),
            relevant_chunks=knowledge_chunks,
            context=str(payload.get("context", "")).strip(),
        )

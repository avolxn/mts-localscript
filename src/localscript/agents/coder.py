from __future__ import annotations

from textwrap import dedent

from pydantic import BaseModel

from localscript.agents.interface import BaseAgent
from localscript.core.schemas import CodeDraft, ContextBundle
from localscript.utils import bullet_text, normalize_code


class CoderPayload(BaseModel):
    code: str | list[str]


class CoderAgent(BaseAgent[CodeDraft]):
    name = "coder"
    response_model = CoderPayload
    system = (
        "You are the CoderAgent in a local multi-agent Lua coding system. "
        "Return strict JSON only. Produce correct Lua 5 code for the requested task."
    )

    def run(
        self,
        *,
        execution_brief: str,
        context: ContextBundle,
        strategy: str,
    ) -> CodeDraft:
        payload = self.generate_json(prompt=self._prompt(execution_brief, context, strategy))
        return self._parse(payload)

    async def run_async(
        self,
        *,
        execution_brief: str,
        context: ContextBundle,
        strategy: str,
    ) -> CodeDraft:
        payload = await self.generate_json_async(
            prompt=self._prompt(execution_brief, context, strategy)
        )
        return self._parse(payload)

    def _prompt(
        self,
        execution_brief: str,
        context: ContextBundle,
        strategy: str,
    ) -> str:
        return dedent(
            f"""
            Execution brief:
            {execution_brief}

            Constraints:
            {bullet_text(context.constraints)}

            Synthesized local context:
            {context.context}

            Draft strategy:
            {strategy}

            Return JSON:
            {{
              "code": "Lua code only without Markdown"
            }}
            """
        ).strip()

    def _parse(self, payload: dict) -> CodeDraft:
        return CodeDraft(
            code=normalize_code(payload.get("code", "")),
        )

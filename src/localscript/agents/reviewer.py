from __future__ import annotations

from textwrap import dedent

from pydantic import BaseModel, Field

from localscript.agents.interface import BaseAgent
from localscript.core.schemas import ContextBundle, ReviewDecision, ReviewIssue
from localscript.utils import bullet_text


class ReviewerIssuePayload(BaseModel):
    title: str = ""
    description: str = ""
    severity: str = "medium"


class ReviewerPayload(BaseModel):
    accept: bool
    issues: list[ReviewerIssuePayload] = Field(default_factory=list)


class ReviewerAgent(BaseAgent[ReviewDecision]):
    name = "reviewer"
    response_model = ReviewerPayload
    system = (
        "You are the ReviewerAgent in a local multi-agent Lua coding system. "
        "Return strict JSON only. Critique the candidate code against the task, "
        "highlight concrete issues, and decide whether it is acceptable."
    )

    def run(
        self,
        *,
        execution_brief: str,
        context: ContextBundle,
        code: str,
        verifier_summary: str = "",
    ) -> ReviewDecision:
        payload = self.generate_json(
            prompt=self._prompt(execution_brief, context, code, verifier_summary)
        )
        return self._parse(payload)

    async def run_async(
        self,
        *,
        execution_brief: str,
        context: ContextBundle,
        code: str,
        verifier_summary: str = "",
    ) -> ReviewDecision:
        payload = await self.generate_json_async(
            prompt=self._prompt(execution_brief, context, code, verifier_summary)
        )
        return self._parse(payload)

    def _prompt(
        self, execution_brief: str, context: ContextBundle, code: str, verifier_summary: str
    ) -> str:
        return dedent(
            f"""
            Execution brief:
            {execution_brief}

            Constraints:
            {bullet_text(context.constraints)}

            Context:
            {context.context}

            Verifier summary:
            {verifier_summary or "No verifier findings yet."}

            Candidate Lua code:
            {code}

            Return JSON:
            {{
              "accept": true or false,
              "issues": [
                {{"title": "...", "description": "...", "severity": "high|medium|low"}}
              ]
            }}
            """
        ).strip()

    def _parse(self, payload: dict) -> ReviewDecision:
        issues = tuple(
            ReviewIssue(
                title=str(item.get("title", "")).strip(),
                description=str(item.get("description", "")).strip(),
                severity=str(item.get("severity", "medium")).strip(),
            )
            for item in payload.get("issues", [])
            if str(item.get("title", "")).strip() or str(item.get("description", "")).strip()
        )
        return ReviewDecision(
            accept=bool(payload.get("accept", False)),
            issues=issues,
        )

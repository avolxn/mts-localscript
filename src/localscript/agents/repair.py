from __future__ import annotations

from textwrap import dedent

from pydantic import BaseModel

from localscript.agents.interface import BaseAgent
from localscript.core.schemas import (
    CodeDraft,
    ContextBundle,
    ReviewDecision,
    VerificationResult,
)
from localscript.utils import bullet_text, normalize_code


class RepairPayload(BaseModel):
    code: str | list[str]


class RepairAgent(BaseAgent[CodeDraft]):
    name = "repair"
    response_model = RepairPayload
    system = (
        "You are the RepairAgent in a local multi-agent Lua coding system. "
        "Return strict JSON only. Revise the code to address reviewer findings, "
        "verifier findings, and direct user feedback."
    )

    def run(
        self,
        *,
        execution_brief: str,
        context: ContextBundle,
        current_code: str,
        review: ReviewDecision,
        verifier: VerificationResult,
        user_feedback: str | None = None,
    ) -> CodeDraft:
        payload = self.generate_json(
            prompt=self._prompt(
                execution_brief,
                context,
                current_code,
                review,
                verifier,
                user_feedback,
            )
        )
        return self._parse(payload)

    async def run_async(
        self,
        *,
        execution_brief: str,
        context: ContextBundle,
        current_code: str,
        review: ReviewDecision,
        verifier: VerificationResult,
        user_feedback: str | None = None,
    ) -> CodeDraft:
        payload = await self.generate_json_async(
            prompt=self._prompt(
                execution_brief,
                context,
                current_code,
                review,
                verifier,
                user_feedback,
            )
        )
        return self._parse(payload)

    def _prompt(
        self,
        execution_brief: str,
        context: ContextBundle,
        current_code: str,
        review: ReviewDecision,
        verifier: VerificationResult,
        user_feedback: str | None,
    ) -> str:
        return dedent(
            f"""
            Execution brief:
            {execution_brief}

            Context:
            {context.context}

            Current Lua code:
            {current_code}

            Reviewer summary:
            {bullet_text(tuple(f"{issue.severity}: {issue.title} - {issue.description}" for issue in review.issues))}

            Verifier summary:
            {verifier.summary}

            User feedback:
            {user_feedback or "No direct user feedback."}

            Return JSON:
            {{
              "code": "revised Lua code only without Markdown"
            }}
            """
        ).strip()

    def _parse(self, payload: dict) -> CodeDraft:
        return CodeDraft(
            code=normalize_code(payload.get("code", "")),
        )

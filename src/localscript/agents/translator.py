from __future__ import annotations

from textwrap import dedent
from typing import Any

from pydantic import BaseModel

from localscript.agents.interface import BaseAgent
from localscript.core.schemas import TranslationDecision


class TranslatorPayload(BaseModel):
    translated_text: str


class TranslatorAgent(BaseAgent[TranslationDecision]):
    name = "translator"
    response_model = TranslatorPayload
    system = (
        "You are the TranslatorAgent in a local multi-agent Lua coding system. "
        "Return strict JSON only. Translate user requests into English for downstream agents. "
        "Preserve code, identifiers, field names, JSON keys, API names, file paths, and workflow variable names exactly."
    )

    def run(self, text: str, source_language: str) -> TranslationDecision:
        payload = self.generate_json(prompt=self._prompt(text, source_language))
        return self._parse(payload, source_language, text)

    async def run_async(self, text: str, source_language: str) -> TranslationDecision:
        payload = await self.generate_json_async(prompt=self._prompt(text, source_language))
        return self._parse(payload, source_language, text)

    def _prompt(self, text: str, source_language: str) -> str:
        return dedent(
            f"""
            Source language: {source_language}

            User text:
            {text}

            Translate the user text into clear English for internal agent use.
            Preserve code snippets, Lua identifiers, workflow paths such as wf.vars and wf.initVariables,
            JSON keys, API names, and filenames exactly as written.

            Return JSON:
            {{
              "translated_text": "translated text"
            }}
            """
        ).strip()

    def _parse(self, payload: dict[str, Any], source_language: str, original_text: str) -> TranslationDecision:
        translated_text = str(payload.get("translated_text", "")).strip() or original_text
        return TranslationDecision(
            source_language=source_language,
            target_language="en",
            translated_text=translated_text,
        )


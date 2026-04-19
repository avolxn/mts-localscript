from __future__ import annotations

import asyncio
import json
from typing import Any

from ollama import chat
from pydantic import BaseModel, ValidationError

from localscript.core.settings import Settings
from localscript.logs import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """Simple wrapper around ollama.chat for agent use."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[Any] | None = None,
        response_format: str | dict[str, Any] | None = None,
    ) -> Any:
        """Synchronous wrapper over ollama.chat."""
        self.settings.validate_runtime()
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.settings.keep_alive,
            "options": {
                "num_ctx": self.settings.num_ctx,
                "num_predict": self.settings.num_predict,
            },
        }
        if tools:
            payload["tools"] = tools
        if response_format is not None:
            payload["format"] = response_format
        return chat(**payload)

    async def chat_async(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[Any] | None = None,
        response_format: str | dict[str, Any] | None = None,
    ) -> Any:
        """Asynchronous wrapper over ollama.chat."""
        self.settings.validate_runtime()
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.settings.keep_alive,
            "options": {
                "num_ctx": self.settings.num_ctx,
                "num_predict": self.settings.num_predict,
            },
        }
        if tools:
            payload["tools"] = tools
        if response_format is not None:
            payload["format"] = response_format
        return await asyncio.to_thread(chat, **payload)

    def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        response_model: type[BaseModel],
    ) -> dict[str, Any]:
        """Generate JSON response using chat with schema format."""
        self.settings.validate_runtime()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        return self._generate_json_once_or_retry(messages=messages, response_model=response_model)

    async def generate_json_async(
        self,
        *,
        system: str,
        prompt: str,
        response_model: type[BaseModel],
    ) -> dict[str, Any]:
        """Generate JSON response asynchronously."""
        self.settings.validate_runtime()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        return await self._generate_json_once_or_retry_async(messages=messages, response_model=response_model)

    def _json_payload(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> dict[str, Any]:
        return {
            "model": self.settings.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.settings.keep_alive,
            "format": response_model.model_json_schema(),
            "options": {
                "num_ctx": self.settings.num_ctx,
                "num_predict": self.settings.num_predict,
            },
        }

    def _generate_json_once_or_retry(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> dict[str, Any]:
        content = self._chat_json_content(messages=messages, response_model=response_model)
        try:
            return self._coerce_json(content, response_model)
        except ValueError:
            logger.warning(
                "Retrying structured JSON response for %s after malformed or truncated output.",
                response_model.__name__,
            )
            retry_content = self._chat_json_content(
                messages=self._retry_messages(messages),
                response_model=response_model,
            )
            return self._coerce_json(retry_content, response_model)

    async def _generate_json_once_or_retry_async(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> dict[str, Any]:
        content = await self._chat_json_content_async(messages=messages, response_model=response_model)
        try:
            return self._coerce_json(content, response_model)
        except ValueError:
            logger.warning(
                "Retrying structured JSON response for %s after malformed or truncated output.",
                response_model.__name__,
            )
            retry_content = await self._chat_json_content_async(
                messages=self._retry_messages(messages),
                response_model=response_model,
            )
            return self._coerce_json(retry_content, response_model)

    def _chat_json_content(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> str:
        response = chat(**self._json_payload(messages=messages, response_model=response_model))
        raw = self._model_dump(response)
        return str(raw.get("message", {}).get("content", "")).strip()

    async def _chat_json_content_async(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> str:
        response = await asyncio.to_thread(chat, **self._json_payload(messages=messages, response_model=response_model))
        raw = self._model_dump(response)
        return str(raw.get("message", {}).get("content", "")).strip()

    @staticmethod
    def _retry_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        retry_messages = list(messages)
        retry_messages.append(
            {
                "role": "system",
                "content": (
                    "Your previous response was malformed or truncated. "
                    "Return valid JSON only. Keep every string compact. "
                    "Do not add explanations, markdown, or extra fields."
                ),
            }
        )
        return retry_messages

    @staticmethod
    def _model_dump(response: Any) -> dict[str, Any]:
        if hasattr(response, "model_dump"):
            return response.model_dump()
        if isinstance(response, dict):
            return dict(response)
        raise TypeError(f"Unsupported Ollama response type: {type(response)!r}")

    @staticmethod
    def _coerce_json(content: str, response_model: type[BaseModel]) -> dict[str, Any]:
        try:
            return response_model.model_validate_json(content).model_dump()
        except ValidationError as exc:
            logger.exception(
                "Ollama structured output failed schema validation for %s.",
                response_model.__name__,
            )
            raise ValueError("Ollama returned JSON that does not match the expected schema.") from exc
        except json.JSONDecodeError as exc:
            logger.exception(
                "Ollama returned malformed JSON for %s.",
                response_model.__name__,
            )
            raise ValueError("Ollama returned malformed JSON.") from exc

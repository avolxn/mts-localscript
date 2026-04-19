from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel

from localscript.ollama import OllamaClient

AgentResultT = TypeVar("AgentResultT")


class BaseAgent[AgentResultT](ABC):
    name: ClassVar[str]
    system: ClassVar[str]
    response_model: ClassVar[type[BaseModel]]

    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def generate_json(self, *, prompt: str) -> dict[str, Any]:
        return self.client.generate_json(
            system=self.system,
            prompt=prompt,
            response_model=self.response_model,
        )

    async def generate_json_async(self, *, prompt: str) -> dict[str, Any]:
        return await self.client.generate_json_async(
            system=self.system,
            prompt=prompt,
            response_model=self.response_model,
        )

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> AgentResultT:
        raise NotImplementedError

    @abstractmethod
    async def run_async(self, *args: Any, **kwargs: Any) -> AgentResultT:
        raise NotImplementedError

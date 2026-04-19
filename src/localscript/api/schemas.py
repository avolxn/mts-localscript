from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural-language task description")


class GenerateResponse(BaseModel):
    code: str = Field(..., min_length=1, description="Generated Lua code")

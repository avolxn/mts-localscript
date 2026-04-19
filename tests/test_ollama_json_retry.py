from __future__ import annotations

from pydantic import BaseModel

from localscript.core.settings import Settings
from localscript.ollama import OllamaClient


class DemoPayload(BaseModel):
    ok: bool
    text: str


def test_generate_json_retries_after_malformed_response(monkeypatch) -> None:
    malformed_json = '{"ok": true, "text": "truncated'
    valid_json = '{"ok": true, "text": "fixed"}'
    responses = [
        {"message": {"content": malformed_json}},
        {"message": {"content": valid_json}},
    ]
    calls: list[dict] = []

    def fake_chat(**payload):
        calls.append(payload)
        return responses.pop(0)

    monkeypatch.setattr("localscript.ollama.chat", fake_chat)

    monkeypatch.setattr(Settings, "validate_runtime", lambda self: None)

    client = OllamaClient(Settings())
    payload = client.generate_json(
        system="Return JSON.",
        prompt="Test prompt",
        response_model=DemoPayload,
    )

    assert payload == {"ok": True, "text": "fixed"}
    assert len(calls) == 2
    assert calls[1]["messages"][-1]["role"] == "system"
    assert "malformed or truncated" in calls[1]["messages"][-1]["content"]

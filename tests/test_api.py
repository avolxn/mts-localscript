from fastapi.testclient import TestClient

from localscript.api import create_app
from localscript.core.classifier import TaskClassifier
from localscript.core.schemas import (
    ClarificationTurn,
    GenerationResult,
    ValidationReport,
)
from localscript.core.settings import Settings


class FakeCodegenMode:
    async def generate_one_shot_async(self, prompt: str):
        return GenerationResult(
            prompt=prompt,
            task_profile=TaskClassifier().classify(prompt),
            clarification=ClarificationTurn(questions=("q",)),
            retrieved_examples=[],
            initial_code="return 42",
            final_code="return 42",
            validation_report=ValidationReport(is_valid=True, normalized_code="return 42"),
            metadata={"session_id": "sess-generate"},
        )


def test_generate_endpoint_matches_contract(monkeypatch) -> None:
    monkeypatch.setattr(Settings, "validate_runtime", lambda self: None)
    app = create_app(Settings(), codegen_mode=FakeCodegenMode())
    with TestClient(app) as client:
        response = client.post("/generate", json={"prompt": "Return 42"})
        missing = client.get("/sessions/sess-1")
    assert response.status_code == 200
    assert response.json() == {"code": "return 42"}
    assert missing.status_code == 404

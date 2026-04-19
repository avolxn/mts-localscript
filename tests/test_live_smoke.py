import os
import runpy
from pathlib import Path

import pytest

from localscript.core import Settings, parse_public_dataset
from localscript.modes import build_lua_codegen_mode

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LOCAL_MODEL_TESTS") != "1",
    reason="Set RUN_LOCAL_MODEL_TESTS=1 to run live Ollama smoke tests.",
)


def test_live_model_smoke() -> None:
    module = runpy.run_path(str(Path("scripts/evaluate_dataset.py")))
    evaluate_examples = module["evaluate_examples"]
    settings = Settings.from_env()
    settings.validate_runtime()
    codegen_mode = build_lua_codegen_mode(settings)
    dataset = parse_public_dataset(Path("data/public_localscript_dataset.md").read_text(encoding="utf-8"))
    results = evaluate_examples(codegen_mode, dataset[:2])
    assert results
    assert all(result.result.final_code.strip() for result in results)
    assert all(result.valid for result in results)
    assert all(result.result.candidates for result in results)

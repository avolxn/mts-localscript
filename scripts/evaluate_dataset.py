from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from localscript.core import Settings, parse_public_dataset
from localscript.core.knowledge import tokenize
from localscript.core.schemas import (
    GenerationResult,
    KnowledgeExample,
    ValidationReport,
)
from localscript.modes import LuaCodegenMode, build_lua_codegen_mode


@dataclass(slots=True)
class RegressionExpectation:
    required_substrings: tuple[str, ...] = ()
    forbidden_substrings: tuple[str, ...] = ()


@dataclass(slots=True)
class RegressionCheckResult:
    passed: bool
    missing_required: tuple[str, ...]
    forbidden_present: tuple[str, ...]


@dataclass(slots=True)
class EvaluationResult:
    identifier: str
    title: str
    valid: bool
    match_ratio: float
    expectation_result: RegressionCheckResult
    report: ValidationReport
    result: GenerationResult


def compose_task_prompt(example: KnowledgeExample) -> str:
    if example.context_json:
        return f"{example.prompt}\n\nContext JSON:\n{example.context_json}"
    return example.prompt


def token_overlap_ratio(expected_code: str, actual_code: str) -> float:
    expected_tokens = tokenize(expected_code)
    actual_tokens = tokenize(actual_code)
    if not expected_tokens:
        return 0.0
    return len(expected_tokens & actual_tokens) / len(expected_tokens)


def load_expectations(path: Path) -> dict[str, RegressionExpectation]:
    if not path.exists():
        raise FileNotFoundError(f"Regression expectations file not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        key: RegressionExpectation(
            required_substrings=tuple(value.get("required_substrings", [])),
            forbidden_substrings=tuple(value.get("forbidden_substrings", [])),
        )
        for key, value in raw.items()
    }


def check_expectations(code: str, expectation: RegressionExpectation | None) -> RegressionCheckResult:
    if expectation is None:
        return RegressionCheckResult(True, (), ())
    missing_required = tuple(item for item in expectation.required_substrings if item not in code)
    forbidden_present = tuple(item for item in expectation.forbidden_substrings if item in code)
    return RegressionCheckResult(
        passed=not missing_required and not forbidden_present,
        missing_required=missing_required,
        forbidden_present=forbidden_present,
    )


def evaluate_examples(codegen_mode: LuaCodegenMode, examples: list[KnowledgeExample]) -> list[EvaluationResult]:
    expectations = load_expectations(Path(codegen_mode.orchestrator.settings.data_dir) / "regression_expectations.json")
    results: list[EvaluationResult] = []
    for example in examples:
        prompt = compose_task_prompt(example)
        generation_result = codegen_mode.generate_one_shot(prompt)
        report = generation_result.active_report
        expectation_result = check_expectations(generation_result.final_code, expectations.get(example.identifier))
        results.append(
            EvaluationResult(
                identifier=example.identifier,
                title=example.title,
                valid=report.is_valid and expectation_result.passed,
                match_ratio=token_overlap_ratio(example.expected_code, generation_result.final_code),
                expectation_result=expectation_result,
                report=report,
                result=generation_result,
            )
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate LocalScript on the bundled dataset")
    parser.add_argument(
        "--dataset",
        default="data/public_localscript_dataset.md",
        help="Dataset markdown path",
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional maximum number of tasks to run")
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.validate_runtime()
    codegen_mode = build_lua_codegen_mode(settings)
    dataset_path = Path(args.dataset)
    examples = parse_public_dataset(dataset_path.read_text(encoding="utf-8"))
    if args.limit:
        examples = examples[: args.limit]

    evaluated = evaluate_examples(codegen_mode, examples)
    results: list[dict[str, object]] = []
    for result in evaluated:
        results.append(
            {
                "id": result.identifier,
                "title": result.title,
                "valid": result.valid,
                "match_ratio": round(result.match_ratio, 3),
                "expectation_passed": result.expectation_result.passed,
                "missing_required": list(result.expectation_result.missing_required),
                "forbidden_present": list(result.expectation_result.forbidden_present),
                "issues": [issue.message for issue in result.report.issues],
                "code": result.result.final_code,
                "task_profile": result.result.task_profile.summary(),
                "candidate_scores": [round(candidate.score, 2) for candidate in result.result.candidates],
                "session_id": result.result.metadata.get("session_id"),
            }
        )

    passed = sum(1 for result in results if result["valid"])
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

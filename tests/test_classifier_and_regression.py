import runpy
from pathlib import Path

from localscript.core.classifier import TaskClassifier


def test_classifier_detects_lowcode_time_task() -> None:
    profile = TaskClassifier().classify(
        'Convert wf.initVariables.recallTime to unix format in Lua with {"wf": {"initVariables": {}}}'
    )
    assert profile.environment == "lowcode"
    assert profile.task_type == "unix_time"
    assert profile.needs_workflow is True


def test_regression_expectations_load_and_check() -> None:
    module = runpy.run_path(str(Path("scripts/evaluate_dataset.py")))
    load_expectations = module["load_expectations"]
    check_expectations = module["check_expectations"]
    expectations = load_expectations(Path("data/regression_expectations.json"))
    result = check_expectations(
        "return wf.vars.try_count_n + 1",
        expectations["example-2"],
    )
    assert result.passed

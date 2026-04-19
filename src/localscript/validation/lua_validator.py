from __future__ import annotations

from dataclasses import asdict

from localscript.core.classifier import TaskClassifier
from localscript.core.schemas import VerificationResult, VerificationToolResult
from localscript.validation.lua_lsp import LuaLspValidator
from localscript.validation.lua_static import LuaStaticValidator


class LuaValidator:
    def __init__(self) -> None:
        self.static_validator = LuaStaticValidator()
        self.lsp_validator = LuaLspValidator()
        self.classifier = TaskClassifier()

    def verify(self, prompt: str, code: str) -> VerificationResult:
        task_profile = self.classifier.classify(prompt)
        validation_report = self.static_validator.validate(prompt, code, task_profile)
        tool_results = [self._static_tool_result(validation_report)]
        lsp_result, lsp_issues = self.lsp_validator.verify(code)
        tool_results.append(lsp_result)
        issues = [*validation_report.issues, *lsp_issues]
        passed = validation_report.is_valid and all(tool.passed for tool in tool_results)
        summary_parts = [tool.summary for tool in tool_results]
        return VerificationResult(
            passed=passed,
            summary=" | ".join(part for part in summary_parts if part),
            tool_results=tuple(tool_results),
            issues=tuple(issues),
        )

    def _static_tool_result(self, validation_report) -> VerificationToolResult:
        if validation_report.is_valid:
            return VerificationToolResult(
                tool="static_validator",
                passed=True,
                summary="Static validator passed.",
                metadata={"issue_count": 0},
            )
        return VerificationToolResult(
            tool="static_validator",
            passed=False,
            summary=validation_report.summary(),
            metadata={"issue_count": len(validation_report.issues)},
        )


def validation_to_payload(result: VerificationResult) -> dict:
    return {
        "passed": result.passed,
        "summary": result.summary,
        "tool_results": [asdict(tool) for tool in result.tool_results],
        "issues": [asdict(issue) for issue in result.issues],
    }

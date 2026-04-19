from __future__ import annotations

import re

from localscript.core.schemas import TaskProfile, ValidationIssue, ValidationReport

FENCE_RE = re.compile(r"```|^lua\{|}lua$", re.MULTILINE)
JSON_RE = re.compile(r"^\s*[{[]", re.DOTALL)
BANNED_PATTERNS = {
    "jsonpath": re.compile(r"[$]\.|jsonpath", re.IGNORECASE),
    "placeholder": re.compile(r"\b(TODO|FIXME|placeholder)\b", re.IGNORECASE),
    "shell": re.compile(r"\bos\.execute\b|\bio\.popen\b"),
}


class LuaStaticValidator:
    def validate(self, prompt: str, code: str, task_profile: TaskProfile | None = None) -> ValidationReport:
        normalized = code.strip()
        issues: list[ValidationIssue] = []
        if not normalized:
            issues.append(
                ValidationIssue(
                    code="empty",
                    message="The model returned empty output.",
                    category="format",
                )
            )
        if FENCE_RE.search(normalized):
            issues.append(
                ValidationIssue(
                    code="markdown",
                    message="Output must not include Markdown fences or lua{ wrappers.",
                    category="format",
                )
            )
        if JSON_RE.match(normalized):
            issues.append(
                ValidationIssue(
                    code="json",
                    message="Output must be Lua code only, not JSON.",
                    category="format",
                )
            )
        issues.extend(self._validate_banned_patterns(normalized))
        issues.extend(self._validate_workflow_access(prompt, normalized))
        issues.extend(self._validate_array_creation(prompt, normalized))
        issues.extend(self._validate_task_match(prompt, normalized, task_profile))
        is_valid = not issues
        return ValidationReport(is_valid=is_valid, issues=issues, normalized_code=normalized)

    def _validate_banned_patterns(self, code: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for issue_code, pattern in BANNED_PATTERNS.items():
            if pattern.search(code):
                category = "safety" if issue_code == "shell" else "rules"
                issues.append(
                    ValidationIssue(
                        code=issue_code,
                        message=f"Banned pattern detected: {issue_code}.",
                        category=category,
                    )
                )
        return issues

    def _validate_workflow_access(self, prompt: str, code: str) -> list[ValidationIssue]:
        lowered_prompt = prompt.lower()
        requires_workflow = any(
            token in lowered_prompt for token in ('"wf"', "wf.vars", "wf.initvariables", "initvariables")
        )
        if requires_workflow and "wf.vars" not in code and "wf.initVariables" not in code:
            return [
                ValidationIssue(
                    code="workflow",
                    message="Prompt includes workflow context, so the code should use direct wf.vars or wf.initVariables access.",
                    category="rules",
                )
            ]
        return []

    def _validate_array_creation(self, prompt: str, code: str) -> list[ValidationIssue]:
        if "_utils.array.new()" in code or "_utils.array.markAsArray" in code:
            return []
        lowered_prompt = prompt.lower()
        if "lowcode" not in lowered_prompt and '"wf"' not in lowered_prompt:
            return []
        if re.search(r"local\s+\w+\s*=\s*\{\s*\}", code) and "table.insert" in code:
            return [
                ValidationIssue(
                    code="array_helper",
                    message="LowCode array creation should use _utils.array.new() instead of a plain {} table.",
                    category="rules",
                )
            ]
        return []

    def _validate_task_match(
        self,
        prompt: str,
        code: str,
        task_profile: TaskProfile | None,
    ) -> list[ValidationIssue]:
        if task_profile is None:
            return []
        lowered_code = code.lower()
        issues: list[ValidationIssue] = []
        if task_profile.task_type == "array_last_element" and "#" not in code:
            issues.append(
                ValidationIssue(
                    code="last_element",
                    message="The task asks for the last element, but the code does not appear to index from the end.",
                    category="task_match",
                    severity="warning",
                )
            )
        elif task_profile.task_type == "counter_increment" and "+ 1" not in code and "+1" not in code:
            issues.append(
                ValidationIssue(
                    code="increment",
                    message="The task asks for an increment, but '+ 1' was not detected.",
                    category="task_match",
                    severity="warning",
                )
            )
        elif task_profile.task_type == "field_cleanup":
            missing = [token for token in ("ID", "ENTITY_ID", "CALL") if token not in code]
            if missing or "nil" not in code:
                issues.append(
                    ValidationIssue(
                        code="cleanup_fields",
                        message="The cleanup task should preserve ID, ENTITY_ID, CALL and remove other fields with nil assignments.",
                        category="task_match",
                        severity="warning",
                    )
                )
        elif task_profile.task_type == "iso_time_format" and "string.format" not in code:
            issues.append(
                ValidationIssue(
                    code="iso_format",
                    message="The ISO formatting task should usually construct the final string explicitly with string.format.",
                    category="task_match",
                    severity="warning",
                )
            )
        elif task_profile.task_type == "unix_time" and not any(
            token in code for token in ("86400", "os.time", "epoch")
        ):
            issues.append(
                ValidationIssue(
                    code="unix_time",
                    message="The unix time task should contain timestamp conversion logic.",
                    category="task_match",
                    severity="warning",
                )
            )
        elif task_profile.task_type == "array_filter" and not all(
            token.lower() in lowered_code for token in ("discount", "markdown")
        ):
            issues.append(
                ValidationIssue(
                    code="filter_fields",
                    message="The filter task should reference both Discount and Markdown fields.",
                    category="task_match",
                    severity="warning",
                )
            )
        elif task_profile.task_type == "array_normalization" and not any(
            token in code for token in ("type(", "pairs(", "ipairs(")
        ):
            issues.append(
                ValidationIssue(
                    code="array_normalization",
                    message="The normalization task should inspect item shapes before wrapping them as arrays.",
                    category="task_match",
                    severity="warning",
                )
            )
        elif task_profile.task_type == "math_factorial" and "factorial" not in lowered_code:
            issues.append(
                ValidationIssue(
                    code="factorial_name",
                    message="The factorial task usually expects a factorial function or clearly named implementation.",
                    category="task_match",
                    severity="warning",
                )
            )
        return issues

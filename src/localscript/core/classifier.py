from __future__ import annotations

from localscript.core.schemas import TaskProfile


class TaskClassifier:
    def classify(self, prompt: str) -> TaskProfile:
        lowered = prompt.lower()
        needs_workflow = any(
            token in lowered
            for token in (
                '"wf"',
                "wf.vars",
                "wf.initvariables",
                "wf.initvariables",
                "initvariables",
            )
        )
        environment = "lowcode" if needs_workflow or "_utils.array" in lowered or "lowcode" in lowered else "plain_lua"
        task_type = self._detect_task_type(lowered)
        tags = list(self._derive_tags(lowered, task_type, environment))
        needs_array_helpers = environment == "lowcode" and (
            task_type in {"array_filter", "array_normalization"} or any(tag in lowered for tag in ("array", "list"))
        )
        expected_patterns, avoid_patterns = self._pattern_hints(task_type, needs_workflow, needs_array_helpers)
        return TaskProfile(
            task_type=task_type,
            environment=environment,
            tags=tuple(tags),
            needs_workflow=needs_workflow,
            needs_array_helpers=needs_array_helpers,
            expected_patterns=expected_patterns,
            avoid_patterns=avoid_patterns,
        )

    def _detect_task_type(self, lowered: str) -> str:
        if "factorial" in lowered:
            return "math_factorial"
        if ("last" in lowered or "послед" in lowered) and any(
            token in lowered for token in ("array", "list", "email", "emails")
        ):
            return "array_last_element"
        if any(token in lowered for token in ("increment", "counter", "try_count", "увелич")):
            return "counter_increment"
        if "clear" in lowered and all(token in lowered for token in ("id", "entity_id", "call")):
            return "field_cleanup"
        if any(token in lowered for token in ("yyyymmdd", "hhmmss", "iso 8601", "iso-8601", "iso standard")):
            return "iso_time_format"
        if "unix" in lowered and "time" in lowered:
            return "unix_time"
        if "filter" in lowered and any(token in lowered for token in ("discount", "markdown")):
            return "array_filter"
        if "items" in lowered and "array" in lowered:
            return "array_normalization"
        if "square" in lowered or "squared" in lowered:
            return "derive_square"
        if "existing code" in lowered or "revise" in lowered or "improve" in lowered:
            return "refine_existing_code"
        if "filter" in lowered:
            return "generic_filter"
        if any(token in lowered for token in ("date", "time", "timestamp")):
            return "time_transform"
        if any(token in lowered for token in ("array", "list", "table")):
            return "array_transform"
        return "general_lua"

    def _derive_tags(self, lowered: str, task_type: str, environment: str) -> tuple[str, ...]:
        tags = [task_type, environment]
        if environment == "lowcode":
            tags.extend(["workflow", "lowcode"])
        if "array" in lowered or "list" in lowered:
            tags.append("arrays")
        if "time" in lowered or "date" in lowered or "unix" in lowered or "iso" in lowered:
            tags.append("time")
        if "filter" in lowered:
            tags.append("filtering")
        if "json" in lowered:
            tags.append("json")
        return tuple(dict.fromkeys(tags))

    def _pattern_hints(
        self,
        task_type: str,
        needs_workflow: bool,
        needs_array_helpers: bool,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        expected: list[str] = []
        avoid: list[str] = ["```", "jsonpath"]
        if needs_workflow:
            expected.append("wf.vars")
        if task_type == "array_last_element":
            expected.extend(["#", "return"])
        elif task_type == "counter_increment":
            expected.extend(["+ 1", "return"])
        elif task_type == "field_cleanup":
            expected.extend(["ID", "ENTITY_ID", "CALL", "nil"])
        elif task_type == "iso_time_format":
            expected.extend(["string.format", "T", "Z"])
        elif task_type == "unix_time":
            expected.extend(["86400", "return"])
        elif task_type == "array_filter":
            expected.extend(["Discount", "Markdown", "table.insert"])
        elif task_type == "array_normalization":
            expected.extend(["type(", "pairs", "return"])
        if needs_array_helpers:
            expected.append("_utils.array")
        return tuple(expected), tuple(avoid)

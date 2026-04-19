from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class TaskProfile:
    task_type: str
    environment: str
    tags: tuple[str, ...] = ()
    needs_workflow: bool = False
    needs_array_helpers: bool = False
    expected_patterns: tuple[str, ...] = ()
    avoid_patterns: tuple[str, ...] = ()

    def summary(self) -> str:
        tags = ", ".join(self.tags) if self.tags else "none"
        return (
            f"type={self.task_type}; environment={self.environment}; "
            f"workflow={self.needs_workflow}; array_helpers={self.needs_array_helpers}; tags={tags}"
        )


@dataclass(slots=True)
class ClarifierDecision:
    need_clarification: bool
    questions: tuple[str, ...] = ()
    execution_brief: str = ""


@dataclass(slots=True)
class TranslationDecision:
    source_language: str
    target_language: str
    translated_text: str

    @property
    def was_translated(self) -> bool:
        return self.source_language != self.target_language


@dataclass(slots=True)
class KnowledgeChunk:
    chunk_id: str
    source: str
    title: str
    content: str
    kind: str
    score: float = 0.0


@dataclass(slots=True)
class ContextBundle:
    constraints: tuple[str, ...]
    relevant_chunks: list[KnowledgeChunk]
    context: str


@dataclass(slots=True)
class CodeDraft:
    code: str


@dataclass(slots=True)
class ReviewIssue:
    title: str
    description: str
    severity: str = "medium"


@dataclass(slots=True)
class ReviewDecision:
    accept: bool
    issues: tuple[ReviewIssue, ...] = ()


@dataclass(slots=True)
class VerificationToolResult:
    tool: str
    passed: bool
    summary: str
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VerificationResult:
    passed: bool
    summary: str
    tool_results: tuple[VerificationToolResult, ...] = ()
    issues: tuple[ValidationIssue, ...] = ()


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    status: str
    prompt: str
    clarification_question: str | None
    execution_brief: str | None
    latest_code: str | None
    latest_summary: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class KnowledgeExample:
    identifier: str
    title: str
    prompt: str
    expected_code: str
    context_json: str | None = None
    tags: tuple[str, ...] = ()

    @property
    def search_text(self) -> str:
        parts = [self.title, self.prompt, self.expected_code, " ".join(self.tags)]
        if self.context_json:
            parts.append(self.context_json)
        return "\n".join(parts)


@dataclass(slots=True)
class RetrievedExample:
    example: KnowledgeExample
    score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class ClarificationTurn:
    questions: tuple[str, ...] = ()
    answer: str | None = None
    execution_brief: str = ""

    def answer_or_brief(self) -> str:
        if self.answer and self.answer.strip():
            return self.answer.strip()
        if self.execution_brief.strip():
            return self.execution_brief.strip()
        return "Proceed with a minimal, correct implementation."


@dataclass(slots=True)
class ValidationIssue:
    code: str
    message: str
    category: str = "rules"
    severity: str = "error"


@dataclass(slots=True)
class ValidationReport:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    normalized_code: str = ""

    def summary(self) -> str:
        if not self.issues:
            return "No validation issues detected."
        grouped: dict[str, list[ValidationIssue]] = {}
        for issue in self.issues:
            grouped.setdefault(issue.category, []).append(issue)
        parts: list[str] = []
        for category in sorted(grouped):
            parts.append(f"[{category}]")
            parts.extend(f"- {issue.code}: {issue.message}" for issue in grouped[category])
        return "\n".join(parts)

    def categories(self) -> tuple[str, ...]:
        return tuple(sorted({issue.category for issue in self.issues}))

    def total_penalty(self) -> float:
        severity_weights = {"error": 20.0, "warning": 8.0, "info": 3.0}
        category_weights = {
            "format": 1.2,
            "syntax": 1.0,
            "rules": 0.9,
            "task_match": 1.3,
            "semantics": 1.1,
            "safety": 1.4,
        }
        return sum(
            severity_weights.get(issue.severity, 10.0) * category_weights.get(issue.category, 1.0)
            for issue in self.issues
        )


@dataclass(slots=True)
class CandidateResult:
    index: int
    code: str
    report: ValidationReport
    score: float
    strategy: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StageMetric:
    name: str
    duration_ms: float
    gpu_memory_mb_before: int | None = None
    gpu_memory_mb_after: int | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GenerationResult:
    prompt: str
    task_profile: TaskProfile
    clarification: ClarificationTurn
    retrieved_examples: list[RetrievedExample]
    initial_code: str
    final_code: str
    validation_report: ValidationReport
    repair_report: ValidationReport | None = None
    candidates: list[CandidateResult] = field(default_factory=list)
    selected_candidate_index: int = 1
    stage_metrics: list[StageMetric] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def active_report(self) -> ValidationReport:
        return self.repair_report or self.validation_report


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

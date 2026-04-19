from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from localscript.agents import (
    ClarifierAgent,
    CoderAgent,
    ContextAgent,
    RepairAgent,
    ReviewerAgent,
    TranslatorAgent,
)
from localscript.core.classifier import TaskClassifier
from localscript.core.knowledge import KnowledgeBase
from localscript.core.language import detect_language
from localscript.core.schemas import (
    CandidateResult,
    ClarificationTurn,
    CodeDraft,
    ContextBundle,
    GenerationResult,
    ReviewDecision,
    ReviewIssue,
    SessionRecord,
    StageMetric,
    TranslationDecision,
    ValidationReport,
)
from localscript.core.settings import Settings
from localscript.ollama import OllamaClient
from localscript.storage import LocalKnowledgeBase, SQLiteStore
from localscript.tools import ToolExecutionReporter, ToolExecutor, ToolRegistry, build_local_tooling
from localscript.validation import LuaStaticValidator, LuaValidator

DEFAULT_DRAFT_STRATEGIES = (
    "Write the shortest correct implementation that satisfies the task and local constraints.",
    "Write a defensive implementation that handles input shape and edge cases explicitly while staying concise.",
)


@dataclass(slots=True)
class LuaCodegenOrchestrator:
    settings: Settings
    store: SQLiteStore
    kb: LocalKnowledgeBase
    ollama: OllamaClient
    translator: TranslatorAgent
    clarifier: ClarifierAgent
    context_agent: ContextAgent
    coder: CoderAgent
    reviewer: ReviewerAgent
    repair: RepairAgent
    lua_validator: LuaValidator
    task_classifier: TaskClassifier
    lua_static_validator: LuaStaticValidator
    dataset: KnowledgeBase


class LuaCodegenMode:
    def __init__(self, orchestrator: LuaCodegenOrchestrator) -> None:
        self.orchestrator = orchestrator

    @staticmethod
    def clarification_prompt(clarification: ClarificationTurn) -> str:
        if not clarification.questions:
            return ""
        if len(clarification.questions) == 1:
            return clarification.questions[0]
        return "\n".join(f"{index}. {question}" for index, question in enumerate(clarification.questions, start=1))

    def start_session(
        self,
        prompt: str,
        *,
        interactive: bool = True,
        workspace_root: Path | None = None,
        tool_reporter: ToolExecutionReporter | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_executor: ToolExecutor | None = None,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> SessionRecord:
        session = self.orchestrator.store.create_session(prompt, status="created")
        self.orchestrator.store.append_message(session.session_id, role="user", kind="prompt", content=prompt)
        prompt_translation = self._translate_user_text(session.session_id, prompt, kind="prompt")
        history = self.orchestrator.store.list_messages(session.session_id)
        decision = self._record_stage(
            [],
            "clarifier",
            lambda: self.orchestrator.clarifier.run(prompt_translation.translated_text, history),
            progress_callback=progress_callback,
        )
        clarification_prompt = self.clarification_prompt(ClarificationTurn(questions=decision.questions))
        if interactive and decision.need_clarification and clarification_prompt:
            self.orchestrator.store.append_message(
                session.session_id,
                role="assistant",
                kind="clarification",
                content=clarification_prompt,
            )
            self.orchestrator.store.update_session(
                session.session_id,
                status="waiting_for_clarification",
                clarification_question=clarification_prompt,
                execution_brief=None,
                latest_summary="Waiting for clarification.",
            )
            return self.orchestrator.store.get_session(session.session_id)
        execution_brief = decision.execution_brief or "Proceed with a minimal, correct implementation."
        self._execute_session(
            session.session_id,
            prompt_for_model=prompt_translation.translated_text,
            clarification=ClarificationTurn(
                execution_brief=execution_brief,
            ),
            force_refine=True,
            workspace_root=workspace_root,
            tool_reporter=tool_reporter,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
            progress_callback=progress_callback,
        )
        return self.orchestrator.store.get_session(session.session_id)

    async def start_session_async(
        self,
        prompt: str,
        *,
        interactive: bool = True,
        workspace_root: Path | None = None,
        tool_reporter: ToolExecutionReporter | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_executor: ToolExecutor | None = None,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> SessionRecord:
        session = self.orchestrator.store.create_session(prompt, status="created")
        self.orchestrator.store.append_message(session.session_id, role="user", kind="prompt", content=prompt)
        prompt_translation = await self._translate_user_text_async(session.session_id, prompt, kind="prompt")
        history = self.orchestrator.store.list_messages(session.session_id)
        decision = await self._record_stage_async(
            [],
            "clarifier",
            lambda: self.orchestrator.clarifier.run_async(prompt_translation.translated_text, history),
            progress_callback=progress_callback,
        )
        clarification_prompt = self.clarification_prompt(ClarificationTurn(questions=decision.questions))
        if interactive and decision.need_clarification and clarification_prompt:
            self.orchestrator.store.append_message(
                session.session_id,
                role="assistant",
                kind="clarification",
                content=clarification_prompt,
            )
            self.orchestrator.store.update_session(
                session.session_id,
                status="waiting_for_clarification",
                clarification_question=clarification_prompt,
                execution_brief=None,
                latest_summary="Waiting for clarification.",
            )
            return self.orchestrator.store.get_session(session.session_id)
        execution_brief = decision.execution_brief or "Proceed with a minimal, correct implementation."
        await self._execute_session_async(
            session.session_id,
            prompt_for_model=prompt_translation.translated_text,
            clarification=ClarificationTurn(
                execution_brief=execution_brief,
            ),
            force_refine=True,
            workspace_root=workspace_root,
            tool_reporter=tool_reporter,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
            progress_callback=progress_callback,
        )
        return self.orchestrator.store.get_session(session.session_id)

    def reply_to_session(
        self,
        session_id: str,
        content: str,
        *,
        workspace_root: Path | None = None,
        tool_reporter: ToolExecutionReporter | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_executor: ToolExecutor | None = None,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> SessionRecord:
        session = self.orchestrator.store.get_session(session_id)
        self.orchestrator.store.append_message(session_id, role="user", kind="message", content=content)
        prompt_translation = self._translate_user_text(session_id, session.prompt, kind="prompt")
        if session.status == "waiting_for_clarification":
            answer_translation = self._translate_user_text(session_id, content, kind="clarification_answer")
            decision = self._record_stage(
                [],
                "clarifier_followup",
                lambda: self.orchestrator.clarifier.run(prompt_translation.translated_text, self.orchestrator.store.list_messages(session_id)),
                progress_callback=progress_callback,
            )
            if decision.need_clarification and decision.questions:
                clarification_prompt = self.clarification_prompt(ClarificationTurn(questions=decision.questions))
                self.orchestrator.store.append_message(
                    session_id,
                    role="assistant",
                    kind="clarification",
                    content=clarification_prompt,
                )
                self.orchestrator.store.update_session(
                    session_id,
                    status="waiting_for_clarification",
                    clarification_question=clarification_prompt,
                    execution_brief=None,
                    latest_summary="Waiting for clarification.",
                )
            else:
                execution_brief = decision.execution_brief or "Proceed with a minimal, correct implementation."
                self._execute_session(
                    session_id,
                    prompt_for_model=prompt_translation.translated_text,
                    clarification=ClarificationTurn(
                        answer=answer_translation.translated_text,
                        execution_brief=execution_brief,
                    ),
                    force_refine=True,
                    workspace_root=workspace_root,
                    tool_reporter=tool_reporter,
                    tool_registry=tool_registry,
                    tool_executor=tool_executor,
                    progress_callback=progress_callback,
                )
        else:
            feedback_translation = self._translate_user_text(session_id, content, kind="feedback")
            self._refine_session(
                session_id,
                prompt_for_model=prompt_translation.translated_text,
                original_feedback=content,
                feedback_for_model=feedback_translation.translated_text,
                workspace_root=workspace_root,
                tool_reporter=tool_reporter,
                tool_registry=tool_registry,
                tool_executor=tool_executor,
                progress_callback=progress_callback,
            )
        return self.orchestrator.store.get_session(session_id)

    async def reply_to_session_async(
        self,
        session_id: str,
        content: str,
        *,
        workspace_root: Path | None = None,
        tool_reporter: ToolExecutionReporter | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_executor: ToolExecutor | None = None,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> SessionRecord:
        session = self.orchestrator.store.get_session(session_id)
        self.orchestrator.store.append_message(session_id, role="user", kind="message", content=content)
        prompt_translation = await self._translate_user_text_async(session_id, session.prompt, kind="prompt")
        if session.status == "waiting_for_clarification":
            answer_translation = await self._translate_user_text_async(
                session_id,
                content,
                kind="clarification_answer",
            )
            decision = await self._record_stage_async(
                [],
                "clarifier_followup",
                lambda: self.orchestrator.clarifier.run_async(
                    prompt_translation.translated_text,
                    self.orchestrator.store.list_messages(session_id),
                ),
                progress_callback=progress_callback,
            )
            if decision.need_clarification and decision.questions:
                clarification_prompt = self.clarification_prompt(ClarificationTurn(questions=decision.questions))
                self.orchestrator.store.append_message(
                    session_id,
                    role="assistant",
                    kind="clarification",
                    content=clarification_prompt,
                )
                self.orchestrator.store.update_session(
                    session_id,
                    status="waiting_for_clarification",
                    clarification_question=clarification_prompt,
                    execution_brief=None,
                    latest_summary="Waiting for clarification.",
                )
            else:
                execution_brief = decision.execution_brief or "Proceed with a minimal, correct implementation."
                await self._execute_session_async(
                    session_id,
                    prompt_for_model=prompt_translation.translated_text,
                    clarification=ClarificationTurn(
                        answer=answer_translation.translated_text,
                        execution_brief=execution_brief,
                    ),
                    force_refine=True,
                    workspace_root=workspace_root,
                    tool_reporter=tool_reporter,
                    tool_registry=tool_registry,
                    tool_executor=tool_executor,
                    progress_callback=progress_callback,
                )
        else:
            feedback_translation = await self._translate_user_text_async(session_id, content, kind="feedback")
            await self._refine_session_async(
                session_id,
                prompt_for_model=prompt_translation.translated_text,
                original_feedback=content,
                feedback_for_model=feedback_translation.translated_text,
                workspace_root=workspace_root,
                tool_reporter=tool_reporter,
                tool_registry=tool_registry,
                tool_executor=tool_executor,
                progress_callback=progress_callback,
            )
        return self.orchestrator.store.get_session(session_id)

    def generate_one_shot(
        self,
        prompt: str,
        *,
        workspace_root: Path | None = None,
        tool_reporter: ToolExecutionReporter | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_executor: ToolExecutor | None = None,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> GenerationResult:
        session = self.orchestrator.store.create_session(prompt, status="created")
        self.orchestrator.store.append_message(session.session_id, role="user", kind="prompt", content=prompt)
        prompt_translation = self._translate_user_text(session.session_id, prompt, kind="prompt")
        history = self.orchestrator.store.list_messages(session.session_id)
        decision = self._record_stage(
            [],
            "clarifier",
            lambda: self.orchestrator.clarifier.run(prompt_translation.translated_text, history),
            progress_callback=progress_callback,
        )
        execution_brief = decision.execution_brief or "Proceed with a minimal, correct implementation."
        return self._execute_session(
            session.session_id,
            prompt_for_model=prompt_translation.translated_text,
            clarification=ClarificationTurn(
                execution_brief=execution_brief,
            ),
            force_refine=True,
            workspace_root=workspace_root,
            tool_reporter=tool_reporter,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
            progress_callback=progress_callback,
        )

    async def generate_one_shot_async(
        self,
        prompt: str,
        *,
        workspace_root: Path | None = None,
        tool_reporter: ToolExecutionReporter | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_executor: ToolExecutor | None = None,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> GenerationResult:
        session = self.orchestrator.store.create_session(prompt, status="created")
        self.orchestrator.store.append_message(session.session_id, role="user", kind="prompt", content=prompt)
        prompt_translation = await self._translate_user_text_async(session.session_id, prompt, kind="prompt")
        history = self.orchestrator.store.list_messages(session.session_id)
        decision = await self._record_stage_async(
            [],
            "clarifier",
            lambda: self.orchestrator.clarifier.run_async(prompt_translation.translated_text, history),
            progress_callback=progress_callback,
        )
        execution_brief = decision.execution_brief or "Proceed with a minimal, correct implementation."
        return await self._execute_session_async(
            session.session_id,
            prompt_for_model=prompt_translation.translated_text,
            clarification=ClarificationTurn(
                execution_brief=execution_brief,
            ),
            force_refine=True,
            workspace_root=workspace_root,
            tool_reporter=tool_reporter,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
            progress_callback=progress_callback,
        )

    def _execute_session(
        self,
        session_id: str,
        *,
        prompt_for_model: str,
        clarification: ClarificationTurn,
        force_refine: bool,
        workspace_root: Path | None,
        tool_reporter: ToolExecutionReporter | None,
        tool_registry: ToolRegistry | None,
        tool_executor: ToolExecutor | None,
        progress_callback: Callable[[str, str], None] | None,
    ) -> GenerationResult:
        session = self.orchestrator.store.get_session(session_id)
        task_profile = self.orchestrator.task_classifier.classify(prompt_for_model)
        stage_metrics: list[StageMetric] = []
        history = self.orchestrator.store.list_messages(session_id)
        execution_brief = clarification.execution_brief.strip() or clarification.answer_or_brief()
        active_registry, active_executor = self._resolve_tooling(
            workspace_root=workspace_root,
            tool_reporter=tool_reporter,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
        )
        context = self._build_context(
            session_id,
            prompt_for_model,
            execution_brief,
            history,
            stage_metrics,
            progress_callback=progress_callback,
        )
        candidates = self._draft_and_review_candidates(
            session_id,
            prompt_for_model,
            execution_brief,
            context,
            stage_metrics,
            progress_callback=progress_callback,
        )
        selected = self._select_candidate(candidates, stage_metrics)
        final_draft = CodeDraft(code=selected.code)
        final_review = selected.metadata["review"]
        final_verification = selected.metadata["verification"]
        repair_report: ValidationReport | None = None

        if force_refine or not final_review.accept or not final_verification.passed:
            final_draft, final_review, final_verification, repair_report = self._repair_cycle(
                session_id,
                prompt_for_model,
                execution_brief,
                context,
                final_draft,
                final_review,
                final_verification,
                user_feedback=None,
                stage_metrics=stage_metrics,
                progress_callback=progress_callback,
            )

        self.orchestrator.store.append_message(session_id, role="assistant", kind="code", content=final_draft.code)
        self.orchestrator.store.update_session(
            session_id,
            status="complete",
            clarification_question=None,
            execution_brief=execution_brief,
            latest_code=final_draft.code,
            latest_summary=self._build_latest_summary(
                review=final_review,
                verification=final_verification,
                repaired=repair_report is not None,
            ),
        )
        validation_report = self.orchestrator.lua_static_validator.validate(
            prompt_for_model, selected.code, task_profile
        )
        return GenerationResult(
            prompt=session.prompt,
            task_profile=task_profile,
            clarification=clarification,
            retrieved_examples=self.orchestrator.dataset.retrieve(
                prompt_for_model,
                top_k=self.orchestrator.settings.top_k_examples,
                task_profile=task_profile,
            ),
            initial_code=selected.code,
            final_code=final_draft.code,
            validation_report=validation_report,
            repair_report=repair_report,
            candidates=candidates,
            selected_candidate_index=selected.index,
            stage_metrics=stage_metrics,
            metadata={
                "session_id": session_id,
                "translated_prompt": prompt_for_model,
                "review_issue_count": len(final_review.issues),
                "verification_summary": final_verification.summary,
            },
        )

    async def _execute_session_async(
        self,
        session_id: str,
        *,
        prompt_for_model: str,
        clarification: ClarificationTurn,
        force_refine: bool,
        workspace_root: Path | None,
        tool_reporter: ToolExecutionReporter | None,
        tool_registry: ToolRegistry | None,
        tool_executor: ToolExecutor | None,
        progress_callback: Callable[[str, str], None] | None,
    ) -> GenerationResult:
        session = self.orchestrator.store.get_session(session_id)
        task_profile = self.orchestrator.task_classifier.classify(prompt_for_model)
        stage_metrics: list[StageMetric] = []
        history = self.orchestrator.store.list_messages(session_id)
        execution_brief = clarification.execution_brief.strip() or clarification.answer_or_brief()
        active_registry, active_executor = self._resolve_tooling(
            workspace_root=workspace_root,
            tool_reporter=tool_reporter,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
        )
        context = await self._build_context_async(
            session_id,
            prompt_for_model,
            execution_brief,
            history,
            stage_metrics,
            progress_callback=progress_callback,
        )
        candidates = await self._draft_and_review_candidates_async(
            session_id,
            prompt_for_model,
            execution_brief,
            context,
            stage_metrics,
            progress_callback=progress_callback,
        )
        selected = self._select_candidate(candidates, stage_metrics)
        final_draft = CodeDraft(code=selected.code)
        final_review = selected.metadata["review"]
        final_verification = selected.metadata["verification"]
        repair_report: ValidationReport | None = None

        if force_refine or not final_review.accept or not final_verification.passed:
            (
                final_draft,
                final_review,
                final_verification,
                repair_report,
            ) = await self._repair_cycle_async(
                session_id,
                prompt_for_model,
                execution_brief,
                context,
                final_draft,
                final_review,
                final_verification,
                user_feedback=None,
                stage_metrics=stage_metrics,
                progress_callback=progress_callback,
            )

        self.orchestrator.store.append_message(session_id, role="assistant", kind="code", content=final_draft.code)
        self.orchestrator.store.update_session(
            session_id,
            status="complete",
            clarification_question=None,
            execution_brief=execution_brief,
            latest_code=final_draft.code,
            latest_summary=self._build_latest_summary(
                review=final_review,
                verification=final_verification,
                repaired=repair_report is not None,
            ),
        )
        validation_report = self.orchestrator.lua_static_validator.validate(
            prompt_for_model, selected.code, task_profile
        )
        return GenerationResult(
            prompt=session.prompt,
            task_profile=task_profile,
            clarification=clarification,
            retrieved_examples=self.orchestrator.dataset.retrieve(
                prompt_for_model,
                top_k=self.orchestrator.settings.top_k_examples,
                task_profile=task_profile,
            ),
            initial_code=selected.code,
            final_code=final_draft.code,
            validation_report=validation_report,
            repair_report=repair_report,
            candidates=candidates,
            selected_candidate_index=selected.index,
            stage_metrics=stage_metrics,
            metadata={
                "session_id": session_id,
                "translated_prompt": prompt_for_model,
                "review_issue_count": len(final_review.issues),
                "verification_summary": final_verification.summary,
            },
        )

    def _refine_session(
        self,
        session_id: str,
        *,
        prompt_for_model: str,
        original_feedback: str,
        feedback_for_model: str,
        workspace_root: Path | None,
        tool_reporter: ToolExecutionReporter | None,
        tool_registry: ToolRegistry | None,
        tool_executor: ToolExecutor | None,
        progress_callback: Callable[[str, str], None] | None,
    ) -> GenerationResult:
        session = self.orchestrator.store.get_session(session_id)
        history = self.orchestrator.store.list_messages(session_id)
        execution_brief = session.execution_brief or "Refinement session."
        task_profile = self.orchestrator.task_classifier.classify(prompt_for_model)
        stage_metrics: list[StageMetric] = []
        active_registry, active_executor = self._resolve_tooling(
            workspace_root=workspace_root,
            tool_reporter=tool_reporter,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
        )
        context = self._build_context(
            session_id,
            prompt_for_model,
            feedback_for_model,
            history,
            stage_metrics,
            progress_callback=progress_callback,
        )
        current_code = session.latest_code or ""
        current_review = ReviewDecision(
            accept=False,
            issues=(
                ReviewIssue(
                    title="User refinement request",
                    description=feedback_for_model,
                    severity="medium",
                ),
            ),
        )
        current_verification = self.orchestrator.lua_validator.verify(prompt_for_model, current_code)
        final_draft, final_review, final_verification, repair_report = self._repair_cycle(
            session_id,
            prompt_for_model,
            execution_brief,
            context,
            CodeDraft(code=current_code),
            current_review,
            current_verification,
            user_feedback=feedback_for_model,
            stage_metrics=stage_metrics,
            progress_callback=progress_callback,
        )
        self.orchestrator.store.append_message(session_id, role="assistant", kind="code", content=final_draft.code)
        self.orchestrator.store.update_session(
            session_id,
            status="complete",
            execution_brief=execution_brief,
            latest_code=final_draft.code,
            latest_summary=self._build_latest_summary(
                review=final_review,
                verification=final_verification,
                repaired=True,
            ),
        )
        return GenerationResult(
            prompt=session.prompt,
            task_profile=task_profile,
            clarification=ClarificationTurn(
                questions=((session.clarification_question or "").strip(),) if session.clarification_question else (),
                answer=original_feedback,
            ),
            retrieved_examples=self.orchestrator.dataset.retrieve(
                prompt_for_model,
                top_k=self.orchestrator.settings.top_k_examples,
                task_profile=task_profile,
            ),
            initial_code=current_code,
            final_code=final_draft.code,
            validation_report=self.orchestrator.lua_static_validator.validate(
                prompt_for_model, current_code, task_profile
            ),
            repair_report=repair_report,
            candidates=[],
            selected_candidate_index=1,
            stage_metrics=stage_metrics,
            metadata={
                "session_id": session_id,
                "feedback": original_feedback,
                "translated_prompt": prompt_for_model,
            },
        )

    async def _refine_session_async(
        self,
        session_id: str,
        *,
        prompt_for_model: str,
        original_feedback: str,
        feedback_for_model: str,
        workspace_root: Path | None,
        tool_reporter: ToolExecutionReporter | None,
        tool_registry: ToolRegistry | None,
        tool_executor: ToolExecutor | None,
        progress_callback: Callable[[str, str], None] | None,
    ) -> GenerationResult:
        session = self.orchestrator.store.get_session(session_id)
        history = self.orchestrator.store.list_messages(session_id)
        execution_brief = session.execution_brief or "Refinement session."
        task_profile = self.orchestrator.task_classifier.classify(prompt_for_model)
        stage_metrics: list[StageMetric] = []
        active_registry, active_executor = self._resolve_tooling(
            workspace_root=workspace_root,
            tool_reporter=tool_reporter,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
        )
        context = await self._build_context_async(
            session_id,
            prompt_for_model,
            feedback_for_model,
            history,
            stage_metrics,
            progress_callback=progress_callback,
        )
        current_code = session.latest_code or ""
        current_review = ReviewDecision(
            accept=False,
            issues=(
                ReviewIssue(
                    title="User refinement request",
                    description=feedback_for_model,
                    severity="medium",
                ),
            ),
        )
        current_verification = self.orchestrator.lua_validator.verify(prompt_for_model, current_code)
        (
            final_draft,
            final_review,
            final_verification,
            repair_report,
        ) = await self._repair_cycle_async(
            session_id,
            prompt_for_model,
            execution_brief,
            context,
            CodeDraft(code=current_code),
            current_review,
            current_verification,
            user_feedback=feedback_for_model,
            stage_metrics=stage_metrics,
            progress_callback=progress_callback,
        )
        self.orchestrator.store.append_message(session_id, role="assistant", kind="code", content=final_draft.code)
        self.orchestrator.store.update_session(
            session_id,
            status="complete",
            execution_brief=execution_brief,
            latest_code=final_draft.code,
            latest_summary=self._build_latest_summary(
                review=final_review,
                verification=final_verification,
                repaired=True,
            ),
        )
        return GenerationResult(
            prompt=session.prompt,
            task_profile=task_profile,
            clarification=ClarificationTurn(
                questions=((session.clarification_question or "").strip(),) if session.clarification_question else (),
                answer=original_feedback,
            ),
            retrieved_examples=self.orchestrator.dataset.retrieve(
                prompt_for_model,
                top_k=self.orchestrator.settings.top_k_examples,
                task_profile=task_profile,
            ),
            initial_code=current_code,
            final_code=final_draft.code,
            validation_report=self.orchestrator.lua_static_validator.validate(
                prompt_for_model, current_code, task_profile
            ),
            repair_report=repair_report,
            candidates=[],
            selected_candidate_index=1,
            stage_metrics=stage_metrics,
            metadata={
                "session_id": session_id,
                "feedback": original_feedback,
                "translated_prompt": prompt_for_model,
            },
        )

    def _build_context(
        self,
        session_id: str,
        prompt: str,
        execution_brief: str,
        history: list[dict[str, object]],
        stage_metrics: list[StageMetric],
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> ContextBundle:
        knowledge_chunks = self._record_stage(
            stage_metrics,
            "kb_search",
            lambda: self.orchestrator.kb.search(f"{prompt}\n{execution_brief}", limit=6),
            progress_callback=progress_callback,
        )
        context = self._record_stage(
            stage_metrics,
            "context_agent",
            lambda: self.orchestrator.context_agent.run(
                execution_brief,
                "",
                knowledge_chunks,
                history,
            ),
            progress_callback=progress_callback,
        )
        return context

    async def _build_context_async(
        self,
        session_id: str,
        prompt: str,
        execution_brief: str,
        history: list[dict[str, object]],
        stage_metrics: list[StageMetric],
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> ContextBundle:
        knowledge_chunks = self._record_stage(
            stage_metrics,
            "kb_search",
            lambda: self.orchestrator.kb.search(f"{prompt}\n{execution_brief}", limit=6),
            progress_callback=progress_callback,
        )
        context = await self._record_stage_async(
            stage_metrics,
            "context_agent",
            lambda: self.orchestrator.context_agent.run_async(
                execution_brief,
                "",
                knowledge_chunks,
                history,
            ),
            progress_callback=progress_callback,
        )
        return context

    def _draft_and_review_candidates(
        self,
        session_id: str,
        prompt: str,
        execution_brief: str,
        context: ContextBundle,
        stage_metrics: list[StageMetric],
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> list[CandidateResult]:
        results: list[CandidateResult] = []
        for index in range(1, self.orchestrator.settings.candidate_count + 1):
            strategy = DEFAULT_DRAFT_STRATEGIES[min(index - 1, len(DEFAULT_DRAFT_STRATEGIES) - 1)]
            draft = self._record_stage(
                stage_metrics,
                f"coder_{index}",
                lambda s=strategy: self.orchestrator.coder.run(
                    execution_brief=execution_brief,
                    context=context,
                    strategy=s,
                ),
                progress_callback=progress_callback,
            )
            review = self._record_stage(
                stage_metrics,
                f"reviewer_{index}",
                lambda d=draft.code: self.orchestrator.reviewer.run(
                    execution_brief=execution_brief,
                    context=context,
                    code=d,
                ),
                progress_callback=progress_callback,
            )
            verification = self._record_stage(
                stage_metrics,
                f"verifier_{index}",
                lambda d=draft.code: self.orchestrator.lua_validator.verify(prompt, d),
                progress_callback=progress_callback,
            )
            score = self._score_candidate(draft, review, verification)
            results.append(
                CandidateResult(
                    index=index,
                    code=draft.code,
                    report=self.orchestrator.lua_static_validator.validate(
                        prompt,
                        draft.code,
                        self.orchestrator.task_classifier.classify(prompt),
                    ),
                    score=score,
                    strategy=strategy,
                    metadata={
                        "review": review,
                        "verification": verification,
                        "draft": draft,
                    },
                )
            )
        return results

    async def _draft_and_review_candidates_async(
        self,
        session_id: str,
        prompt: str,
        execution_brief: str,
        context: ContextBundle,
        stage_metrics: list[StageMetric],
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> list[CandidateResult]:
        results: list[CandidateResult] = []
        for index in range(1, self.orchestrator.settings.candidate_count + 1):
            strategy = DEFAULT_DRAFT_STRATEGIES[min(index - 1, len(DEFAULT_DRAFT_STRATEGIES) - 1)]
            draft = await self._record_stage_async(
                stage_metrics,
                f"coder_{index}",
                lambda s=strategy: self.orchestrator.coder.run_async(
                    execution_brief=execution_brief,
                    context=context,
                    strategy=s,
                ),
                progress_callback=progress_callback,
            )
            review = await self._record_stage_async(
                stage_metrics,
                f"reviewer_{index}",
                lambda d=draft.code: self.orchestrator.reviewer.run_async(
                    execution_brief=execution_brief,
                    context=context,
                    code=d,
                ),
                progress_callback=progress_callback,
            )
            verification = self._record_stage(
                stage_metrics,
                f"verifier_{index}",
                lambda d=draft.code: self.orchestrator.lua_validator.verify(prompt, d),
                progress_callback=progress_callback,
            )
            score = self._score_candidate(draft, review, verification)
            results.append(
                CandidateResult(
                    index=index,
                    code=draft.code,
                    report=self.orchestrator.lua_static_validator.validate(
                        prompt,
                        draft.code,
                        self.orchestrator.task_classifier.classify(prompt),
                    ),
                    score=score,
                    strategy=strategy,
                    metadata={
                        "review": review,
                        "verification": verification,
                        "draft": draft,
                    },
                )
            )
        return results

    def _repair_cycle(
        self,
        session_id: str,
        prompt: str,
        execution_brief: str,
        context: ContextBundle,
        draft: CodeDraft,
        review: ReviewDecision,
        verification,
        *,
        user_feedback: str | None,
        stage_metrics: list[StageMetric],
        progress_callback: Callable[[str, str], None] | None = None,
    ):
        repaired = self._record_stage(
            stage_metrics,
            "repair_agent",
            lambda: self.orchestrator.repair.run(
                execution_brief=execution_brief,
                context=context,
                current_code=draft.code,
                review=review,
                verifier=verification,
                user_feedback=user_feedback,
            ),
            progress_callback=progress_callback,
        )
        repaired_review = self._record_stage(
            stage_metrics,
            "reviewer_repair",
            lambda: self.orchestrator.reviewer.run(
                execution_brief=execution_brief,
                context=context,
                code=repaired.code,
                verifier_summary=verification.summary,
            ),
            progress_callback=progress_callback,
        )
        repaired_verification = self._record_stage(
            stage_metrics,
            "verifier_repair",
            lambda: self.orchestrator.lua_validator.verify(prompt, repaired.code),
            progress_callback=progress_callback,
        )
        repair_report = self.orchestrator.lua_static_validator.validate(
            prompt,
            repaired.code,
            self.orchestrator.task_classifier.classify(prompt),
        )
        return repaired, repaired_review, repaired_verification, repair_report

    async def _repair_cycle_async(
        self,
        session_id: str,
        prompt: str,
        execution_brief: str,
        context: ContextBundle,
        draft: CodeDraft,
        review: ReviewDecision,
        verification,
        *,
        user_feedback: str | None,
        stage_metrics: list[StageMetric],
        progress_callback: Callable[[str, str], None] | None = None,
    ):
        repaired = await self._record_stage_async(
            stage_metrics,
            "repair_agent",
            lambda: self.orchestrator.repair.run_async(
                execution_brief=execution_brief,
                context=context,
                current_code=draft.code,
                review=review,
                verifier=verification,
                user_feedback=user_feedback,
            ),
            progress_callback=progress_callback,
        )
        repaired_review = await self._record_stage_async(
            stage_metrics,
            "reviewer_repair",
            lambda: self.orchestrator.reviewer.run_async(
                execution_brief=execution_brief,
                context=context,
                code=repaired.code,
                verifier_summary=verification.summary,
            ),
            progress_callback=progress_callback,
        )
        repaired_verification = self._record_stage(
            stage_metrics,
            "verifier_repair",
            lambda: self.orchestrator.lua_validator.verify(prompt, repaired.code),
            progress_callback=progress_callback,
        )
        repair_report = self.orchestrator.lua_static_validator.validate(
            prompt,
            repaired.code,
            self.orchestrator.task_classifier.classify(prompt),
        )
        return repaired, repaired_review, repaired_verification, repair_report

    def _translate_user_text(self, session_id: str, text: str, *, kind: str) -> TranslationDecision:
        source_language = detect_language(text)
        if source_language == "en":
            return TranslationDecision(source_language="en", target_language="en", translated_text=text)
        decision = self._timed(
            f"translator_{kind}",
            lambda: self.orchestrator.translator.run(text, source_language),
        )
        return decision

    async def _translate_user_text_async(self, session_id: str, text: str, *, kind: str) -> TranslationDecision:
        source_language = detect_language(text)
        if source_language == "en":
            return TranslationDecision(source_language="en", target_language="en", translated_text=text)
        decision = await self._timed_async(
            f"translator_{kind}",
            lambda: self.orchestrator.translator.run_async(text, source_language),
        )
        return decision

    @staticmethod
    def _build_latest_summary(*, review: ReviewDecision, verification, repaired: bool) -> str:
        if not verification.passed:
            prefix = (
                "Repaired code still has validation issues." if repaired else "Generated code has validation issues."
            )
            return f"{prefix} {verification.summary}".strip()
        if review.issues:
            issue_count = len(review.issues)
            noun = "issue" if issue_count == 1 else "issues"
            prefix = (
                "Repaired code passed validation with review findings."
                if repaired
                else "Generated code passed validation with review findings."
            )
            return f"{prefix} {issue_count} review {noun} flagged."
        return "Repaired code passed validation." if repaired else "Generated code passed validation."

    def _resolve_tooling(
        self,
        *,
        workspace_root: Path | None,
        tool_reporter: ToolExecutionReporter | None,
        tool_registry: ToolRegistry | None,
        tool_executor: ToolExecutor | None,
    ) -> tuple[ToolRegistry, ToolExecutor]:
        if tool_registry is not None and tool_executor is not None:
            return tool_registry, tool_executor
        resolved_root = workspace_root or self.orchestrator.settings.workspace_root
        return build_local_tooling(resolved_root, reporter=tool_reporter)

    @staticmethod
    def _score_candidate(draft: CodeDraft, review: ReviewDecision, verification) -> float:
        score = 100.0
        if review.accept:
            score += 15.0
        score -= len(review.issues) * 8.0
        score += 20.0 if verification.passed else -20.0
        score -= len(verification.issues) * 6.0
        score -= max(draft.code.count("\n") - 24, 0) * 0.5
        return score

    def _select_candidate(self, candidates: list[CandidateResult], stage_metrics: list[StageMetric]) -> CandidateResult:
        return self._record_stage(
            stage_metrics,
            "candidate_selection",
            lambda: max(candidates, key=lambda item: (item.score, -item.index)),
        )

    @staticmethod
    def _timed(name: str, fn):
        started = perf_counter()
        result = fn()
        _ = perf_counter() - started
        return result

    @staticmethod
    async def _timed_async(name: str, fn):
        started = perf_counter()
        result = await fn()
        _ = perf_counter() - started
        return result


    @staticmethod
    def _record_stage(
        metrics: list[StageMetric],
        name: str,
        fn,
        *,
        progress_callback: Callable[[str, str], None] | None = None,
    ):
        if progress_callback is not None:
            progress_callback(name, "started")
        started = perf_counter()
        result = fn()
        duration_ms = (perf_counter() - started) * 1000
        metrics.append(StageMetric(name=name, duration_ms=duration_ms))
        if progress_callback is not None:
            progress_callback(name, "completed")
        return result

    @staticmethod
    async def _record_stage_async(
        metrics: list[StageMetric],
        name: str,
        fn,
        *,
        progress_callback: Callable[[str, str], None] | None = None,
    ):
        if progress_callback is not None:
            progress_callback(name, "started")
        started = perf_counter()
        result = await fn()
        duration_ms = (perf_counter() - started) * 1000
        metrics.append(StageMetric(name=name, duration_ms=duration_ms))
        if progress_callback is not None:
            progress_callback(name, "completed")
        return result


def build_lua_codegen_mode(settings: Settings) -> LuaCodegenMode:
    settings.validate_runtime()
    store = SQLiteStore(settings.database_path)
    kb = LocalKnowledgeBase(settings.data_dir, store)
    kb.rebuild()
    ollama = OllamaClient(settings)
    orchestrator = LuaCodegenOrchestrator(
        settings=settings,
        store=store,
        kb=kb,
        ollama=ollama,
        translator=TranslatorAgent(ollama),
        clarifier=ClarifierAgent(ollama),
        context_agent=ContextAgent(ollama),
        coder=CoderAgent(ollama),
        reviewer=ReviewerAgent(ollama),
        repair=RepairAgent(ollama),
        lua_validator=LuaValidator(),
        task_classifier=TaskClassifier(),
        lua_static_validator=LuaStaticValidator(),
        dataset=KnowledgeBase.from_files(
            Path(settings.data_dir) / "localscript_rules.md",
            Path(settings.data_dir) / "public_localscript_dataset.md",
        ),
    )
    return LuaCodegenMode(orchestrator)

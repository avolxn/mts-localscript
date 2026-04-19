from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from math import log
from pathlib import Path

from localscript.core.schemas import KnowledgeExample, RetrievedExample, TaskProfile

TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]+")
SECTION_RE = re.compile(r"^##\s+2\.\d+\s+(.+)$", re.MULTILINE)
FIELD_WEIGHTS = {
    "title": 2.5,
    "prompt": 2.2,
    "context_json": 1.2,
    "expected_code": 1.8,
    "tags": 1.5,
}


@dataclass(slots=True)
class KnowledgeBase:
    rules_text: str
    examples: list[KnowledgeExample]
    _indexed: list[_IndexedExample] = field(init=False, repr=False)
    _avg_field_lengths: dict[str, float] = field(init=False, repr=False)
    _doc_frequencies: dict[str, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._indexed = [_index_example(example) for example in self.examples]
        self._avg_field_lengths = self._compute_average_field_lengths()
        self._doc_frequencies = self._compute_doc_frequencies()

    @classmethod
    def from_files(cls, rules_path: Path, dataset_path: Path) -> KnowledgeBase:
        rules_text = rules_path.read_text(encoding="utf-8").strip()
        examples = parse_public_dataset(dataset_path.read_text(encoding="utf-8"))
        return cls(rules_text=rules_text, examples=examples)

    def retrieve(self, query: str, top_k: int = 3, task_profile: TaskProfile | None = None) -> list[RetrievedExample]:
        query_terms = Counter(tokenize_list(query))
        scored: list[RetrievedExample] = []
        for indexed in self._indexed:
            if not indexed.field_lengths:
                continue
            score, breakdown = self._score_indexed_example(query_terms, indexed, task_profile)
            if score > 0:
                scored.append(RetrievedExample(example=indexed.example, score=score, score_breakdown=breakdown))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def _score_indexed_example(
        self,
        query_terms: Counter[str],
        indexed: _IndexedExample,
        task_profile: TaskProfile | None,
    ) -> tuple[float, dict[str, float]]:
        breakdown: dict[str, float] = {}
        total = 0.0
        for field_name, weight in FIELD_WEIGHTS.items():
            field_counter = indexed.field_tokens[field_name]
            if not field_counter:
                continue
            field_length = indexed.field_lengths[field_name]
            avg_field_length = self._avg_field_lengths.get(field_name, 1.0)
            field_score = 0.0
            for term, query_tf in query_terms.items():
                tf = field_counter.get(term, 0)
                if not tf:
                    continue
                idf = self._inverse_document_frequency(term)
                numerator = tf * (1.2 + 1.0)
                denominator = tf + 1.2 * (1 - 0.75 + 0.75 * (field_length / max(avg_field_length, 1.0)))
                field_score += query_tf * idf * (numerator / denominator)
            weighted = field_score * weight
            breakdown[field_name] = weighted
            total += weighted

        profile_bonus = 0.0
        if task_profile:
            if task_profile.environment == "lowcode" and any(
                tag in indexed.example.tags for tag in ("lowcode", "workflow")
            ):
                profile_bonus += 1.0
            if task_profile.task_type in indexed.example.tags:
                profile_bonus += 1.5
            overlap = len(set(task_profile.tags) & set(indexed.example.tags))
            profile_bonus += overlap * 0.4
        if profile_bonus:
            breakdown["profile_bonus"] = profile_bonus
            total += profile_bonus
        return total, breakdown

    def _compute_average_field_lengths(self) -> dict[str, float]:
        lengths: dict[str, list[int]] = {field_name: [] for field_name in FIELD_WEIGHTS}
        for indexed in self._indexed:
            for field_name, length in indexed.field_lengths.items():
                lengths[field_name].append(length)
        return {field_name: (sum(values) / len(values) if values else 1.0) for field_name, values in lengths.items()}

    def _compute_doc_frequencies(self) -> dict[str, int]:
        frequencies: dict[str, int] = {}
        for indexed in self._indexed:
            all_tokens: set[str] = set()
            for field_counter in indexed.field_tokens.values():
                all_tokens.update(field_counter)
            for token in all_tokens:
                frequencies[token] = frequencies.get(token, 0) + 1
        return frequencies

    def _inverse_document_frequency(self, token: str) -> float:
        total_docs = max(len(self._indexed), 1)
        doc_freq = self._doc_frequencies.get(token, 0)
        return log(1 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))


@dataclass(slots=True)
class _IndexedExample:
    example: KnowledgeExample
    field_tokens: dict[str, Counter[str]]
    field_lengths: dict[str, int]


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def tokenize_list(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def parse_public_dataset(markdown: str) -> list[KnowledgeExample]:
    matches = list(SECTION_RE.finditer(markdown))
    examples: list[KnowledgeExample] = []
    for index, match in enumerate(matches, start=1):
        start = match.start()
        end = matches[index].start() if index < len(matches) else len(markdown)
        section = markdown[start:end]
        title = match.group(1).strip()
        request = _extract_subsection_text(section, "User Request")
        expected = _extract_first_code_block(_extract_subsection_text(section, "Expected Answer"))
        context = _extract_context_code_block(section)
        tags = tuple(_derive_tags(title, request, expected))
        if request and expected:
            examples.append(
                KnowledgeExample(
                    identifier=f"example-{index}",
                    title=title,
                    prompt=request,
                    expected_code=expected,
                    context_json=context,
                    tags=tags,
                )
            )
    return examples


def _extract_subsection_text(section: str, title: str) -> str:
    pattern = re.compile(
        rf"^##\s+.+?{re.escape(title)}\s*$\n(.*?)(?=^##\s+.+?$|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(section)
    return match.group(1).strip() if match else ""


def _extract_first_code_block(section: str) -> str:
    match = re.search(r"```[a-zA-Z0-9_+-]*\n(.*?)```", section, re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_context_code_block(section: str) -> str | None:
    blocks = re.findall(r"```json\n(.*?)```", section, re.DOTALL)
    if not blocks:
        return None
    for block in blocks:
        candidate = block.strip()
        if '"wf"' in candidate:
            return candidate
    return blocks[0].strip()


def _derive_tags(title: str, request: str, expected: str) -> Iterable[str]:
    text = " ".join([title, request, expected]).lower()
    if "last" in text and ("array" in text or "email" in text):
        yield "array_last_element"
    if "increment" in text or "try_count" in text:
        yield "counter_increment"
    if "id" in text and "entity_id" in text and "call" in text and "nil" in expected.lower():
        yield "field_cleanup"
    if "iso" in text or "yyyymmdd" in text or "hhmmss" in text:
        yield "iso_time_format"
    if "unix" in text and "time" in text:
        yield "unix_time"
    if "discount" in text and "markdown" in text:
        yield "array_filter"
    if "items" in text and "ensurearray" in expected.lower():
        yield "array_normalization"
    if "array" in text or "list" in text:
        yield "arrays"
    if "time" in text or "iso" in text or "unix" in text:
        yield "time"
    if "wf.vars" in expected or "wf.initvariables" in text:
        yield "workflow"
    if "_utils.array" in expected:
        yield "lowcode"
    if "filter" in text:
        yield "filtering"


def export_examples_json(dataset_path: Path, output_path: Path) -> None:
    examples = parse_public_dataset(dataset_path.read_text(encoding="utf-8"))
    serializable = [
        {
            "identifier": example.identifier,
            "title": example.title,
            "prompt": example.prompt,
            "expected_code": example.expected_code,
            "context_json": example.context_json,
            "tags": list(example.tags),
        }
        for example in examples
    ]
    output_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")


def _index_example(example: KnowledgeExample) -> _IndexedExample:
    fields = {
        "title": example.title,
        "prompt": example.prompt,
        "context_json": example.context_json or "",
        "expected_code": example.expected_code,
        "tags": " ".join(example.tags),
    }
    counters = {name: Counter(tokenize_list(value)) for name, value in fields.items()}
    lengths = {name: sum(counter.values()) for name, counter in counters.items()}
    return _IndexedExample(example=example, field_tokens=counters, field_lengths=lengths)

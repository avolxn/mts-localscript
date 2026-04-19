from pathlib import Path

from localscript.core.knowledge import KnowledgeBase, parse_public_dataset


def test_parse_public_dataset_extracts_examples() -> None:
    dataset_path = Path("data/public_localscript_dataset.md")
    examples = parse_public_dataset(dataset_path.read_text(encoding="utf-8"))
    assert len(examples) == 8
    assert examples[0].title == "1. Last Element of an Array"
    assert "wf.vars.emails" in examples[0].expected_code


def test_retrieve_prefers_relevant_examples() -> None:
    kb = KnowledgeBase.from_files(
        rules_path=Path("data/localscript_rules.md"),
        dataset_path=Path("data/public_localscript_dataset.md"),
    )
    results = kb.retrieve("Convert recallTime to unix format", top_k=2)
    assert results
    assert any("Time Conversion" in item.example.title for item in results)

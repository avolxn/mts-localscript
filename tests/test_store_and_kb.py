from pathlib import Path

from localscript.storage import LocalKnowledgeBase, SQLiteStore


def test_sqlite_store_persists_session_and_messages(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "localscript.db")
    session = store.create_session("Return 42")
    store.append_message(session.session_id, role="user", kind="prompt", content="Return 42")
    detail_messages = store.list_messages(session.session_id)
    assert detail_messages[0]["content"] == "Return 42"


def test_local_kb_indexes_and_searches(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "rules.md").write_text("# Rules\nUse wf.vars for workflow variables.", encoding="utf-8")
    (data_dir / "patterns.md").write_text("# Time\nConvert timestamps to unix time with 86400.", encoding="utf-8")
    store = SQLiteStore(tmp_path / "localscript.db")
    kb = LocalKnowledgeBase(data_dir, store)
    kb.rebuild()
    results = kb.search("unix time", limit=2)
    assert results
    assert any("86400" in chunk.content for chunk in results)


def test_local_kb_search_handles_punctuation_in_query(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "rules.md").write_text("# Rules\nUse wf.vars for workflow variables.", encoding="utf-8")
    store = SQLiteStore(tmp_path / "localscript.db")
    kb = LocalKnowledgeBase(data_dir, store)
    kb.rebuild()
    results = kb.search("Convert wf.vars.recallTime to unix time.", limit=2)
    assert results
    assert any("wf.vars" in chunk.content for chunk in results)

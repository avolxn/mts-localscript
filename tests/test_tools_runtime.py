from pathlib import Path

from localscript.tools import build_local_tooling


def test_local_tooling_lists_reads_and_searches_files(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    lua_file = src / "factorial.lua"
    lua_file.write_text("local function factorial(n)\n  return n\nend\n", encoding="utf-8")

    _registry, executor = build_local_tooling(tmp_path)

    listed = executor.execute("list_project_files", {"pattern": "factorial", "limit": 10})
    assert "src/factorial.lua" in listed["paths"]

    read = executor.execute("read_text_file", {"path": "src/factorial.lua", "line": 1, "limit": 2})
    assert "local function factorial" in read["content"]

    search = executor.execute("search_text", {"pattern": "factorial", "glob": "*.lua", "limit": 10})
    assert any("factorial.lua" in hit for hit in search["hits"])


def test_local_tooling_runs_shell_commands(tmp_path: Path) -> None:
    _registry, executor = build_local_tooling(tmp_path)
    result = executor.execute("run_shell_command", {"command": "printf 'ok'", "timeout_seconds": 5})
    assert result["stdout"] == "ok"
    assert result["exit_code"] == 0


def test_local_tooling_writes_file(tmp_path: Path) -> None:
    _registry, executor = build_local_tooling(tmp_path)
    result = executor.execute("write_text_file", {"path": "out/generated.lua", "content": "local y = 2\n"})
    assert result["path"] == "out/generated.lua"
    assert (tmp_path / "out" / "generated.lua").read_text(encoding="utf-8") == "local y = 2\n"

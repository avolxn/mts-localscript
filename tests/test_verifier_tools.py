from types import SimpleNamespace

import pytest

from localscript.validation import LuaLspValidator, LuaValidator


def test_lua_validator_requires_lua_language_server(monkeypatch) -> None:
    monkeypatch.setattr(
        "localscript.validation.lua_lsp.shutil.which",
        lambda command: None,
    )
    with pytest.raises(RuntimeError, match="lua-language-server"):
        LuaValidator()


def test_lua_validator_runs_lua_lsp(monkeypatch) -> None:
    monkeypatch.setattr(
        "localscript.validation.lua_lsp.shutil.which",
        lambda command: ("/usr/bin/lua-language-server" if command == "lua-language-server" else None),
    )
    monkeypatch.setattr(
        "localscript.validation.lua_lsp.subprocess.run",
        lambda command, capture_output, text, timeout: SimpleNamespace(
            returncode=0,
            stdout="Initializing ...\nDiagnosis completed, no problems found\n",
            stderr="",
        ),
    )
    validator = LuaValidator()
    result = validator.verify(
        "Write factorial in Lua",
        "local function factorial(n)\n  return n\nend\nreturn factorial",
    )
    assert result.passed
    assert any(tool.tool == "lua_ls_check" for tool in result.tool_results)


def test_lua_lsp_validator_returns_semantic_issues(monkeypatch) -> None:
    monkeypatch.setattr(
        "localscript.validation.lua_lsp.shutil.which",
        lambda command: ("/usr/bin/lua-language-server" if command == "lua-language-server" else None),
    )
    monkeypatch.setattr(
        "localscript.validation.lua_lsp.subprocess.run",
        lambda command, capture_output, text, timeout: SimpleNamespace(
            returncode=1,
            stdout=(
                "Initializing ...\n"
                "workspace/generated.lua:1:11 [Warning] Undefined global `does_not_exist`. (undefined-global)\n"
                "Diagnosis complete, 1 problems found\n"
            ),
            stderr="",
        ),
    )

    validator = LuaLspValidator()
    tool_result, issues = validator.verify("local x = does_not_exist + 1\nreturn x")

    assert not tool_result.passed
    assert tool_result.tool == "lua_ls_check"
    assert issues
    assert issues[0].code == "lua_ls:undefined-global"
    assert issues[0].category == "semantics"

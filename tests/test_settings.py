import pytest

from localscript.core.settings import Settings


def test_settings_validate_runtime_requires_lua_language_server(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("localscript.core.settings.shutil.which", lambda command: None)

    with pytest.raises(RuntimeError, match="lua-language-server"):
        Settings(
            runtime_dir=tmp_path / ".localscript",
            database_path=tmp_path / ".localscript" / "localscript.db",
        ).validate_runtime()

from localscript.acp import Agent, Mode, api, messages, protocol


def test_localscript_acp_reexports_ui_modules() -> None:
    assert Agent.__module__ == "localscript_ui.acp.agent"
    assert Mode.__module__ == "localscript_ui.acp.agent"
    assert api.API is not None
    assert messages is not None
    assert protocol is not None

from localscript.agents.coder import CoderAgent
from localscript.utils import normalize_code
from localscript.agents.repair import RepairAgent


def test_normalize_code_joins_string_lists() -> None:
    assert normalize_code(["line1\n", "line2\n"]) == "line1\nline2"


def test_coder_parse_normalizes_list_code() -> None:
    agent = CoderAgent(client=None)  # type: ignore[arg-type]
    draft = agent._parse({"code": ["local x = 1\n", "return x\n"]})
    assert draft.code == "local x = 1\nreturn x"


def test_repair_parse_normalizes_list_code() -> None:
    agent = RepairAgent(client=None)  # type: ignore[arg-type]
    draft = agent._parse({"code": ["local x = 1\n", "return x\n"]})
    assert draft.code == "local x = 1\nreturn x"

from localscript.core.classifier import TaskClassifier
from localscript.validation import LuaStaticValidator


def test_validator_rejects_markdown_and_json() -> None:
    validator = LuaStaticValidator()
    report = validator.validate("factorial function", "```lua\nreturn 1\n```")
    assert not report.is_valid
    assert any(issue.code == "markdown" for issue in report.issues)


def test_validator_requires_workflow_access_when_prompt_has_wf() -> None:
    validator = LuaStaticValidator()
    profile = TaskClassifier().classify('Use {"wf": {"vars": {"emails": []}}}')
    report = validator.validate('Use {"wf": {"vars": {"emails": []}}}', "return emails[#emails]", profile)
    assert not report.is_valid
    assert any(issue.code == "workflow" for issue in report.issues)


def test_validator_flags_lowcode_array_creation_without_helper() -> None:
    validator = LuaStaticValidator()
    profile = TaskClassifier().classify('LowCode task with {"wf": {"vars": {"parsedCsv": []}}}')
    code = "local result = {}\ntable.insert(result, item)\nreturn result"
    report = validator.validate('LowCode task with {"wf": {"vars": {"parsedCsv": []}}}', code, profile)
    assert not report.is_valid
    assert any(issue.code == "array_helper" for issue in report.issues)


def test_validator_does_not_duplicate_lua_syntax_checks() -> None:
    validator = LuaStaticValidator()
    report = validator.validate("Write factorial in Lua", "local function factorial(n\n  return n")
    assert report.is_valid
    assert not any(issue.category == "syntax" for issue in report.issues)

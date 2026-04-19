from localscript.agents import TranslatorAgent
from localscript.core.language import detect_language


class FakeTranslatorClient:
    def generate_json(self, *, system: str, prompt: str, response_model):
        self.response_model = response_model
        return {
            "translated_text": "Convert wf.vars.recallTime to Unix time and return the timestamp.",
        }


def test_detect_language_handles_ascii_english_and_russian() -> None:
    assert detect_language("Return factorial of n in Lua") == "en"
    assert detect_language("Сделай функцию факториала на Lua") == "ru"


def test_translator_agent_translates() -> None:
    client = FakeTranslatorClient()
    agent = TranslatorAgent(client)
    decision = agent.run("Преобразуй wf.vars.recallTime в unix time", "ru")
    assert decision.source_language == "ru"
    assert decision.target_language == "en"
    assert "wf.vars.recallTime" in decision.translated_text
    assert decision.was_translated is True
    assert "translated_text" in client.response_model.model_json_schema()["properties"]

from localscript.agents import (
    BaseAgent,
    ClarifierAgent,
    CoderAgent,
    ContextAgent,
    RepairAgent,
    ReviewerAgent,
    TranslatorAgent,
)


def test_all_agents_implement_base_agent_interface() -> None:
    for agent_type in (
        TranslatorAgent,
        ClarifierAgent,
        ContextAgent,
        CoderAgent,
        ReviewerAgent,
        RepairAgent,
    ):
        assert issubclass(agent_type, BaseAgent)

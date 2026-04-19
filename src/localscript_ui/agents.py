from __future__ import annotations

from localscript.acp import build_agent_definition
from localscript_ui.agent_schema import Agent


class AgentReadError(Exception):
    """Problem reading the agents."""


async def read_agents() -> dict[str, Agent]:
    """Return the built-in LocalScript agent registry."""

    agent = build_agent_definition()
    return {agent["identity"]: agent}

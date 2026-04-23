from __future__ import annotations

import pathlib
from dataclasses import dataclass

from pydantic_ai import Agent, WebSearchTool

from brunel.agents.errors import AgentRunError
from brunel.agents.loader import resolve_agent
from brunel.agents.specs import AgentSpec, WebSearchCapability


@dataclass(frozen=True)
class ExecutionRequest:
    agent_name: str
    prompt: str
    cwd_path: pathlib.Path | None = None


@dataclass(frozen=True)
class ExecutionResult:
    agent_name: str
    output: str
    model: str


def execute(request: ExecutionRequest) -> ExecutionResult:
    loaded_agent = resolve_agent(request.agent_name, request.cwd_path)
    agent = _build_agent(loaded_agent.name, loaded_agent.spec)

    try:
        result = agent.run_sync(request.prompt)
    except Exception as exc:
        raise AgentRunError(f"agent `{loaded_agent.name}` failed to run: {exc}") from exc

    return ExecutionResult(
        agent_name=loaded_agent.name,
        output=result.output,
        model=loaded_agent.spec.model,
    )


def _build_agent(agent_name: str, spec: AgentSpec) -> Agent[None, str]:
    return Agent(
        spec.model,
        name=agent_name,
        instructions=spec.instructions,
        model_settings=spec.model_settings.model_dump(exclude_none=True) if spec.model_settings else None,
        builtin_tools=_build_builtin_tools(spec),
        defer_model_check=True,
    )


def _build_builtin_tools(spec: AgentSpec) -> list[WebSearchTool]:
    builtin_tools: list[WebSearchTool] = []
    for capability in spec.capabilities:
        if isinstance(capability, WebSearchCapability):
            builtin_tools.append(
                WebSearchTool(
                    search_context_size=capability.search_context_size,
                    blocked_domains=capability.blocked_domains,
                    allowed_domains=capability.allowed_domains,
                    max_uses=capability.max_uses,
                )
            )
    return builtin_tools

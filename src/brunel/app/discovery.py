import pathlib
from collections.abc import Generator

from brunel.app import dirs
from brunel.app.registries import (
    AgentPath,
    AgentPathRegistry,
    MCPPath,
    MCPPathRegistry,
    SkillPath,
    SkillPathRegistry,
    agent_path_registry,
    mcp_path_registry,
    skill_path_registry,
)


def discover_agents(
    cwd_path: pathlib.Path | None = None,
) -> Generator[AgentPath, None, None]:
    agent_seed_paths = dirs.get_agent_candidate_paths(cwd_path)

    # Agents can be a directory or agent.yaml
    for path in agent_seed_paths:
        if not path.exists():
            continue
        for item in path.iterdir():
            if item.is_dir() and (item / "agent.yaml").exists():
                yield AgentPath(path=item, spec_file=item / "agent.yaml")
            elif item.is_file():
                yield AgentPath(path=item, spec_file=item)


def discover_skills(
    cwd_path: pathlib.Path | None = None,
) -> Generator[SkillPath, None, None]:
    skill_seed_paths = dirs.get_skills_candidate_paths(cwd_path)

    # Skills are a directory with a SKILL.md file
    for path in skill_seed_paths:
        if not path.exists():
            continue
        for item in path.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                yield SkillPath(path=item, skill_file=item / "SKILL.md")


def discover_mcp(
    cwd_path: pathlib.Path | None = None,
) -> Generator[MCPPath, None, None]:
    mcp_seed_paths = dirs.get_mcp_candidate_paths(cwd_path)

    # MCP are a directory with an mcp.json file.
    for path in mcp_seed_paths:
        if path.is_dir() and (path / "mcp.json").exists():
            yield MCPPath(path=path, mcp_file=path / "mcp.json")


def discover_all_paths(
    cwd_path: pathlib.Path | None = None,
) -> tuple[AgentPathRegistry, SkillPathRegistry, MCPPathRegistry]:
    for agent_candidate in discover_agents(cwd_path):
        agent_path_registry.register(agent_candidate)
    for skill_candidate in discover_skills(cwd_path):
        skill_path_registry.register(skill_candidate)
    for mcp_candidate in discover_mcp(cwd_path):
        mcp_path_registry.register(mcp_candidate)
    return agent_path_registry, skill_path_registry, mcp_path_registry


def build_world(cwd_path: pathlib.Path | None = None) -> None:
    discover_all_paths(cwd_path)

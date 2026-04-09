import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPath:
    path: pathlib.Path
    """The path to the agent directory root."""
    spec_file: pathlib.Path
    """The path to the agent spec file."""


@dataclass(frozen=True)
class SkillPath:
    path: pathlib.Path
    """The path to the skill directory root."""
    skill_file: pathlib.Path
    """The path to the skill spec file."""


@dataclass(frozen=True)
class MCPPath:
    path: pathlib.Path
    """The path to the MCP directory root."""
    mcp_file: pathlib.Path
    """The path to the MCP spec file."""


class AgentPathRegistry:
    def __init__(self):
        self.candidates = []

    def register(self, candidate: AgentPath):
        self.candidates.append(candidate)

    def get_all(self):
        return self.candidates


class SkillPathRegistry:
    def __init__(self):
        self.candidates = []

    def register(self, candidate: SkillPath):
        self.candidates.append(candidate)

    def get_all(self):
        return self.candidates


class MCPPathRegistry:
    def __init__(self):
        self.candidates = []

    def register(self, candidate: MCPPath):
        self.candidates.append(candidate)

    def get_all(self):
        return self.candidates


agent_path_registry = AgentPathRegistry()
skill_path_registry = SkillPathRegistry()
mcp_path_registry = MCPPathRegistry()

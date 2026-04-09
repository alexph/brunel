import pathlib

from brunel.core import platform

JUNK_DIRS = [
    "__pycache__",
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
]


def get_agent_candidate_paths(
    cwd_path: pathlib.Path | None = None,
) -> list[pathlib.Path]:
    """Return a list of candidate paths for agent discovery.

    Args:
        cwd_path: The current working directory path.

    Returns:
        A list of candidate paths for agent discovery.
    """

    # Lowest index is the highest priority.
    agent_seed_paths = [
        platform.get_home_path() / ".brunel" / "agents",
        platform.get_config_path() / "agents",
    ]

    if cwd_path is not None:
        agent_seed_paths.insert(0, cwd_path / ".brunel" / "agents")

    agent_seed_paths.insert(0, platform.get_install_path() / "builtins" / "agents")

    return agent_seed_paths


def get_skills_candidate_paths(
    cwd_path: pathlib.Path | None = None,
) -> list[pathlib.Path]:
    """Return a list of candidate paths for skill discovery.

    Args:
        cwd_path: The current working directory path.

    Returns:
        A list of candidate paths for skill discovery.
    """

    # Lowest index is the highest priority.
    skill_seed_paths = [
        platform.get_home_path() / ".brunel" / "skills",
        platform.get_config_path() / "skills",
    ]

    if cwd_path is not None:
        skill_seed_paths.insert(0, cwd_path / ".brunel" / "skills")

    skill_seed_paths.insert(0, platform.get_install_path() / "builtins" / "skills")

    return skill_seed_paths


def get_mcp_candidate_paths(cwd_path: pathlib.Path | None = None) -> list[pathlib.Path]:
    """Return a list of candidate paths for MCP discovery.

    Args:
        cwd_path: The current working directory path.

    Returns:
        A list of candidate paths for MCP discovery.
    """

    # Lowest index is the highest priority.
    mcp_seed_paths = [
        platform.get_home_path() / ".brunel",
        platform.get_config_path(),
    ]
    if cwd_path is not None:
        mcp_seed_paths.insert(0, cwd_path / ".brunel")

    return mcp_seed_paths

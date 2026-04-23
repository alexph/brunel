import pathlib

from platformdirs import user_cache_path, user_config_path, user_data_path

JUNK_DIRS = [
    "__pycache__",
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
]


def get_cache_path() -> pathlib.Path:
    """Return the path to the user's cache directory."""
    return user_cache_path("brunel", "brunel")


def get_data_path() -> pathlib.Path:
    """Return the path to the user's data directory."""
    return user_data_path("brunel", "brunel")


def get_config_path() -> pathlib.Path:
    """Return the path to the user's config directory."""
    return user_config_path("brunel", "brunel")


def get_home_path() -> pathlib.Path:
    """Return the path to the user's home directory."""
    return pathlib.Path.home()


def get_install_path() -> pathlib.Path:
    """Return the path to the installation directory."""
    return pathlib.Path(__file__).parent.parent


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
        get_home_path() / ".brunel" / "agents",
        get_config_path() / "agents",
    ]

    if cwd_path is not None:
        agent_seed_paths.insert(0, cwd_path / ".brunel" / "agents")

    agent_seed_paths.insert(0, get_install_path() / "builtins" / "agents")

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
        get_home_path() / ".brunel" / "skills",
        get_config_path() / "skills",
    ]

    if cwd_path is not None:
        skill_seed_paths.insert(0, cwd_path / ".brunel" / "skills")

    skill_seed_paths.insert(0, get_install_path() / "builtins" / "skills")

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
        get_home_path() / ".brunel",
        get_config_path(),
    ]
    if cwd_path is not None:
        mcp_seed_paths.insert(0, cwd_path / ".brunel")

    return mcp_seed_paths

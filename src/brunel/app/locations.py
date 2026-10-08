import abc
import pathlib
from dataclasses import dataclass
from typing import override

from platformdirs import user_cache_path, user_config_path, user_data_path

JUNK_DIRS = [
    "__pycache__",
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
]


@dataclass(kw_only=True, frozen=True)
class UserCachePath:
    appname: str
    appauthor: str
    version: str | None = None
    opinion: bool = True
    ensure_exists: bool = False
    use_site_for_root: bool = False


@dataclass(kw_only=True, frozen=True)
class UserDataPath:
    appname: str
    appauthor: str
    version: str | None = None
    roaming: bool = True
    ensure_exists: bool = False
    use_site_for_root: bool = False


@dataclass(kw_only=True, frozen=True)
class UserConfigPath:
    appname: str
    appauthor: str
    version: str | None = None
    roaming: bool = True
    ensure_exists: bool = False
    use_site_for_root: bool = False


@dataclass(kw_only=True, frozen=True)
class Locations:
    cache_path: UserCachePath
    config_path: UserConfigPath
    data_path: UserDataPath

    @property
    def cache(self) -> pathlib.Path:
        """Return the path to the user's cache directory."""
        return user_cache_path(
            appname=self.cache_path.appname,
            appauthor=self.cache_path.appauthor,
            version=self.cache_path.version,
            opinion=self.cache_path.opinion,
            ensure_exists=self.cache_path.ensure_exists,
            use_site_for_root=self.cache_path.use_site_for_root,
        )

    @property
    def data(self) -> pathlib.Path:
        """Return the path to the user's data directory."""
        return user_data_path(
            appname=self.data_path.appname,
            appauthor=self.data_path.appauthor,
            version=self.data_path.version,
            roaming=self.data_path.roaming,
            ensure_exists=self.data_path.ensure_exists,
            use_site_for_root=self.data_path.use_site_for_root,
        )

    @property
    def config(self) -> pathlib.Path:
        """Return the path to the user's config directory."""
        return user_config_path(
            appname=self.config_path.appname,
            appauthor=self.config_path.appauthor,
            version=self.config_path.version,
            roaming=self.config_path.roaming,
            ensure_exists=self.config_path.ensure_exists,
            use_site_for_root=self.config_path.use_site_for_root,
        )

    @property
    def home(self) -> pathlib.Path:
        """Return the path to the user's home directory."""
        return pathlib.Path.home()

    @property
    def install(self) -> pathlib.Path:
        """Return the path to the installation directory."""
        return pathlib.Path(__file__).parent.parent


def get_locations() -> Locations:
    return Locations(
        cache_path=UserCachePath(appname="brunel", appauthor="brunel"),
        data_path=UserDataPath(appname="brunel", appauthor="brunel"),
        config_path=UserConfigPath(appname="brunel", appauthor="brunel"),
    )


@dataclass(kw_only=True, frozen=True)
class ResolvedLocations:
    home: pathlib.Path
    install: pathlib.Path
    config: pathlib.Path
    data: pathlib.Path
    cache: pathlib.Path


@dataclass(kw_only=True, frozen=True)
class AgentPath:
    path: pathlib.Path
    """The path to the agent directory root."""
    spec_file: pathlib.Path
    """The path to the agent spec file."""


@dataclass(kw_only=True, frozen=True)
class SkillPath:
    path: pathlib.Path
    """The path to the skill directory root."""
    skill_file: pathlib.Path
    """The path to the skill spec file."""


@dataclass(kw_only=True, frozen=True)
class MCPPath:
    path: pathlib.Path
    """The path to the MCP directory root."""
    mcp_file: pathlib.Path
    """The path to the MCP spec file."""


class AbstractFinder(abc.ABC):
    def __init__(self, locations: ResolvedLocations):
        self.locations = locations

    @abc.abstractmethod
    def get_paths(self) -> list[pathlib.Path]:
        """Return a list of candidate paths for discovery."""

    @abc.abstractmethod
    def find(self) -> object:
        """Return a list of candidates."""


class AgentFinder(AbstractFinder):
    @override
    def get_paths(self) -> list[pathlib.Path]:
        locations = self.locations
        return [
            locations.home / ".brunel" / "agents",
            locations.config / "agents",
        ]

    @override
    def find(self) -> list[AgentPath]:
        items: list[AgentPath] = []
        file_names = ["agent.yaml", "agent.yml"]
        for path in self.get_paths():
            if not path.exists():
                continue
            for item in path.iterdir():
                if item.is_dir():
                    for file_name in file_names:
                        if (item / file_name).exists():
                            items.append(
                                AgentPath(path=item, spec_file=item / file_name)
                            )
                elif item.is_file() and item.name in file_names:
                    items.append(AgentPath(path=item, spec_file=item))
        return items


class SkillFinder(AbstractFinder):
    @override
    def get_paths(self) -> list[pathlib.Path]:
        locations = self.locations
        return [
            locations.home / ".brunel" / "skills",
            locations.config / "skills",
        ]

    @override
    def find(self) -> list[SkillPath]:
        items: list[SkillPath] = []
        for path in self.get_paths():
            if not path.exists():
                continue
            for item in path.iterdir():
                if item.is_dir() and (item / "SKILL.md").exists():
                    items.append(SkillPath(path=item, skill_file=item / "SKILL.md"))
        return items


class MCPFinder(AbstractFinder):
    @override
    def get_paths(self) -> list[pathlib.Path]:
        locations = self.locations
        return [
            locations.home / ".brunel",
            locations.config,
        ]

    @override
    def find(self) -> list[MCPPath]:
        items: list[MCPPath] = []
        for path in self.get_paths():
            if not path.exists():
                continue
            if (path / "mcp.json").is_file():
                items.append(MCPPath(path=path, mcp_file=path / "mcp.json"))
            for item in path.iterdir():
                if item.is_dir() and (item / "mcp.json").exists():
                    items.append(MCPPath(path=item, mcp_file=item / "mcp.json"))
        return items

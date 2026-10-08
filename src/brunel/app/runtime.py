import os
from dataclasses import dataclass
from pathlib import Path

from brunel.app.db import DATABASE_FILENAME, get_database_url
from brunel.app.locations import ResolvedLocations, get_locations
from brunel.app.settings import load_settings


@dataclass(kw_only=True, frozen=True)
class RuntimeConfig:
    config_file: Path
    locations: ResolvedLocations
    database_url: str
    idle_timeout: float
    service: bool


def load_runtime_config(
    config_file: Path | None = None,
    *,
    idle_timeout: float | None = None,
    service: bool = False,
) -> RuntimeConfig:
    defaults = get_locations()

    explicit_file = config_file or os.environ.get("BRUNEL_CONFIG_FILE")

    path = Path(explicit_file or defaults.config / "brunel.toml").expanduser().resolve()

    if explicit_file is not None and not path.is_file():
        raise FileNotFoundError(f"Config file does not exist: {path}")

    overrides = {} if idle_timeout is None else {"idle_timeout": idle_timeout}
    settings = load_settings(path, **overrides)

    def resolve(value: Path | None, default: Path) -> Path:
        if value is None:
            return default.resolve()
        value = value.expanduser()
        return (value if value.is_absolute() else path.parent / value).resolve()

    locations = ResolvedLocations(
        home=defaults.home.resolve(),
        install=defaults.install.resolve(),
        data=resolve(settings.data_dir, defaults.data),
        config=resolve(settings.config_dir, defaults.config),
        cache=resolve(settings.cache_dir, defaults.cache),
    )

    database_path = resolve(settings.database_path, locations.data / DATABASE_FILENAME)

    return RuntimeConfig(
        config_file=path,
        locations=locations,
        database_url=get_database_url(database_path),
        idle_timeout=settings.idle_timeout,
        service=service,
    )

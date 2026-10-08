from pathlib import Path
from typing import Any, ClassVar, override

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        extra="ignore", env_prefix="brunel_", frozen=True,
    )
    data_dir: Path | None = None
    config_dir: Path | None = None
    cache_dir: Path | None = None
    database_path: Path | None = None
    idle_timeout: float = Field(default=30, ge=0.1, allow_inf_nan=False)


def load_settings(config_path: Path, **overrides: Any) -> Settings:
    class Settings_(Settings):
        @classmethod
        @override
        def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            return (
                init_settings,
                env_settings,
                TomlConfigSettingsSource(settings_cls, toml_file=config_path),
            )

    return Settings_(**overrides)

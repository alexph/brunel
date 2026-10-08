from dataclasses import FrozenInstanceError
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from brunel.app.db import Database, bootstrap
from brunel.app.locations import AgentFinder, MCPFinder, SkillFinder
from brunel.app.runtime import load_runtime_config
from brunel.app.settings import load_settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("CONFIG_FILE", "DATA_DIR", "CONFIG_DIR", "CACHE_DIR", "DATABASE_PATH", "IDLE_TIMEOUT"):
        monkeypatch.delenv(f"BRUNEL_{name}", raising=False)


def test_settings_precedence_and_validation(tmp_path, monkeypatch):
    config = tmp_path / "brunel.toml"
    config.write_text("idle_timeout = 12\n")
    assert load_settings(config).idle_timeout == 12
    monkeypatch.setenv("BRUNEL_IDLE_TIMEOUT", "7")
    assert load_settings(config).idle_timeout == 7
    assert load_settings(config, idle_timeout=3).idle_timeout == 3
    monkeypatch.setenv("BRUNEL_IDLE_TIMEOUT", "-1")
    with pytest.raises(ValidationError):
        load_settings(config)


def test_resolution_is_immutable_and_has_no_directory_side_effects(tmp_path):
    config = tmp_path / "brunel.toml"
    config.write_text('data_dir = "state"\nconfig_dir = "discovery"\ncache_dir = "cache"\n')
    runtime = load_runtime_config(config)
    assert runtime.locations.data == tmp_path / "state"
    assert runtime.locations.config == tmp_path / "discovery"
    assert runtime.locations.cache == tmp_path / "cache"
    assert runtime.database_url.endswith("/state/brunel.sqlite3")
    assert not runtime.locations.data.exists()
    assert not runtime.locations.config.exists()
    assert not runtime.locations.cache.exists()
    with pytest.raises(FrozenInstanceError):
        runtime.idle_timeout = 9


def test_default_file_is_optional_but_explicit_file_is_required(tmp_path, monkeypatch):
    from brunel.app.locations import get_locations
    from types import SimpleNamespace

    defaults = get_locations()
    monkeypatch.setattr("brunel.app.runtime.get_locations", lambda: SimpleNamespace(
        home=defaults.home, install=defaults.install,
        config=tmp_path / "config", data=tmp_path / "data", cache=tmp_path / "cache",
    ))
    assert load_runtime_config().idle_timeout == 30
    assert not (tmp_path / "config").exists()
    with pytest.raises(FileNotFoundError):
        load_runtime_config(tmp_path / "missing.toml")
    monkeypatch.setenv("BRUNEL_CONFIG_FILE", str(tmp_path / "missing.toml"))
    with pytest.raises(FileNotFoundError):
        load_runtime_config()


def test_config_file_selection_and_database_override(tmp_path, monkeypatch):
    first = tmp_path / "first.toml"
    first.write_text('database_path = "db/custom.sqlite3"\nidle_timeout = 6\n')
    second = tmp_path / "second.toml"
    second.write_text('idle_timeout = 8\n')
    monkeypatch.setenv("BRUNEL_CONFIG_FILE", str(first))
    runtime = load_runtime_config()
    assert runtime.database_url.endswith("/db/custom.sqlite3")
    assert load_runtime_config(second).idle_timeout == 8
    assert load_runtime_config(idle_timeout=4).idle_timeout == 4
    assert load_runtime_config(service=True).service


def test_discovery_uses_resolved_config_directory(tmp_path):
    config = tmp_path / "brunel.toml"
    config.write_text('config_dir = "discovery"\n')
    locations = load_runtime_config(config).locations
    agent = locations.config / "agents" / "sample"
    agent.mkdir(parents=True)
    (agent / "agent.yaml").write_text("name: sample\n")
    skill = locations.config / "skills" / "sample"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("Sample skill\n")
    (locations.config / "mcp.json").write_text("{}")
    assert any(item.path == agent for item in AgentFinder(locations).find())
    assert any(item.path == skill for item in SkillFinder(locations).find())
    assert any(item.path == locations.config for item in MCPFinder(locations).find())


def test_bootstrap_and_sessions_with_percent_in_path(tmp_path):
    config = tmp_path / "brunel.toml"
    config.write_text('database_path = "state%20/db.sqlite3"\n')
    runtime = load_runtime_config(config)
    bootstrap(runtime.database_url)
    database = Database(runtime.database_url)
    try:
        with database.sessions() as session:
            assert inspect(session.connection()).get_table_names() == ["alembic_version", "projects"]
    finally:
        database.close()


def test_failed_migration_does_not_start_server(tmp_path, monkeypatch):
    import importlib

    module = importlib.import_module("brunel.rest.server")
    config = tmp_path / "brunel.toml"
    config.write_text('data_dir = "state"\n')
    monkeypatch.setattr(module, "runtime_directory", lambda: tmp_path)

    def fail(database_url):
        raise RuntimeError("Migration failed")

    monkeypatch.setattr(module, "bootstrap", fail)
    with pytest.raises(RuntimeError, match="Migration failed"):
        module.server(config_file=config)
    assert not (tmp_path / "daemon.sock").exists()


@pytest.fixture
def short_runtime_directory():
    with tempfile.TemporaryDirectory(prefix="brn-", dir="/tmp") as directory:
        yield Path(directory)


def test_database_disposed_when_server_fails(tmp_path, monkeypatch, short_runtime_directory):
    import importlib

    module = importlib.import_module("brunel.rest.server")
    config = tmp_path / "brunel.toml"
    config.write_text('data_dir = "state"\n')
    monkeypatch.setattr(module, "runtime_directory", lambda: short_runtime_directory)
    calls = []

    class FakeDatabase:
        def __init__(self, url):
            self.url = url

        def close(self):
            calls.append("closed")

    monkeypatch.setattr(module, "Database", FakeDatabase)
    monkeypatch.setattr(module, "bootstrap", lambda url: None)

    def fail(self, **kwargs):
        assert self.config.app.state.database.url.endswith("/state/brunel.sqlite3")
        assert self.config.app.state.runtime.config_file == config
        raise RuntimeError("Server failed")

    monkeypatch.setattr(module.uvicorn.Server, "run", fail)
    with pytest.raises(RuntimeError, match="Server failed"):
        module.server(config_file=config)
    assert calls == ["closed"]
    assert not (short_runtime_directory / "daemon.sock").exists()

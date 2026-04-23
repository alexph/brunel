from __future__ import annotations

from pathlib import Path

from brunel.app import discovery


def _write_agent(root: Path, name: str, model: str) -> None:
    agent_dir = root / name
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.yaml").write_text(
        "\n".join(
            [
                f"model: {model}",
                "instructions: test agent",
            ]
        )
    )


def test_discover_agents_respects_seed_precedence(monkeypatch, tmp_path: Path) -> None:
    install_root = tmp_path / "install" / "builtins" / "agents"
    project_root = tmp_path / "project" / ".brunel" / "agents"
    home_root = tmp_path / "home" / ".brunel" / "agents"
    config_root = tmp_path / "config" / "agents"

    _write_agent(install_root, "shared", "openai:gpt-4.1-mini")
    _write_agent(project_root, "shared", "openai:gpt-4.1-nano")
    _write_agent(home_root, "shared", "openai:gpt-4o-mini")
    _write_agent(config_root, "shared", "openai:gpt-5-nano")

    monkeypatch.setattr(
        discovery.paths.platform, "get_install_path", lambda: tmp_path / "install"
    )
    monkeypatch.setattr(
        discovery.paths.platform, "get_home_path", lambda: tmp_path / "home"
    )
    monkeypatch.setattr(
        discovery.paths.platform, "get_config_path", lambda: tmp_path / "config"
    )

    discovered = list(discovery.discover_agents(tmp_path / "project"))

    assert [
        candidate.spec_file.read_text().splitlines()[0]
        for candidate in discovered
        if candidate.path.name == "shared"
    ] == [
        "model: openai:gpt-4.1-mini",
        "model: openai:gpt-4.1-nano",
        "model: openai:gpt-4o-mini",
        "model: openai:gpt-5-nano",
    ]

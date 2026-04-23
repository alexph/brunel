from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from brunel.agents.errors import AgentNotFoundError, AgentRunError, AgentSpecError
from brunel.agents.runner import ExecutionResult
from brunel.cli import app


runner = CliRunner()


def test_cli_run_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "brunel.cli.execute",
        lambda request: ExecutionResult(
            agent_name=request.agent_name,
            output="result text",
            model="openai:gpt-4.1-mini",
        ),
    )

    result = runner.invoke(app, ["run", "default", "--prompt", "hello"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "result text"


def test_cli_run_unknown_agent(monkeypatch) -> None:
    monkeypatch.setattr(
        "brunel.cli.execute",
        lambda request: (_ for _ in ()).throw(AgentNotFoundError("missing")),
    )

    result = runner.invoke(app, ["run", "missing", "--prompt", "hello"])

    assert result.exit_code == 1
    assert "Agent lookup error: missing" in result.stderr


def test_cli_run_invalid_spec(monkeypatch) -> None:
    monkeypatch.setattr(
        "brunel.cli.execute",
        lambda request: (_ for _ in ()).throw(AgentSpecError("invalid spec")),
    )

    result = runner.invoke(app, ["run", "default", "--prompt", "hello"])

    assert result.exit_code == 1
    assert "Agent spec error: invalid spec" in result.stderr


def test_cli_run_runtime_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "brunel.cli.execute",
        lambda request: (_ for _ in ()).throw(AgentRunError("runtime failure")),
    )

    result = runner.invoke(app, ["run", "default", "--prompt", "hello"])

    assert result.exit_code == 1
    assert "Agent run error: runtime failure" in result.stderr

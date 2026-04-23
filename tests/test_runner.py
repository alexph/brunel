from __future__ import annotations

from pathlib import Path

import pytest

from brunel.agents.errors import AgentRunError
from brunel.agents.runner import ExecutionRequest, execute


def test_execute_translates_spec_to_pydantic_ai(monkeypatch, tmp_path: Path) -> None:
    agent_dir = tmp_path / ".brunel" / "agents" / "local"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.yaml").write_text(
        "\n".join(
            [
                "model: openai:gpt-4.1-mini",
                "instructions: test instructions",
                "model_settings:",
                "  max_tokens: 256",
                "capabilities:",
                "  - WebSearch",
            ]
        )
    )

    captured: dict[str, object] = {}

    class FakeResult:
        output = "completed"

    class FakeAgent:
        def __init__(self, model, **kwargs):
            captured["model"] = model
            captured["kwargs"] = kwargs

        def run_sync(self, prompt):
            captured["prompt"] = prompt
            return FakeResult()

    monkeypatch.setattr("brunel.agents.runner.Agent", FakeAgent)

    result = execute(ExecutionRequest(agent_name="local", prompt="hello", cwd_path=tmp_path))

    assert result.output == "completed"
    assert captured["model"] == "openai:gpt-4.1-mini"
    assert captured["prompt"] == "hello"
    assert captured["kwargs"]["name"] == "local"
    assert captured["kwargs"]["instructions"] == "test instructions"
    assert captured["kwargs"]["model_settings"] == {"max_tokens": 256}
    assert len(captured["kwargs"]["builtin_tools"]) == 1


def test_execute_wraps_runtime_failures(monkeypatch, tmp_path: Path) -> None:
    agent_dir = tmp_path / ".brunel" / "agents" / "default"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.yaml").write_text(
        "\n".join(
            [
                "model: openai:gpt-4.1-mini",
                "instructions: test instructions",
            ]
        )
    )

    class FakeAgent:
        def __init__(self, model, **kwargs):
            pass

        def run_sync(self, prompt):
            raise RuntimeError("boom")

    monkeypatch.setattr("brunel.agents.runner.Agent", FakeAgent)

    with pytest.raises(AgentRunError, match="failed to run"):
        execute(ExecutionRequest(agent_name="default", prompt="hello", cwd_path=tmp_path))

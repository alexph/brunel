from __future__ import annotations

from pathlib import Path

import pytest

from brunel.agents.errors import AgentSpecError
from brunel.agents.loader import load_agent_spec


def test_load_agent_spec_validates_supported_fields(tmp_path: Path) -> None:
    spec_file = tmp_path / "agent.yaml"
    spec_file.write_text(
        "\n".join(
            [
                "model: openai:gpt-4.1-mini",
                "instructions: test agent",
                "model_settings:",
                "  max_tokens: 128",
                "  thinking:",
                "    effort: high",
                "capabilities:",
                "  - WebSearch:",
                "      search_context_size: high",
                "      max_uses: 2",
            ]
        )
    )

    spec = load_agent_spec(spec_file)

    assert spec.model == "openai:gpt-4.1-mini"
    assert spec.model_settings is not None
    assert spec.model_settings.max_tokens == 128
    assert spec.model_settings.thinking is not None
    assert spec.model_settings.thinking.effort == "high"
    assert len(spec.capabilities) == 1
    assert spec.capabilities[0].search_context_size == "high"
    assert spec.capabilities[0].max_uses == 2


def test_load_agent_spec_rejects_missing_required_fields(tmp_path: Path) -> None:
    spec_file = tmp_path / "agent.yaml"
    spec_file.write_text("instructions: missing model\n")

    with pytest.raises(AgentSpecError, match="model"):
        load_agent_spec(spec_file)


def test_load_agent_spec_rejects_thinking_capability(tmp_path: Path) -> None:
    spec_file = tmp_path / "agent.yaml"
    spec_file.write_text(
        "\n".join(
            [
                "model: openai:gpt-4.1-mini",
                "instructions: invalid capability",
                "capabilities:",
                "  - Thinking:",
                "      effort: high",
            ]
        )
    )

    with pytest.raises(AgentSpecError, match="model_settings.thinking"):
        load_agent_spec(spec_file)


def test_load_agent_spec_rejects_unsupported_provider(tmp_path: Path) -> None:
    spec_file = tmp_path / "agent.yaml"
    spec_file.write_text(
        "\n".join(
            [
                "model: anthropic:claude-opus-4-1",
                "instructions: invalid provider",
            ]
        )
    )

    with pytest.raises(AgentSpecError, match="OpenAI-compatible"):
        load_agent_spec(spec_file)

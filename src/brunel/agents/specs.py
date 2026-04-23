from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from brunel.agents.errors import AgentSpecError


class ThinkingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    effort: Literal["minimal", "low", "medium", "high", "xhigh"] | None = None


class AgentModelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = None
    top_p: float | None = None
    timeout: float | None = Field(default=None, gt=0)
    parallel_tool_calls: bool | None = None
    seed: int | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    logit_bias: dict[str, int] | None = None
    stop_sequences: list[str] | None = None
    extra_headers: dict[str, str] | None = None
    thinking: bool | ThinkingSettings | None = None
    extra_body: object | None = None


class WebSearchCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["WebSearch"] = "WebSearch"
    search_context_size: Literal["low", "medium", "high"] = "medium"
    blocked_domains: list[str] | None = None
    allowed_domains: list[str] | None = None
    max_uses: int | None = Field(default=None, ge=1)


Capability = WebSearchCapability


class AgentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    instructions: str
    model_settings: AgentModelSettings | None = None
    capabilities: list[Capability] = Field(default_factory=list)

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not value.startswith("openai:"):
            raise ValueError("v1 only supports OpenAI-compatible models; use an `openai:` model string")
        return value

    @model_validator(mode="before")
    @classmethod
    def normalize_capabilities(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data

        capabilities = data.get("capabilities")
        if capabilities is None:
            return data
        if not isinstance(capabilities, list):
            raise ValueError("`capabilities` must be a list")

        normalized_capabilities: list[dict[str, Any]] = []
        for raw_capability in capabilities:
            if isinstance(raw_capability, str):
                normalized_capabilities.append(cls._normalize_capability_name(raw_capability, {}))
                continue
            if isinstance(raw_capability, Mapping):
                if len(raw_capability) != 1:
                    raise ValueError("each capability mapping must contain exactly one capability name")
                capability_name, capability_settings = next(iter(raw_capability.items()))
                if capability_settings is None:
                    capability_settings = {}
                if not isinstance(capability_settings, Mapping):
                    raise ValueError(
                        f"capability `{capability_name}` must map to a settings object or be declared as a string"
                    )
                normalized_capabilities.append(
                    cls._normalize_capability_name(str(capability_name), dict(capability_settings))
                )
                continue
            raise ValueError("each capability must be either a string or a single-key mapping")

        return {**data, "capabilities": normalized_capabilities}

    @staticmethod
    def _normalize_capability_name(name: str, settings: dict[str, Any]) -> dict[str, Any]:
        normalized_name = name.strip()
        if normalized_name == "Thinking":
            raise ValueError("`Thinking` is not a v1 capability; configure `model_settings.thinking` instead")
        if normalized_name != "WebSearch":
            raise ValueError(f"unsupported capability `{normalized_name}`")
        return {"kind": "WebSearch", **settings}


def validate_agent_spec(data: Any) -> AgentSpec:
    try:
        return AgentSpec.model_validate(data)
    except ValidationError as exc:
        raise AgentSpecError(str(exc)) from exc

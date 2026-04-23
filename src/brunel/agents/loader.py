from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

import yaml

from brunel.agents.errors import AgentNotFoundError, AgentSpecError
from brunel.agents.specs import AgentSpec, validate_agent_spec
from brunel.app.discovery import discover_agents
from brunel.app.registries import AgentPath


@dataclass(frozen=True)
class LoadedAgent:
    name: str
    source: AgentPath
    spec: AgentSpec


def resolve_agent(name: str, cwd_path: pathlib.Path | None = None) -> LoadedAgent:
    normalized_name = name.strip()
    if not normalized_name:
        raise AgentNotFoundError("agent name cannot be empty")

    for candidate in discover_agents(cwd_path):
        if _get_agent_name(candidate) != normalized_name:
            continue
        return LoadedAgent(
            name=normalized_name,
            source=candidate,
            spec=load_agent_spec(candidate.spec_file),
        )

    available_agents = sorted(
        {_get_agent_name(candidate) for candidate in discover_agents(cwd_path)}
    )
    if available_agents:
        available = ", ".join(available_agents)
        raise AgentNotFoundError(
            f"agent `{normalized_name}` was not found. Available agents: {available}"
        )
    raise AgentNotFoundError(
        f"agent `{normalized_name}` was not found. No agents are available."
    )


def load_agent_spec(spec_file: pathlib.Path) -> AgentSpec:
    try:
        raw_text = spec_file.read_text()
    except OSError as exc:
        raise AgentSpecError(f"failed to read agent spec `{spec_file}`: {exc}") from exc

    raw_data = _parse_spec_text(raw_text, spec_file)
    return validate_agent_spec(raw_data)


def _parse_spec_text(raw_text: str, spec_file: pathlib.Path) -> object:
    suffix = spec_file.suffix.lower()
    try:
        if suffix == ".json":
            return json.loads(raw_text)
        return yaml.safe_load(raw_text)
    except json.JSONDecodeError as exc:
        raise AgentSpecError(f"invalid JSON in `{spec_file}`: {exc}") from exc
    except yaml.YAMLError as exc:
        raise AgentSpecError(f"invalid YAML in `{spec_file}`: {exc}") from exc
    except AgentSpecError:
        raise
    except Exception as exc:  # pragma: no cover
        raise AgentSpecError(f"failed to parse `{spec_file}`: {exc}") from exc


def _get_agent_name(candidate: AgentPath) -> str:
    if candidate.path.is_dir():
        return candidate.path.name
    return candidate.path.stem

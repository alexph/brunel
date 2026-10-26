import json
from copy import deepcopy
from dataclasses import dataclass, field, replace

import ag_ui.core as ag
import jsonpatch
from pydantic import TypeAdapter

from brunel.tui.stores import StoreChange


EVENT = TypeAdapter(ag.Event)


@dataclass(frozen=True)
class TranscriptEntry:
    id: str
    role: str
    content: str = ""
    name: str = ""
    status: str = "complete"
    tool_call_id: str | None = None
    activity_type: str | None = None
    data: object = None
    owner: str | None = None
    metadata: dict = field(default_factory=dict)


class ConversationStore:
    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.run_id: str | None = None
        self.status = "Runtime not connected"
        self.entries: dict[str, TranscriptEntry] = {}
        self.state: object = None
        self.interrupts: tuple = ()
        self.notice = ""
        self.steps: set[tuple[str | None, str]] = set()
        self.subagents: dict[str, str] = {}
        self._open: set[str] = set()
        self._spans: set[str] = set()
        self._active = False
        self._chunks: dict[str, str] = {}
        self._encrypted: dict[tuple[str, str], str] = {}

    def apply(self, event: object) -> StoreChange:
        event = EVENT.validate_python(event)
        data = event.model_dump(exclude_none=True)
        kind = event.type.value
        owner = data.get("subagent_run_id")
        if kind == "RUN_STARTED":
            if event.thread_id != self.thread_id:
                raise ValueError("Event belongs to a different conversation")
            if self._active:
                raise ValueError("A run is already active")
            self.run_id = event.run_id
            self._active = True
            self.status = "Running"
            self.interrupts = ()
            self.notice = ""
            return StoreChange(status=True)
        if kind in {"RUN_FINISHED", "RUN_ERROR"}:
            if kind == "RUN_FINISHED":
                if not self._active or event.thread_id != self.thread_id or event.run_id != self.run_id:
                    raise ValueError("Run identifiers do not match")
                self._close_chunks()
                if self._open or self._spans or self.steps or "running" in self.subagents.values():
                    raise ValueError("Run finished with open messages or tool calls")
                outcome = data.get("outcome", {})
                self.status = {"interrupt": "Awaiting input", "cancelled": "Cancelled"}.get(
                    outcome.get("type"), "Complete"
                )
                self.interrupts = tuple(outcome.get("interrupts", ()))
            else:
                self.status = "Failed"
                self.notice = event.message
                for key in self._open:
                    self.entries[key] = replace(self.entries[key], status="interrupted")
                self._open.clear()
                self._chunks.clear()
                self._spans.clear()
                self.steps.clear()
                self.subagents = {key: "interrupted" if value == "running" else value for key, value in self.subagents.items()}
            self._active = False
            return StoreChange(updated=tuple(self.entries), status=True)
        if kind == "MESSAGES_SNAPSHOT":
            incoming: dict[str, TranscriptEntry] = {}
            for message in event.messages:
                item = message.model_dump(exclude_none=True)
                incoming[message.id] = TranscriptEntry(
                    id=message.id, role=message.role,
                    content=self._text(item.get("content", "")),
                    name=item.get("name", ""), tool_call_id=item.get("tool_call_id"),
                    activity_type=item.get("activity_type"), data=deepcopy(item.get("content")),
                    owner=item.get("subagent_run_id"), metadata=deepcopy(item.get("metadata", {})),
                )
                for call in item.get("tool_calls", []):
                    key = self._tool_key(call["id"])
                    incoming[key] = TranscriptEntry(
                        id=key, role="call", name=call["function"]["name"],
                        content=call["function"]["arguments"], tool_call_id=call["id"],
                        status="arguments complete",
                    )
            roles = {entry.role for entry in incoming.values()}
            self.entries = {
                key: incoming.pop(key, entry)
                for key, entry in self.entries.items()
                if key in incoming or (entry.role in {"activity", "reasoning"} and entry.role not in roles)
            } | incoming
            self._open.intersection_update(self.entries)
            return StoreChange(updated=tuple(self.entries), structure=True)
        if kind in {"STATE_SNAPSHOT", "STATE_DELTA"}:
            if kind == "STATE_SNAPSHOT":
                self.state = deepcopy(event.snapshot)
            else:
                try:
                    self.state = jsonpatch.apply_patch(self.state, event.delta, in_place=False)
                except (jsonpatch.JsonPatchException, KeyError, IndexError, TypeError) as error:
                    self.notice = f"State update skipped; waiting for a fresh snapshot: {error}"
            return StoreChange(status=True)
        if kind.startswith("STEP_"):
            key = (owner, event.step_name)
            if kind == "STEP_STARTED":
                self.steps.add(key)
            else:
                self.steps.discard(key)
            return StoreChange(status=True)
        if kind.startswith("SUBAGENT_"):
            self.subagents[event.subagent_run_id] = {
                "SUBAGENT_STARTED": "running", "SUBAGENT_FINISHED": "complete",
                "SUBAGENT_ERROR": "failed",
            }[kind]
            return StoreChange(status=True)
        if kind == "REASONING_ENCRYPTED_VALUE":
            self._encrypted[(event.subtype, event.entity_id)] = event.encrypted_value
            return StoreChange()
        if kind in {"REASONING_START", "REASONING_END"}:
            if kind == "REASONING_START":
                if event.message_id in self._spans:
                    raise ValueError("Reasoning span is already open")
                self._spans.add(event.message_id)
            else:
                if event.message_id not in self._spans:
                    raise ValueError("Reasoning span ended without a start")
                self._spans.remove(event.message_id)
            return StoreChange()
        if kind in {"THINKING_START", "THINKING_END"}:
            return StoreChange()
        if kind == "TOOL_CALL_RESULT":
            key = event.message_id
            if key in self.entries and self.entries[key].role != "tool":
                raise ValueError("Message ID already belongs to another role")
            self.entries[key] = TranscriptEntry(
                id=key, role="tool", content=self._text(event.content),
                tool_call_id=event.tool_call_id, owner=owner,
            )
            call = self._tool_key(event.tool_call_id)
            if call in self.entries:
                self.entries[call] = replace(self.entries[call], status="result received")
            return StoreChange(updated=(key, call), structure=True)
        if kind.startswith("ACTIVITY_"):
            key = event.message_id
            existing = self.entries.get(key)
            if existing is not None and existing.role != "activity":
                raise ValueError("Message ID already belongs to another role")
            if kind == "ACTIVITY_SNAPSHOT":
                if existing is not None and event.replace is False:
                    return StoreChange()
                content = deepcopy(event.content)
            else:
                if existing is None:
                    self.notice = "Activity update skipped: missing snapshot"
                    return StoreChange(status=True)
                self._check_owner(existing, owner)
                try:
                    content = jsonpatch.apply_patch(existing.data, event.patch, in_place=False)
                except (jsonpatch.JsonPatchException, KeyError, IndexError, TypeError) as error:
                    self.notice = f"Activity update skipped: {error}"
                    return StoreChange(status=True)
            self.entries[key] = TranscriptEntry(
                id=key, role="activity", activity_type=event.activity_type,
                data=content, content=json.dumps(content, indent=2, ensure_ascii=False),
                owner=owner if kind == "ACTIVITY_SNAPSHOT" else existing.owner,
            )
            return StoreChange(updated=(key,), structure=existing is None)
        family = (
            "tool" if kind.startswith("TOOL_CALL_") else
            "reasoning" if kind.startswith(("REASONING_MESSAGE_", "THINKING_TEXT_MESSAGE_")) else
            "text" if kind.startswith("TEXT_MESSAGE_") else None
        )
        if family is None:
            self.notice = f"{kind}: no renderer registered"
            return StoreChange(status=True)
        identifier = data.get("tool_call_id" if family == "tool" else "message_id")
        chunk = kind.endswith("_CHUNK")
        updated = []
        if chunk:
            previous = self._chunks.get(family)
            if identifier is None:
                identifier = previous
            if identifier is None:
                raise ValueError("First chunk requires an identifier")
            if previous and previous != identifier:
                updated.append(self._close_chunk(family))
            self._chunks[family] = identifier
        key = self._tool_key(identifier) if family == "tool" else identifier
        existing = self.entries.get(key)
        starting = kind.endswith("_START") or (chunk and key not in self._open)
        if starting:
            if key in self._open:
                raise ValueError("Entity is already open")
            role = "call" if family == "tool" else "reasoning" if family == "reasoning" else data.get("role", "assistant")
            if existing is not None:
                if existing.role != role:
                    raise ValueError("Message ID already belongs to another role")
                self._check_owner(existing, owner)
            else:
                self.entries[key] = TranscriptEntry(
                    id=key, role=role, name=data.get("tool_call_name", data.get("name", "")),
                    tool_call_id=identifier if family == "tool" else None, owner=owner,
                )
            self._open.add(key)
        elif key not in self._open:
            raise ValueError("Content or end received without a start")
        entry = self.entries[key]
        self._check_owner(entry, owner)
        if family == "tool" and data.get("tool_call_name", entry.name) != entry.name:
            raise ValueError("Tool name does not match its opener")
        ending = kind.endswith("_END")
        self.entries[key] = replace(
            entry, content=entry.content + data.get("delta", ""),
            status=("arguments complete" if family == "tool" else "complete") if ending else "streaming",
            metadata=entry.metadata | deepcopy(data.get("metadata", {})),
        )
        if ending:
            self._open.remove(key)
        return StoreChange(updated=(*updated, key), structure=existing is None)

    def _close_chunk(self, family: str) -> str:
        identifier = self._chunks.pop(family)
        key = self._tool_key(identifier) if family == "tool" else identifier
        self._open.discard(key)
        self.entries[key] = replace(
            self.entries[key], status="arguments complete" if family == "tool" else "complete"
        )
        return key

    def _close_chunks(self) -> None:
        for family in tuple(self._chunks):
            self._close_chunk(family)

    @staticmethod
    def _check_owner(entry: TranscriptEntry, owner: str | None) -> None:
        if owner is not None and entry.owner != owner:
            raise ValueError("Entity attribution does not match its opener")

    @staticmethod
    def _tool_key(identifier: str) -> str:
        return f"tool:{identifier}"

    @staticmethod
    def _text(content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            return json.dumps(content, indent=2, ensure_ascii=False)
        lines = []
        for part in content or []:
            item = part.model_dump() if hasattr(part, "model_dump") else part
            if item.get("type") == "text":
                lines.append(item["text"])
            else:
                source = item.get("source", {})
                target = source.get("value", "") if source.get("type") == "url" else "not available as a link"
                lines.append(f"[{item.get('type', 'attachment')}: {target}]")
        return "\n".join(lines)

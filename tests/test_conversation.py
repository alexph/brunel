import ag_ui.core as ag
import pytest

from brunel.tui.conversation import ConversationStore
from brunel.tui.stores import StoreChange, StoreKey, StoreRouter


def running_store():
    store = ConversationStore("thread-1")
    store.apply(ag.RunStartedEvent(thread_id="thread-1", run_id="run-1"))
    return store


def test_router_isolates_object_kinds_and_instances():
    router = StoreRouter()
    conversation = running_store()

    class ProjectStore:
        def __init__(self):
            self.project = None

        def apply(self, event):
            self.project = event
            return StoreChange(updated=("project",))

    project = ProjectStore()
    conversation_key = StoreKey("conversation", "1")
    project_key = StoreKey("project", "1")
    router.register(conversation_key, conversation)
    router.register(project_key, project)
    router.dispatch(project_key, {"name": "Brunel"})
    assert project.project == {"name": "Brunel"}
    assert not conversation.entries
    with pytest.raises(ValueError, match="already registered"):
        router.register(project_key, project)
    with pytest.raises(KeyError):
        router.dispatch(StoreKey("thread", "1"), {})


def test_streaming_updates_only_target_and_keeps_prior_views_immutable():
    store = running_store()
    store.apply(ag.TextMessageStartEvent(message_id="m1"))
    before = store.entries["m1"]
    change = store.apply(ag.TextMessageContentEvent(message_id="m1", delta="Hello"))
    store.apply(ag.TextMessageContentEvent(message_id="m1", delta=" world"))
    store.apply(ag.TextMessageEndEvent(message_id="m1"))
    assert change.updated == ("m1",)
    assert not change.structure
    assert before.content == ""
    assert store.entries["m1"].content == "Hello world"
    store.apply(ag.RunFinishedEvent(thread_id="thread-1", run_id="run-1"))
    assert store.status == "Complete"


def test_interleaved_tools_and_text_do_not_conflate_argument_end_with_result():
    store = running_store()
    store.apply(ag.TextMessageStartEvent(message_id="m1"))
    store.apply(ag.ToolCallStartEvent(tool_call_id="c1", tool_call_name="search"))
    store.apply(ag.ToolCallStartEvent(tool_call_id="c2", tool_call_name="read"))
    store.apply(ag.ToolCallArgsEvent(tool_call_id="c1", delta='{"query":'))
    store.apply(ag.ToolCallArgsEvent(tool_call_id="c2", delta="{}"))
    store.apply(ag.ToolCallArgsEvent(tool_call_id="c1", delta='"widgets"}'))
    store.apply(ag.ToolCallEndEvent(tool_call_id="c1"))
    assert store.entries["tool:c1"].status == "arguments complete"
    store.apply(
        ag.ToolCallResultEvent(
            message_id="result", tool_call_id="c1", content="Found it"
        )
    )
    assert store.entries["tool:c1"].status == "result received"
    assert store.entries["tool:c2"].status == "streaming"
    assert store.entries["result"].tool_call_id == "c1"


def test_chunks_close_previous_message_and_finish_at_run_boundary():
    store = running_store()
    store.apply(ag.TextMessageChunkEvent(message_id="m1", delta="One"))
    store.apply(ag.TextMessageChunkEvent(delta="!"))
    store.apply(ag.TextMessageChunkEvent(message_id="m2", delta="Two"))
    assert store.entries["m1"].content == "One!"
    assert store.entries["m1"].status == "complete"
    store.apply(ag.RunFinishedEvent(thread_id="thread-1", run_id="run-1"))
    assert store.entries["m2"].status == "complete"


def test_invalid_stream_and_attribution_are_rejected():
    store = running_store()
    with pytest.raises(ValueError, match="without a start"):
        store.apply(ag.TextMessageContentEvent(message_id="missing", delta="oops"))
    store.apply(ag.TextMessageStartEvent(message_id="m1", subagent_run_id="worker"))
    with pytest.raises(ValueError, match="attribution"):
        store.apply(
            ag.TextMessageContentEvent(
                message_id="m1", delta="oops", subagent_run_id="other"
            )
        )
    store.apply(ag.TextMessageContentEvent(message_id="m1", delta="valid"))
    with pytest.raises(ValueError, match="open messages"):
        store.apply(ag.RunFinishedEvent(thread_id="thread-1", run_id="run-1"))
    store.apply(ag.RunErrorEvent(message="Disconnected"))
    assert store.status == "Failed"
    assert store.entries["m1"].status == "interrupted"


def test_snapshots_reconcile_without_duplicates_and_preserve_client_roles():
    store = running_store()
    store.apply(
        ag.ActivitySnapshotEvent(
            message_id="activity", activity_type="PLAN", content={"done": 0}
        )
    )
    store.apply(ag.ReasoningMessageStartEvent(message_id="reasoning", role="reasoning"))
    store.apply(
        ag.ReasoningMessageContentEvent(message_id="reasoning", delta="Summary")
    )
    store.apply(ag.ReasoningMessageEndEvent(message_id="reasoning"))
    store.apply(
        ag.MessagesSnapshotEvent(messages=[ag.UserMessage(id="user", content="Hello")])
    )
    store.apply(
        ag.MessagesSnapshotEvent(
            messages=[ag.UserMessage(id="user", content="Updated")]
        )
    )
    assert list(store.entries) == ["activity", "reasoning", "user"]
    assert store.entries["user"].content == "Updated"
    store.apply(
        ag.MessagesSnapshotEvent(
            messages=[
                ag.ActivityMessage(id="replacement", activity_type="PLAN", content={})
            ]
        )
    )
    assert list(store.entries) == ["reasoning", "replacement"]


def test_state_and_activity_patches_are_atomic_and_recoverable():
    store = running_store()
    store.apply(ag.StateSnapshotEvent(snapshot={"done": 0}))
    store.apply(
        ag.StateDeltaEvent(delta=[{"op": "replace", "path": "/done", "value": 1}])
    )
    assert store.state == {"done": 1}
    store.apply(
        ag.StateDeltaEvent(
            delta=[
                {"op": "replace", "path": "/done", "value": 2},
                {"op": "remove", "path": "/missing"},
            ]
        )
    )
    assert store.state == {"done": 1}
    assert "skipped" in store.notice
    store.apply(
        ag.ActivitySnapshotEvent(
            message_id="a", activity_type="PLAN", content={"done": 0}
        )
    )
    store.apply(
        ag.ActivityDeltaEvent(
            message_id="a",
            activity_type="PLAN",
            patch=[{"op": "replace", "path": "/done", "value": 1}],
        )
    )
    assert store.entries["a"].data == {"done": 1}
    store.apply(
        ag.ActivitySnapshotEvent(
            message_id="a", activity_type="OTHER", content={}, replace=False
        )
    )
    assert store.entries["a"].activity_type == "PLAN"


def test_reasoning_encryption_is_not_transcript_content():
    store = running_store()
    store.apply(
        ag.ReasoningEncryptedValueEvent(
            subtype="message", entity_id="m1", encrypted_value="opaque"
        )
    )
    assert not store.entries
    assert store._encrypted[("message", "m1")] == "opaque"


def test_interrupt_outcome_is_not_success():
    store = running_store()
    store.apply(
        {
            "type": "RUN_FINISHED",
            "threadId": "thread-1",
            "runId": "run-1",
            "outcome": {
                "type": "interrupt",
                "interrupts": [{"id": "approval", "reason": "tool_call"}],
            },
        }
    )
    assert store.status == "Awaiting input"
    assert store.interrupts[0]["id"] == "approval"


def test_current_pydantic_ai_adapter_stream_is_consumable():
    import asyncio

    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    from pydantic_ai.ui.ag_ui import AGUIAdapter

    async def check():
        store = ConversationStore("thread")
        adapter = AGUIAdapter(
            agent=Agent(TestModel(custom_output_text="Hello from Pydantic AI")),
            run_input=ag.RunAgentInput(
                thread_id="thread",
                run_id="run",
                state={},
                tools=[],
                context=[],
                forwarded_props={},
                messages=[ag.UserMessage(id="user", content="Hi")],
            ),
        )
        async for event in adapter.run_stream():
            store.apply(event)
        assert store.status == "Complete"
        assert any(
            entry.content == "Hello from Pydantic AI"
            for entry in store.entries.values()
        )

    asyncio.run(check())

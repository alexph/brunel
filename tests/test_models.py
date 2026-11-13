from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid7

import pytest
from alembic import command
from alembic.config import Config
from pydantic import TypeAdapter
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    PartStartEvent,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from brunel.app.db import Database, bootstrap, get_database_url
from brunel.app.models import Project, Thread, ThreadEvent, ThreadInbox, ThreadMessage


@pytest.fixture
def database(tmp_path):
    url = get_database_url(tmp_path / "database.sqlite3")
    bootstrap(url)
    db = Database(url)
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def thread_id(database, tmp_path):
    with database.sessions.begin() as session:
        project = Project(name="Brunel", local_dir=str(tmp_path))
        session.add(project)
        session.flush()
        thread = Thread(project_id=project.id)
        session.add(thread)
        session.flush()
        return thread.id


def test_project_and_child_thread_persist_with_uuid7_keys(database, tmp_path):
    with database.sessions.begin() as session:
        project = Project(
            name="Brunel", local_dir=str(tmp_path), git_url="https://github.com/alexph/brunel.git"
        )
        session.add(project)
        session.flush()
        parent = Thread(project_id=project.id)
        session.add(parent)
        session.flush()
        child = Thread(project_id=project.id, parent_thread_id=parent.id, title="Investigate migrations")
        session.add(child)
        session.flush()
        project_id, parent_id, child_id = project.id, parent.id, child.id

    with database.sessions() as session:
        project = session.get(Project, project_id)
        parent = session.get(Thread, parent_id)
        child = session.get(Thread, child_id)
        assert all(key.version == 7 for key in (project.id, parent.id, child.id))
        assert project.local_dir == str(tmp_path)
        assert project.git_url == "https://github.com/alexph/brunel.git"
        assert parent.title is None
        assert child.title == "Investigate migrations"
        assert child.parent_thread_id == parent.id
        assert child.project_id == project.id
        assert project.created_at is not None
        assert child.updated_at is not None


def test_native_message_history_round_trips_in_sequence(database, thread_id):
    messages = [
        ModelRequest(parts=[UserPromptPart(content="Read the project")]),
        ModelResponse(parts=[ToolCallPart(tool_name="read", args={"path": "README.md"}, tool_call_id="read-1")]),
        ModelRequest(parts=[ToolReturnPart(tool_name="read", content="Brunel", tool_call_id="read-1")]),
        ModelResponse(parts=[TextPart(content="The project is Brunel.")]),
    ]
    payloads = ModelMessagesTypeAdapter.dump_python(messages, mode="json")
    with database.sessions.begin() as session:
        for sequence, payload in reversed(list(enumerate(payloads, start=1))):
            session.add(ThreadMessage(thread_id=thread_id, sequence=sequence, payload=payload))

    with database.sessions() as session:
        records = session.scalars(
            select(ThreadMessage).where(ThreadMessage.thread_id == thread_id).order_by(ThreadMessage.sequence)
        ).all()
        restored = ModelMessagesTypeAdapter.validate_python([record.payload for record in records])
        assert restored == messages
        assert all(record.id.version == 7 and record.format_version == 1 for record in records)


def test_native_stream_event_persists_separately_from_history(database, thread_id):
    event = PartStartEvent(index=0, part=TextPart(content="Hello"))
    adapter = TypeAdapter(PartStartEvent)
    with database.sessions.begin() as session:
        session.add(ThreadEvent(
            thread_id=thread_id, sequence=1, kind=event.event_kind,
            payload=adapter.dump_python(event, mode="json"),
        ))

    with database.sessions() as session:
        record = session.scalars(select(ThreadEvent)).one()
        assert record.id.version == 7
        assert record.format_version == 1
        assert adapter.validate_python(record.payload) == event
        assert session.scalars(select(ThreadMessage)).all() == []


def test_inbox_persists_pending_input_and_consumption(database, thread_id):
    payload = ModelMessagesTypeAdapter.dump_python(
        [ModelRequest(parts=[UserPromptPart(content="Also run the tests")])], mode="json"
    )[0]
    with database.sessions.begin() as session:
        item = ThreadInbox(thread_id=thread_id, sequence=1, payload=payload)
        session.add(item)
        session.flush()
        item_id = item.id
        assert item.status == "pending"
        assert item.consumed_at is None

    with database.sessions.begin() as session:
        item = session.get(ThreadInbox, item_id)
        assert item.id.version == 7
        assert item.payload == payload
        item.status = "consumed"
        item.consumed_at = datetime.now(UTC)

    with database.sessions() as session:
        item = session.get(ThreadInbox, item_id)
        assert item.status == "consumed"
        assert item.consumed_at is not None


@pytest.mark.parametrize("model", [ThreadMessage, ThreadEvent, ThreadInbox])
def test_per_thread_sequences_reject_duplicates(database, thread_id, model):
    values = {"kind": "part_start"} if model is ThreadEvent else {}
    with database.sessions.begin() as session:
        session.add(model(thread_id=thread_id, sequence=1, payload={}, **values))
    with pytest.raises(IntegrityError), database.sessions.begin() as session:
        session.add(model(thread_id=thread_id, sequence=1, payload={}, **values))


@pytest.mark.parametrize("model", [ThreadMessage, ThreadEvent, ThreadInbox])
def test_history_and_inbox_reject_missing_threads(database, model):
    values = {"kind": "part_start"} if model is ThreadEvent else {}
    with pytest.raises(IntegrityError), database.sessions.begin() as session:
        session.add(model(thread_id=uuid7(), sequence=1, payload={}, **values))


def test_threads_reject_missing_project_and_parent(database, thread_id):
    with pytest.raises(IntegrityError), database.sessions.begin() as session:
        session.add(Thread(project_id=uuid7()))
    with database.sessions() as session:
        project_id = session.get(Thread, thread_id).project_id
    with pytest.raises(IntegrityError), database.sessions.begin() as session:
        session.add(Thread(project_id=project_id, parent_thread_id=uuid7()))
    with pytest.raises(IntegrityError), database.sessions.begin() as session:
        session.get(Thread, thread_id).parent_thread_id = thread_id


@pytest.mark.parametrize("values", [
    {"sequence": 0}, {"sequence": -1}, {"format_version": 0}, {"status": "unknown"},
])
def test_inbox_rejects_invalid_order_version_or_status(database, thread_id, values):
    fields = {"sequence": 1, "payload": {}, **values}
    with pytest.raises(IntegrityError), database.sessions.begin() as session:
        session.add(ThreadInbox(thread_id=thread_id, **fields))


def test_upgrade_preserves_existing_projects(tmp_path):
    url = get_database_url(tmp_path / "legacy.sqlite3")
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).parents[1] / "src/brunel/migrations")
    )
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "0001_create_projects")
    db = Database(url)
    try:
        with db.engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO projects (id, name, location) VALUES (42, 'Brunel', '/work/brunel')"
            ))
        bootstrap(url)
        bootstrap(url)
        with db.sessions() as session:
            project = session.scalars(select(Project)).one()
            assert project.id.version == 7
            assert project.name == "Brunel"
            assert project.local_dir == "/work/brunel"
            assert project.git_url is None
            assert project.created_at is not None
        assert "projects_legacy" not in inspect(db.engine).get_table_names()
        command.downgrade(config, "0001_create_projects")
        with db.engine.connect() as connection:
            assert connection.execute(text("SELECT name, location FROM projects")).one() == (
                "Brunel", "/work/brunel"
            )
        bootstrap(url)
        with db.sessions() as session:
            assert session.scalars(select(Project)).one().local_dir == "/work/brunel"
    finally:
        db.close()

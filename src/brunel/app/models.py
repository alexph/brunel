from datetime import datetime
from typing import Any
from uuid import UUID, uuid7

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for Brunel's persisted models."""

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Project(Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String, nullable=False)
    local_dir: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    git_url: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Thread(Base):
    __tablename__ = "threads"
    __table_args__ = (CheckConstraint("parent_thread_id != id", name="ck_threads_not_own_parent"),)

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str | None] = mapped_column(String)
    parent_thread_id: Mapped[UUID | None] = mapped_column(ForeignKey("threads.id"), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ThreadMessage(Base):
    __tablename__ = "thread_messages"
    __table_args__ = (
        UniqueConstraint("thread_id", "sequence", name="uq_thread_messages_sequence"),
        CheckConstraint("sequence > 0", name="ck_thread_messages_sequence"),
        CheckConstraint("format_version > 0", name="ck_thread_messages_format_version"),
    )

    thread_id: Mapped[UUID] = mapped_column(ForeignKey("threads.id"))
    sequence: Mapped[int]
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    format_version: Mapped[int] = mapped_column(server_default="1")


class ThreadEvent(Base):
    __tablename__ = "thread_events"
    __table_args__ = (
        UniqueConstraint("thread_id", "sequence", name="uq_thread_events_sequence"),
        CheckConstraint("sequence > 0", name="ck_thread_events_sequence"),
        CheckConstraint("format_version > 0", name="ck_thread_events_format_version"),
    )

    thread_id: Mapped[UUID] = mapped_column(ForeignKey("threads.id"))
    sequence: Mapped[int]
    kind: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    format_version: Mapped[int] = mapped_column(server_default="1")


class ThreadInbox(Base):
    __tablename__ = "thread_inbox"
    __table_args__ = (
        UniqueConstraint("thread_id", "sequence", name="uq_thread_inbox_sequence"),
        CheckConstraint("sequence > 0", name="ck_thread_inbox_sequence"),
        CheckConstraint("format_version > 0", name="ck_thread_inbox_format_version"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'consumed', 'cancelled')",
            name="ck_thread_inbox_status",
        ),
    )

    thread_id: Mapped[UUID] = mapped_column(ForeignKey("threads.id"))
    sequence: Mapped[int]
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    format_version: Mapped[int] = mapped_column(server_default="1")
    status: Mapped[str] = mapped_column(String, server_default="pending")
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

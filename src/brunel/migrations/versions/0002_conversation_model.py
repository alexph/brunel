"""Add UUID projects, threads, conversation history, and inbox storage."""

from uuid import uuid7

import sqlalchemy as sa
from alembic import op

revision = "0002_conversation_model"
down_revision = "0001_create_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("projects", "projects_legacy")
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("local_dir", sa.String(), nullable=False),
        sa.Column("git_url", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.UniqueConstraint("local_dir", name="uq_projects_local_dir"),
    )
    connection = op.get_bind()
    legacy = sa.table("projects_legacy", sa.column("name"), sa.column("location"))
    projects = sa.table(
        "projects",
        sa.column("id", sa.Uuid()),
        sa.column("name"),
        sa.column("local_dir"),
    )
    for project in connection.execute(sa.select(legacy)).mappings():
        connection.execute(
            projects.insert().values(
                id=uuid7(), name=project["name"], local_dir=project["location"]
            )
        )
    op.drop_table("projects_legacy")

    op.create_table(
        "threads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column(
            "parent_thread_id", sa.Uuid(), sa.ForeignKey("threads.id"), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("parent_thread_id != id", name="ck_threads_not_own_parent"),
    )
    op.create_index("ix_threads_project_id", "threads", ["project_id"])
    op.create_index("ix_threads_parent_thread_id", "threads", ["parent_thread_id"])
    op.create_table(
        "thread_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("format_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "thread_id", "sequence", name="uq_thread_messages_sequence"
        ),
        sa.CheckConstraint("sequence > 0", name="ck_thread_messages_sequence"),
        sa.CheckConstraint(
            "format_version > 0", name="ck_thread_messages_format_version"
        ),
    )
    op.create_table(
        "thread_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("format_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("thread_id", "sequence", name="uq_thread_events_sequence"),
        sa.CheckConstraint("sequence > 0", name="ck_thread_events_sequence"),
        sa.CheckConstraint(
            "format_version > 0", name="ck_thread_events_format_version"
        ),
    )
    op.create_table(
        "thread_inbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("format_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("thread_id", "sequence", name="uq_thread_inbox_sequence"),
        sa.CheckConstraint("sequence > 0", name="ck_thread_inbox_sequence"),
        sa.CheckConstraint("format_version > 0", name="ck_thread_inbox_format_version"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'consumed', 'cancelled')",
            name="ck_thread_inbox_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("thread_inbox")
    op.drop_table("thread_events")
    op.drop_table("thread_messages")
    op.drop_index("ix_threads_parent_thread_id", table_name="threads")
    op.drop_index("ix_threads_project_id", table_name="threads")
    op.drop_table("threads")
    op.create_table(
        "projects_legacy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False, unique=True),
    )
    connection = op.get_bind()
    projects = sa.table("projects", sa.column("name"), sa.column("local_dir"))
    legacy = sa.table(
        "projects_legacy", sa.column("id"), sa.column("name"), sa.column("location")
    )
    for index, project in enumerate(
        connection.execute(sa.select(projects)).mappings(), start=1
    ):
        connection.execute(
            legacy.insert().values(
                id=index, name=project["name"], location=project["local_dir"]
            )
        )
    op.drop_table("projects")
    op.rename_table("projects_legacy", "projects")

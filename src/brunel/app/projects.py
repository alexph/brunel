from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from brunel.app.db import Database
from brunel.app.models import Project
from brunel.protocol import ProjectView


def canonical_directory(value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("Project path must be absolute")
    path = path.resolve()
    if not path.is_dir():
        raise ValueError("Project path must be an existing directory")
    return str(path)


def view(project: Project) -> ProjectView:
    return ProjectView(id=project.id, name=project.name, location=project.location)


def list_projects(database: Database) -> list[ProjectView]:
    with database.sessions() as session:
        return [view(project) for project in session.scalars(
            select(Project).order_by(Project.name, Project.location)
        )]


def find_project(database: Database, location: str) -> ProjectView | None:
    with database.sessions() as session:
        project = session.scalar(select(Project).where(Project.location == location))
        return view(project) if project is not None else None


def add_project(database: Database, location: str) -> tuple[ProjectView, bool]:
    with database.sessions.begin() as session:
        result = session.execute(insert(Project).values(
            name=Path(location).name or location, location=location,
        ).on_conflict_do_nothing(index_elements=[Project.location]))
        project = session.scalar(select(Project).where(Project.location == location))
        assert project is not None
        return view(project), result.rowcount == 1

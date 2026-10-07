from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine, inspect, text

from brunel.app.bootstrap import bootstrap
from brunel.app.db import DATABASE_FILENAME, get_database_url, upgrade_database


def test_get_database_url_uses_user_data_directory(monkeypatch, tmp_path: Path) -> None:
    data_path = tmp_path / "nested" / "data"
    monkeypatch.setattr(
        "brunel.app.db.get_locations", lambda: SimpleNamespace(data=data_path)
    )

    assert get_database_url().endswith(f"/{DATABASE_FILENAME}")
    assert data_path.is_dir()


def test_bootstrap_upgrades_explicit_database(tmp_path: Path) -> None:
    database_path = tmp_path / "brunel.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"

    bootstrap(database_url)

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert inspector.get_table_names() == ["alembic_version", "projects"]
    project_columns = {column["name"]: column for column in inspector.get_columns("projects")}
    assert set(project_columns) == {"id", "name", "location"}
    assert project_columns["id"]["primary_key"] == 1
    assert {tuple(index["column_names"]) for index in inspector.get_unique_constraints("projects")} == {
        ("location",)
    }
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_create_projects"


def test_upgrade_database_is_idempotent(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'brunel.sqlite3'}"

    upgrade_database(database_url)
    upgrade_database(database_url)

    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar_one() == 1

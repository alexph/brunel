from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL

from brunel.app.locations import get_locations

DATABASE_FILENAME = "brunel.sqlite3"


def get_database_url() -> str:
    """Return the SQLite URL for the current user's Brunel data store."""
    database_path = get_locations().data / DATABASE_FILENAME
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return str(URL.create("sqlite+pysqlite", database=str(database_path)))


def upgrade_database(database_url: str | None = None) -> None:
    """Upgrade a database to the latest bundled Alembic revision."""
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).parent.parent / "migrations")
    )
    config.set_main_option("sqlalchemy.url", database_url or get_database_url())
    command.upgrade(config, "head")


def bootstrap(database_url: str | None = None) -> None:
    """Prepare Brunel's persistent state before the application starts."""
    upgrade_database(database_url)

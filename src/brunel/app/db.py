from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

DATABASE_FILENAME = "brunel.sqlite3"


def get_database_url(database_path: Path) -> str:
    """Build a SQLite URL without creating files or directories."""
    return str(URL.create("sqlite+pysqlite", database=str(database_path)))


def upgrade_database(database_url: str) -> None:
    """Upgrade a database to the latest bundled Alembic revision."""
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).parent.parent / "migrations")
    )
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")


def bootstrap(database_url: str) -> None:
    """Prepare Brunel's persistent state before the application starts."""
    database = make_url(database_url).database
    if database and database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)
    upgrade_database(database_url)


class Database:
    def __init__(self, database_url: str):
        self.engine: Engine = create_engine(database_url)
        self.sessions: sessionmaker[Session] = sessionmaker(self.engine)

    def close(self) -> None:
        self.engine.dispose()

from brunel.app.db import upgrade_database


def bootstrap(database_url: str | None = None) -> None:
    """Prepare Brunel's persistent state before the application starts."""
    upgrade_database(database_url)

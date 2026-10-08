import fcntl
import os
import socket
from contextlib import closing, suppress
from pathlib import Path

import uvicorn

from brunel.app.db import Database, bootstrap
from brunel.app.runtime import load_runtime_config
from brunel.daemon.paths import runtime_directory
from brunel.daemon.state import DaemonState
from brunel.rest.app import create_app


def server(
    *,
    service: bool = False,
    idle_timeout: float | None = None,
    config_file: Path | None = None,
) -> None:
    runtime = load_runtime_config(
        config_file, service=service, idle_timeout=idle_timeout
    )
    directory = runtime_directory()
    path = directory / "daemon.sock"

    with (directory / "daemon.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return

        bootstrap(runtime.database_url)

        with closing(Database(runtime.database_url)) as database:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                try:
                    # Only the lock owner may replace or remove the endpoint.
                    path.unlink(missing_ok=True)
                    listener.bind(str(path))
                    os.chmod(path, 0o600)
                    listener.listen(128)
                    state = DaemonState(
                        service=runtime.service,
                        idle_timeout=runtime.idle_timeout,
                    )
                    daemon = uvicorn.Server(
                        uvicorn.Config(
                            create_app(
                                state,
                                lambda: setattr(daemon, "should_exit", True),
                                runtime=runtime,
                                database=database,
                            ),
                            workers=1,
                            log_level="warning",
                            timeout_graceful_shutdown=2,
                        )
                    )
                    daemon.run(sockets=[listener])
                finally:
                    with suppress(FileNotFoundError):
                        path.unlink()

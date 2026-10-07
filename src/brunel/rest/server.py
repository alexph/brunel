import fcntl
import os
import socket
from contextlib import suppress

import uvicorn

from brunel.daemon.paths import runtime_directory
from brunel.daemon.state import DaemonState
from brunel.rest.app import create_app


def server(*, service: bool = False, idle_timeout: float = 30) -> None:
    directory = runtime_directory()
    path = directory / "daemon.sock"
    with (directory / "daemon.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        # Only the lock owner may replace a stale endpoint or remove it on exit.
        path.unlink(missing_ok=True)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            listener.bind(str(path))
            os.chmod(path, 0o600)
            listener.listen(128)
            state = DaemonState(service=service, idle_timeout=idle_timeout)
            daemon = uvicorn.Server(uvicorn.Config(
                create_app(state, lambda: setattr(daemon, "should_exit", True)),
                workers=1, log_level="warning", timeout_graceful_shutdown=2,
            ))
            daemon.run(sockets=[listener])
        finally:
            listener.close()
            with suppress(FileNotFoundError):
                path.unlink()

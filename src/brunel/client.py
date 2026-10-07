import asyncio
import os
import subprocess
import sys
import time
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from websockets.asyncio.client import unix_connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake

from brunel.daemon.paths import runtime_directory
from brunel.protocol import PROTOCOL_VERSION, DaemonStatus, StatusEvent


class ProtocolMismatch(RuntimeError):
    pass


class DaemonClient:
    def __init__(self, directory: Path | None = None):
        self.directory = directory if directory is not None else runtime_directory()
        self.socket = self.directory / "daemon.sock"
        self.process: subprocess.Popen | None = None

    async def status(self) -> DaemonStatus:
        transport = httpx.AsyncHTTPTransport(uds=str(self.socket))
        async with httpx.AsyncClient(transport=transport, base_url="http://brunel", timeout=1) as client:
            response = await client.get("/status")
            response.raise_for_status()
            status = DaemonStatus.model_validate(response.json())
            self.check_version(status)
            return status

    @staticmethod
    def check_version(status: DaemonStatus) -> None:
        if status.protocol_version != PROTOCOL_VERSION:
            raise ProtocolMismatch("The running daemon uses a different protocol version; restart it.")

    def spawn(self) -> None:
        # A daemon is detached from the terminal that first requested it.
        with (self.directory / "daemon.log").open("ab") as log:
            self.process = subprocess.Popen(
                [sys.executable, "-m", "brunel.cli", "server"],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                start_new_session=True,
                env={**os.environ, "BRUNEL_RUNTIME_DIR": str(self.directory)},
            )

    async def ensure_running(self, timeout: float = 10) -> DaemonStatus:
        deadline = time.monotonic() + timeout
        next_spawn = 0.0
        while True:
            try:
                return await self.status()
            except (httpx.TransportError, httpx.HTTPStatusError):
                now = time.monotonic()
                if now >= deadline:
                    raise RuntimeError(f"Daemon did not become ready; see {self.directory / 'daemon.log'}")
                if now >= next_spawn and (self.process is None or self.process.poll() is not None):
                    self.spawn()
                    next_spawn = now + 0.5
                await asyncio.sleep(0.1)

    async def events(self) -> AsyncIterator[StatusEvent]:
        await self.ensure_running()
        async with unix_connect(str(self.socket), uri="ws://brunel/events", open_timeout=2) as websocket:
            async for message in websocket:
                event = StatusEvent.model_validate_json(message)
                self.check_version(event.payload)
                yield event


CONNECTION_ERRORS = (OSError, TimeoutError, ConnectionClosed, InvalidHandshake)

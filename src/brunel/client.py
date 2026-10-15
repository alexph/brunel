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
from brunel.protocol import PROTOCOL_VERSION, DaemonStatus, Event, ProjectView, StatusEvent, event_adapter


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

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        await self.ensure_running()
        transport = httpx.AsyncHTTPTransport(uds=str(self.socket))
        async with httpx.AsyncClient(transport=transport, base_url="http://brunel", timeout=5) as client:
            response = await client.request(method, path, **kwargs)
            if response.status_code != 404:
                response.raise_for_status()
            return response

    async def projects(self) -> list[ProjectView]:
        response = await self.request("GET", "/projects")
        response.raise_for_status()
        return [ProjectView.model_validate(item) for item in response.json()]

    async def project_by_path(self, path: Path) -> ProjectView | None:
        response = await self.request("GET", "/projects/by-path", params={"path": str(path)})
        return None if response.status_code == 404 else ProjectView.model_validate(response.json())

    async def create_project(self, path: Path) -> ProjectView:
        response = await self.request("POST", "/projects", json={"location": str(path)})
        response.raise_for_status()
        return ProjectView.model_validate(response.json())

    async def events(self) -> AsyncIterator[Event]:
        await self.ensure_running()
        async with unix_connect(str(self.socket), uri="ws://brunel/events", open_timeout=2) as websocket:
            async for message in websocket:
                event = event_adapter.validate_json(message)
                if isinstance(event, StatusEvent):
                    self.check_version(event.payload)
                yield event


CONNECTION_ERRORS = (OSError, TimeoutError, ConnectionClosed, InvalidHandshake)

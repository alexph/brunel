import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress

import anyio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from brunel.app.db import Database
from brunel.app.runtime import RuntimeConfig
from brunel.daemon.state import DaemonState
from brunel.protocol import DaemonStatus


def create_app(
    state: DaemonState, shutdown: Callable[[], None], *,
    runtime: RuntimeConfig | None = None, database: Database | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        monitor = asyncio.create_task(state.monitor(shutdown))
        try:
            yield
        finally:
            monitor.cancel()
            with suppress(asyncio.CancelledError):
                await monitor

    app = FastAPI(lifespan=lifespan)
    app.state.daemon = state
    app.state.runtime = runtime
    app.state.database = database

    @app.middleware("http")
    async def track_request(request, call_next):
        if state.closing:
            return JSONResponse({"detail": "Daemon is shutting down"}, status_code=503)
        state.requests += 1
        state.changed.set()
        try:
            return await call_next(request)
        finally:
            state.requests -= 1
            state.changed.set()

    @app.get("/status", response_model=DaemonStatus)
    async def status():
        return state.status()

    @app.websocket("/events")
    async def events(websocket: WebSocket):
        if state.closing:
            await websocket.close(code=1012)
            return
        subscriber = state.subscribe()
        tasks: set[asyncio.Task] = set()
        try:
            await websocket.accept()

            async def receive():
                while True:
                    message = await websocket.receive()
                    if message["type"] == "websocket.disconnect":
                        return

            async def send():
                while True:
                    event = await subscriber.queue.get()
                    await websocket.send_text(event.model_dump_json())

            tasks = {
                asyncio.create_task(receive()), asyncio.create_task(send()),
                asyncio.create_task(subscriber.overflow.wait()),
            }
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
            if subscriber.overflow.is_set():
                await websocket.close(code=1013, reason="Client fell behind; reconnect for a snapshot")
        except WebSocketDisconnect:
            pass
        finally:
            for task in tasks:
                task.cancel()
            state.unsubscribe(subscriber)
            with anyio.CancelScope(shield=True):
                await asyncio.gather(*tasks, return_exceptions=True)

    return app

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from brunel.protocol import DaemonStatus, StatusEvent


class Subscriber:
    def __init__(self, capacity: int):
        self.queue: asyncio.Queue[StatusEvent] = asyncio.Queue(maxsize=capacity)
        self.overflow = asyncio.Event()


class DaemonState:
    def __init__(self, *, service: bool = False, idle_timeout: float = 30, queue_capacity: int = 64):
        self.service = service
        self.idle_timeout = idle_timeout
        self.queue_capacity = queue_capacity
        self.run_id = str(uuid4())
        self.sequence = 0
        self.live_work = 0
        self.requests = 0
        self.closing = False
        self.subscribers: set[Subscriber] = set()
        self.changed = asyncio.Event()

    def status(self) -> DaemonStatus:
        return DaemonStatus(
            run_id=self.run_id, pid=os.getpid(),
            mode="service" if self.service else "on-demand",
            clients=len(self.subscribers), live_work=self.live_work,
            idle_timeout=self.idle_timeout,
        )

    def publish(self) -> None:
        self.sequence += 1
        event = StatusEvent(type="daemon.status", sequence=self.sequence, payload=self.status())
        for subscriber in self.subscribers:
            try:
                subscriber.queue.put_nowait(event)
            except asyncio.QueueFull:
                subscriber.overflow.set()
        self.changed.set()

    def subscribe(self) -> Subscriber:
        if self.closing:
            raise RuntimeError("Daemon is shutting down")
        subscriber = Subscriber(self.queue_capacity)
        # Register and capture state without yielding to other mutations.
        self.subscribers.add(subscriber)
        self.publish()
        subscriber.queue.get_nowait()
        subscriber.queue.put_nowait(StatusEvent(
            type="snapshot", sequence=self.sequence, payload=self.status(),
        ))
        return subscriber

    def unsubscribe(self, subscriber: Subscriber) -> None:
        self.subscribers.discard(subscriber)
        self.publish()

    @asynccontextmanager
    async def work(self) -> AsyncIterator[None]:
        """Keep the daemon alive while execution needs this process."""
        if self.closing:
            raise RuntimeError("Daemon is shutting down")
        self.live_work += 1
        self.publish()
        try:
            yield
        finally:
            self.live_work -= 1
            self.publish()

    async def monitor(self, shutdown: Callable[[], None]) -> None:
        while True:
            self.changed.clear()
            if self.service or self.subscribers or self.live_work or self.requests:
                await self.changed.wait()
                continue
            try:
                await asyncio.wait_for(self.changed.wait(), timeout=self.idle_timeout)
            except TimeoutError:
                if not (self.subscribers or self.live_work or self.requests):
                    self.closing = True
                    shutdown()
                    return

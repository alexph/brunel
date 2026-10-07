import asyncio
import os
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

from fastapi.testclient import TestClient

from brunel.client import DaemonClient
from brunel.daemon.state import DaemonState
from brunel.rest.app import create_app


def test_shared_snapshots_and_events():
    state = DaemonState(service=True)
    with TestClient(create_app(state, lambda: None)) as client:
        with client.websocket_connect("/events") as first:
            assert first.receive_json()["payload"]["clients"] == 1
            with client.websocket_connect("/events") as second:
                snapshot = second.receive_json()
                update = first.receive_json()
                assert snapshot["type"] == "snapshot"
                assert update["type"] == "daemon.status"
                assert snapshot["sequence"] == update["sequence"]
                assert snapshot["payload"] == update["payload"]
                assert client.get("/status").json()["clients"] == 2
            assert first.receive_json()["payload"]["clients"] == 1


def test_slow_subscriber_is_bounded():
    state = DaemonState(queue_capacity=2)
    subscriber = state.subscribe()
    for _ in range(10):
        state.publish()
    assert subscriber.queue.qsize() == 2
    assert subscriber.overflow.is_set()


def test_idle_lifetime_and_live_work():
    async def check():
        stopped = asyncio.Event()
        state = DaemonState(idle_timeout=0.03)
        monitor = asyncio.create_task(state.monitor(stopped.set))
        subscriber = state.subscribe()
        await asyncio.sleep(0.06)
        assert not stopped.is_set()
        async with state.work():
            state.unsubscribe(subscriber)
            await asyncio.sleep(0.06)
            assert not stopped.is_set()
        await asyncio.wait_for(stopped.wait(), 1)
        await monitor
        assert state.closing

        state = DaemonState(service=True, idle_timeout=0.01)
        monitor = asyncio.create_task(state.monitor(lambda: None))
        await asyncio.sleep(0.03)
        assert not state.closing
        monitor.cancel()
        with suppress(asyncio.CancelledError):
            await monitor

    asyncio.run(check())


def test_real_socket_shared_daemon_and_idle_exit():
    async def check(directory, process):
        first = DaemonClient(directory)
        second = DaemonClient(directory)
        # Wait for the explicitly started short-lived daemon without spawning another.
        for _ in range(100):
            try:
                await first.status()
                break
            except Exception:
                if process.poll() is not None:
                    raise AssertionError("Daemon exited before startup")
                await asyncio.sleep(0.02)
        else:
            raise AssertionError("Daemon startup timed out")
        one = first.events()
        two = second.events()
        try:
            initial = await anext(one)
            snapshot = await anext(two)
            update = await anext(one)
            assert initial.payload.pid == snapshot.payload.pid == process.pid
            assert snapshot.payload == update.payload
            assert snapshot.payload.clients == 2
            await one.aclose()
            assert (await anext(two)).payload.clients == 1
            await asyncio.sleep(0.4)
            assert process.poll() is None
        finally:
            await one.aclose()
            await two.aclose()
        await asyncio.to_thread(process.wait, 3)
        assert process.returncode == 0
        assert not (directory / "daemon.sock").exists()

    with tempfile.TemporaryDirectory(prefix="brn-", dir="/tmp") as name:
        directory = Path(name)
        with (directory / "test.log").open("wb") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "brunel.cli", "server", "--idle-timeout", "0.3"],
                env={**os.environ, "BRUNEL_RUNTIME_DIR": name}, stdout=log, stderr=log,
            )
            try:
                asyncio.run(check(directory, process))
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)


def test_simultaneous_discovery_starts_one_daemon():
    async def check(directory):
        clients = [DaemonClient(directory), DaemonClient(directory)]
        pid = None
        try:
            statuses = await asyncio.gather(*(client.ensure_running() for client in clients))
            assert statuses[0].run_id == statuses[1].run_id
            pid = statuses[0].pid
        finally:
            if pid is not None:
                os.kill(pid, 15)
            for client in clients:
                if client.process is not None:
                    if client.process.poll() is None:
                        client.process.terminate()
                    await asyncio.to_thread(client.process.wait, 5)

    with tempfile.TemporaryDirectory(prefix="brn-", dir="/tmp") as name:
        asyncio.run(check(Path(name)))


def test_two_tuis_share_live_status():
    from brunel.tui.app import BrunelApp
    from textual.widgets import Static

    async def check(directory):
        clients = [DaemonClient(directory), DaemonClient(directory)]
        statuses = await asyncio.gather(*(client.ensure_running() for client in clients))
        first = BrunelApp(client=clients[0])
        second = BrunelApp(client=clients[1])
        try:
            async with first.run_test() as one:
                async with second.run_test() as two:
                    for _ in range(100):
                        await one.pause(0.02)
                        await two.pause(0.02)
                        a = str(first.screen.query_one("#daemon-status", Static).content)
                        b = str(second.screen.query_one("#daemon-status", Static).content)
                        if "2 connected clients" in a and a == b:
                            break
                    else:
                        raise AssertionError(f"TUIs did not share status: {a!r}, {b!r}")
                    assert str(statuses[0].pid) in a
                    await two.press("q")
                for _ in range(100):
                    await one.pause(0.02)
                    if "1 connected clients" in str(first.screen.query_one("#daemon-status", Static).content):
                        break
                else:
                    raise AssertionError("Remaining TUI did not receive disconnect update")
                await one.press("q")
        finally:
            os.kill(statuses[0].pid, 15)
            for client in clients:
                if client.process is not None:
                    await asyncio.to_thread(client.process.wait, 5)

    with tempfile.TemporaryDirectory(prefix="brn-", dir="/tmp") as name:
        asyncio.run(check(Path(name)))

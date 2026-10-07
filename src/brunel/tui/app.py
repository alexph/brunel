import asyncio
from pathlib import Path

from textual.app import App
from textual import work
from textual.widgets import Static

from brunel.client import CONNECTION_ERRORS, DaemonClient, ProtocolMismatch

from brunel.tui.screens import MainScreen, ProjectScreen


class BrunelApp(App):
    TITLE = "Brunel"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, project_path: Path | None = None, *, client: DaemonClient | None = None):
        super().__init__()
        self.project_path = project_path
        self.client = client

    def on_mount(self) -> None:
        if self.project_path is None:
            self.push_screen(MainScreen())
        else:
            self.push_screen(ProjectScreen(self.project_path))
        self.watch_daemon()

    @work(exclusive=True)
    async def watch_daemon(self) -> None:
        widget = self.screen.query_one("#daemon-status", Static)
        try:
            client = self.client or DaemonClient()
            while True:
                try:
                    async for event in client.events():
                        status = event.payload
                        widget.update(
                            f"Daemon {status.pid} · {status.mode} · "
                            f"{status.clients} connected clients · {status.live_work} live work"
                        )
                    widget.update("Daemon disconnected; reconnecting…")
                except CONNECTION_ERRORS:
                    widget.update("Daemon disconnected; reconnecting…")
                await asyncio.sleep(0.5)
        except (RuntimeError, ProtocolMismatch) as error:
            widget.update(str(error))

import asyncio
from pathlib import Path

import httpx
from textual import work
from textual.app import App
from textual.widgets import Static

from brunel.client import CONNECTION_ERRORS, DaemonClient
from brunel.protocol import ProjectEvent, ProjectView, StatusEvent
from brunel.tui.screens import MainScreen, ProjectScreen, TrustProjectScreen
from brunel.tui.themes import arctic_theme, blueprint_theme
from brunel.tui.widgets import ProjectTable


class BrunelApp(App):
    TITLE = "Brunel"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(
        self, project_path: Path | None = None, *, client: DaemonClient | None = None
    ):
        super().__init__()
        self.project_path = project_path
        self.client = client
        self.connection_text = "Connecting to daemon…"
        self.main_screen = MainScreen()
        self.projects_lock = asyncio.Lock()

    async def on_mount(self) -> None:
        self.register_theme(arctic_theme)
        self.register_theme(blueprint_theme)
        self.theme = "blueprint"
        await self.push_screen(self.main_screen)
        try:
            self.client = self.client or DaemonClient()
        except (OSError, RuntimeError) as error:
            self.set_status(str(error))
            return
        self.watch_daemon()
        self.initialize_project()

    def set_status(self, message: str) -> None:
        self.connection_text = message
        for screen in self.screen_stack:
            for widget in screen.query("#daemon-status"):
                widget.update(message)

    async def refresh_projects(self) -> None:
        async with self.projects_lock:
            projects = await self.client.projects()
            listing = self.main_screen.query_one("#project-list", ProjectTable)
            listing.set_projects(projects)
            # self.main_screen.query_one("#project-list-message", Static).update(
            #     "Projects" if projects else "No projects yet. Open a folder with brunel PATH."
            # )
            pass

    @work(exclusive=True, group="project-entry")
    async def initialize_project(self) -> None:
        try:
            if self.project_path is not None:
                path = self.project_path.expanduser().resolve()
                project = await self.client.project_by_path(path)
                if project is None:
                    project = await self.push_screen_wait(TrustProjectScreen(path))
                if project is not None:
                    self.open_registered_project(project)
            await self.refresh_projects()
        except (httpx.HTTPError, OSError, RuntimeError) as error:
            # self.main_screen.query_one("#project-list-message", Static).update(
            #     f"Could not load projects: {error}"
            # )
            pass

    def open_registered_project(self, project: ProjectView) -> None:
        self.push_screen(ProjectScreen(project), self.project_closed)
        self.call_after_refresh(lambda: self.set_status(self.connection_text))

    def project_closed(self, result=None) -> None:
        self.set_status(self.connection_text)

    @work(exclusive=True, group="daemon-events")
    async def watch_daemon(self) -> None:
        try:
            while True:
                try:
                    async for event in self.client.events():
                        if isinstance(event, StatusEvent):
                            status = event.payload
                            self.set_status(
                                f"Daemon {status.pid} · {status.mode} · "
                                f"{status.clients} connected clients · {status.live_work} live work"
                            )
                        if isinstance(event, ProjectEvent) or event.type == "snapshot":
                            await self.refresh_projects()
                    self.set_status("Daemon disconnected; reconnecting…")
                except (*CONNECTION_ERRORS, httpx.HTTPError):
                    self.set_status("Daemon disconnected; reconnecting…")
                await asyncio.sleep(0.5)
        except RuntimeError as error:
            self.set_status(str(error))

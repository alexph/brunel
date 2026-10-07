from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class MainScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Connecting to daemon…", id="daemon-status", markup=False)
        yield Static("Projects\n\nProject listing is not connected yet.")
        yield Footer()


class ProjectScreen(Screen):
    def __init__(self, project_path: Path):
        super().__init__()
        self.project_path = project_path

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Connecting to daemon…", id="daemon-status", markup=False)
        yield Static(
            f"Project: {self.project_path}\n\n"
            "Running work is not connected yet.\n"
            "This directory has not been registered or trusted by opening this screen.",
            markup=False,
        )
        yield Footer()

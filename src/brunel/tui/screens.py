from pathlib import Path

import httpx
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Static

from brunel.protocol import ProjectView
from brunel.tui.chat import ChatScreen
from brunel.tui.conversation import ConversationStore
from brunel.tui.stores import StoreKey, StoreRouter
from brunel.tui.widgets import ProjectTable


class MainScreen(Screen):
    # DEFAULT_CSS = """
    # MainScreen #project-list-message { height: auto; margin: 1 2; }
    # MainScreen ProjectTable { height: 1fr; margin: 0 2 1 2; }
    # """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Connecting to daemon…", id="daemon-status", markup=False)
        # yield Static("Projects", id="project-list-message", markup=False)
        yield ProjectTable(id="project-list")
        yield Footer()

    def on_project_table_open_project(self, event: ProjectTable.OpenProject) -> None:
        self.app.open_registered_project(event.project)


class ProjectScreen(ChatScreen):
    BINDINGS = [("escape", "projects", "Projects")]

    def __init__(self, project: ProjectView, *, router: StoreRouter | None = None):
        router = router if router is not None else StoreRouter()
        key = StoreKey("conversation", f"project:{project.id}:draft")
        try:
            store = router.get(key)
        except KeyError:
            store = ConversationStore(key.id)
            router.register(key, store)
        super().__init__(store=store, router=router, key=key)
        self.project = project
        self.project_path = Path(project.location)
        self.sub_title = project.name

    def action_projects(self) -> None:
        self.app.pop_screen()


class TrustProjectScreen(ModalScreen[ProjectView | None]):
    DEFAULT_CSS = """
    TrustProjectScreen { align: center middle; background: $background 70%; }
    TrustProjectScreen #trust-dialog {
        width: 70; max-width: 95%; height: auto;
        padding: 1 2; border: round $primary; background: $surface;
    }
    TrustProjectScreen Static { height: auto; margin-bottom: 1; }
    TrustProjectScreen Horizontal { height: auto; align-horizontal: center; }
    TrustProjectScreen Button { margin: 0 1; }
    TrustProjectScreen #trust-error { color: $error; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self.submitting = False

    def compose(self) -> ComposeResult:
        with Vertical(id="trust-dialog"):
            yield Static("Trust this folder and add a project?")
            yield Static(str(self.path), markup=False)
            yield Static(
                "Trusting allows Brunel to load project configuration and run work "
                "in this folder. Only trust folders whose contents you trust."
            )
            yield Static("", id="trust-error", markup=False)
            with Horizontal():
                yield Button(
                    "Trust and add project", variant="primary", id="trust-confirm"
                )
                yield Button("Cancel", id="trust-cancel")

    def on_mount(self) -> None:
        self.query_one("#trust-cancel", Button).focus()

    def action_cancel(self) -> None:
        if not self.submitting:
            self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "trust-cancel":
            self.action_cancel()
        elif event.button.id == "trust-confirm":
            self.confirm()

    @work(exclusive=True)
    async def confirm(self) -> None:
        self.submitting = True
        for button in self.query(Button):
            button.disabled = True
        try:
            project = await self.app.client.create_project(self.path)
        except (httpx.HTTPError, OSError, RuntimeError) as error:
            self.query_one("#trust-error", Static).update(
                f"Could not add project: {error}"
            )
        else:
            self.dismiss(project)
        finally:
            self.submitting = False
            for button in self.query(Button):
                button.disabled = False

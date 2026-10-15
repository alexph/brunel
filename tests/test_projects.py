import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from brunel.app.db import Database, bootstrap, get_database_url
from brunel.app import projects
from brunel.daemon.state import DaemonState
from brunel.rest.app import create_app
from brunel.tui.app import BrunelApp
from brunel.tui.screens import MainScreen, ProjectScreen, TrustProjectScreen
from textual.widgets import Static
from brunel.tui.widgets import ProjectTable


@pytest.fixture
def database(tmp_path):
    url = get_database_url(tmp_path / "database.sqlite3")
    bootstrap(url)
    db = Database(url)
    try:
        yield db
    finally:
        db.close()


def test_endpoints_lookup_create_and_broadcast(database, tmp_path):
    state = DaemonState(service=True)
    with TestClient(create_app(state, lambda: None, database=database)) as client:
        assert client.get("/projects").json() == []
        assert client.get("/projects/by-path", params={"path": str(tmp_path)}).status_code == 404
        with client.websocket_connect("/events") as events:
            events.receive_json()
            response = client.post("/projects", json={"location": str(tmp_path)})
            assert response.status_code == 200
            project = response.json()
            event = events.receive_json()
            assert event["type"] == "project.created"
            assert event["payload"] == project
            assert client.get("/projects/by-path", params={"path": str(tmp_path / ".")}).json() == project
            assert client.post("/projects", json={"location": str(tmp_path)}).json() == project
            assert client.get("/projects").json() == [project]


def test_path_validation_and_symlink_identity(database, tmp_path):
    folder = tmp_path / "folder"
    folder.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(folder, target_is_directory=True)
    file = tmp_path / "file"
    file.write_text("content")
    with TestClient(create_app(DaemonState(service=True), lambda: None, database=database)) as client:
        for path in ("relative", str(tmp_path / "missing"), str(file)):
            assert client.post("/projects", json={"location": path}).status_code == 422
        created = client.post("/projects", json={"location": str(alias)}).json()
        assert created["location"] == str(folder.resolve())
        assert client.post("/projects", json={"location": str(folder)}).json() == created
        assert len(client.get("/projects").json()) == 1


def test_concurrent_creation_returns_one_project(database, tmp_path):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: projects.add_project(database, str(tmp_path)), range(2)))
    assert results[0][0] == results[1][0]
    assert sum(created for _, created in results) == 1
    assert len(projects.list_projects(database)) == 1


class LocalClient:
    def __init__(self, database, state):
        self.database = database
        self.state = state
        self.fail_creation = False

    async def projects(self):
        return await asyncio.to_thread(projects.list_projects, self.database)

    async def project_by_path(self, path):
        return await asyncio.to_thread(projects.find_project, self.database, str(path))

    async def create_project(self, path):
        if self.fail_creation:
            raise RuntimeError("Test creation failure")
        project, created = await asyncio.to_thread(projects.add_project, self.database, str(path))
        if created:
            self.state.project_created(project)
        return project

    async def events(self):
        subscriber = self.state.subscribe()
        try:
            while True:
                yield await subscriber.queue.get()
        finally:
            self.state.unsubscribe(subscriber)


async def wait_screen(pilot, app, screen):
    for _ in range(100):
        await pilot.pause(0.01)
        if isinstance(app.screen, screen):
            return
    raise AssertionError(f"Expected {screen}, got {type(app.screen)}")


def test_trust_cancel_confirm_and_existing_project(database, tmp_path):
    async def check():
        client = LocalClient(database, DaemonState(service=True))
        app = BrunelApp(tmp_path, client=client)
        async with app.run_test(size=(100, 40)) as pilot:
            await wait_screen(pilot, app, TrustProjectScreen)
            assert projects.list_projects(database) == []
            await pilot.click("#trust-cancel")
            await wait_screen(pilot, app, MainScreen)
            assert projects.list_projects(database) == []

        app = BrunelApp(tmp_path, client=client)
        async with app.run_test(size=(100, 40)) as pilot:
            await wait_screen(pilot, app, TrustProjectScreen)
            client.fail_creation = True
            await pilot.click("#trust-confirm")
            await pilot.pause()
            assert isinstance(app.screen, TrustProjectScreen)
            assert "Test creation failure" in str(app.screen.query_one("#trust-error", Static).content)
            assert projects.list_projects(database) == []
            client.fail_creation = False
            await pilot.pause(0.5)
            await pilot.click("#trust-confirm")
            await wait_screen(pilot, app, ProjectScreen)
            assert app.screen.project.location == str(tmp_path.resolve())
            await pilot.press("escape")
            await wait_screen(pilot, app, MainScreen)
            await pilot.pause()
            listing = app.screen.query_one("#project-list", ProjectTable)
            assert listing.row_count == 1
            listing.focus()
            await pilot.press("enter")
            await wait_screen(pilot, app, ProjectScreen)

        app = BrunelApp(tmp_path, client=client)
        async with app.run_test() as pilot:
            await wait_screen(pilot, app, ProjectScreen)
            assert len(projects.list_projects(database)) == 1

    asyncio.run(check())


def test_project_list_updates_in_other_tui(database, tmp_path):
    async def check():
        state = DaemonState(service=True)
        one = BrunelApp(client=LocalClient(database, state))
        two = BrunelApp(tmp_path, client=LocalClient(database, state))
        async with one.run_test(size=(100, 40)) as first:
            async with two.run_test(size=(100, 40)) as second:
                await wait_screen(second, two, TrustProjectScreen)
                await second.click("#trust-confirm")
                await wait_screen(second, two, ProjectScreen)
                for _ in range(100):
                    await first.pause(0.01)
                    if one.main_screen.query_one("#project-list", ProjectTable).row_count == 1:
                        break
                else:
                    raise AssertionError("Other TUI did not refresh its project list")

    asyncio.run(check())

from pathlib import Path

from typer.testing import CliRunner

from brunel import cli
from brunel.tui.app import BrunelApp
from brunel.tui.screens import MainScreen, ProjectScreen


def test_launch_routes(tmp_path, monkeypatch):
    launches = []
    monkeypatch.setattr(cli, "launch_tui", lambda project_path=None: launches.append(project_path))
    runner = CliRunner()
    assert runner.invoke(cli.app, []).exit_code == 0
    assert runner.invoke(cli.app, cli.route_args([str(tmp_path)])).exit_code == 0
    assert launches == [None, tmp_path.resolve()]


def test_commands_take_precedence_over_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("server").mkdir()
    assert cli.route_args(["server"]) == ["server"]
    assert cli.route_args(["./server"]) == ["open", "./server"]
    assert cli.route_args(["."]) == ["open", "."]
    assert cli.route_args(["--help"]) == ["--help"]
    assert cli.route_args(["unknown"]) == ["unknown"]


def test_help_and_invalid_paths_do_not_launch(monkeypatch, tmp_path):
    def unexpected_launch(project_path=None):
        raise AssertionError("TUI must not launch")

    monkeypatch.setattr(cli, "launch_tui", unexpected_launch)
    runner = CliRunner()
    assert runner.invoke(cli.app, ["--help"]).exit_code == 0
    assert runner.invoke(cli.app, ["unknown"]).exit_code == 2
    assert runner.invoke(cli.app, cli.route_args([str(tmp_path / "missing")])).exit_code == 2


def test_server_command(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "server", lambda **kwargs: calls.append(kwargs))
    assert CliRunner().invoke(cli.app, ["server"]).exit_code == 0
    assert calls == [{"service": False, "idle_timeout": None, "config_file": None}]


def test_placeholder_screens(tmp_path):
    import asyncio

    async def check():
        class FakeClient:
            async def events(self):
                await asyncio.Event().wait()
                yield

        for path, screen_type in [(None, MainScreen), (tmp_path, ProjectScreen)]:
            app = BrunelApp(project_path=path, client=FakeClient())
            async with app.run_test() as pilot:
                assert isinstance(app.screen, screen_type)
                await pilot.press("q")

    asyncio.run(check())

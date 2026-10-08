import sys
from pathlib import Path

import click
import typer
from typer.main import get_command

from brunel.rest.server import server

app = typer.Typer(help="Manage Brunel projects and running work.")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        launch_tui()


def launch_tui(project_path: Path | None = None) -> None:
    from brunel.tui.app import BrunelApp

    BrunelApp(project_path=project_path).run()


@app.command("open")
def open_project(
    path: Path = typer.Argument(..., exists=True, file_okay=False, resolve_path=True),
):
    """Open a working directory in the project screen."""
    launch_tui(path)


@app.command("server")
def run_server(
    service: bool = typer.Option(
        False, help="Stay alive regardless of connected clients."
    ),
    idle_timeout: float | None = typer.Option(
        None, min=0.1, help="Seconds to wait before idle shutdown (default: 30)."
    ),
    config_file: Path | None = typer.Option(
        None, "--config", exists=True, dir_okay=False, resolve_path=True,
        help="User TOML configuration file.",
    ),
):
    """Run the Brunel server in the foreground."""
    server(service=service, idle_timeout=idle_timeout, config_file=config_file)


def route_args(args: list[str]) -> list[str]:
    """Expand a directory shortcut without swallowing unknown commands."""
    if len(args) != 1:
        return args

    value = args[0]
    command = get_command(app)

    assert isinstance(command, click.Group)

    if value.startswith("-") or value in command.commands:
        return args
    if (
        Path(value).is_dir()
        or value.startswith(("./", "../", "/"))
        or value in (".", "..")
    ):
        return ["open", value]

    return args


def entrypoint() -> None:
    app(args=route_args(sys.argv[1:]))


if __name__ == "__main__":
    entrypoint()

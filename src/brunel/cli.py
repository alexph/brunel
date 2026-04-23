# import sys
import pathlib

import typer

from brunel.app.discovery import build_world

# from brunel.tui.app import tui_app

app = typer.Typer()


@app.command()
def main():
    # if sys.stdout.isatty():
    #     tui_app()
    #
    #
    cwd = pathlib.Path.cwd()
    print(cwd)
    build_world(cwd)

    # print(agent_registry.get_all())
    # print(skill_registry.get_all())
    # print(mcp_registry.get_all())


if __name__ == "__main__":
    app()

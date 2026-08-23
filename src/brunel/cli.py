import typer

from brunel.rest.server import server

app = typer.Typer()


@app.command()
def main():
    server()


if __name__ == "__main__":
    app()

# Repository Guidelines

## Project Overview

Brunel is a Python terminal application for registering trusted local project directories and coordinating multiple TUI clients through one per-user daemon. The current product includes project registration, a Textual UI, REST/WebSocket daemon communication over a Unix socket, SQLite persistence, runtime configuration, and initial agent/skill/MCP discovery. Task execution and project-work integration are not implemented; do not assume those flows exist.

## Architecture & Data Flow

- `src/brunel/cli.py` is the Typer entry point. It routes named commands, directory shorthand, the default TUI launch, and the foreground server.
- `src/brunel/tui/` contains the Textual app, screens, and project table. `BrunelApp` uses `DaemonClient` to start/find the daemon, load projects, register trusted directories, watch events, and reconnect.
- `src/brunel/client.py` is the client boundary: HTTP requests and WebSocket events use the daemon Unix socket. `src/brunel/protocol.py` defines Pydantic wire models and the protocol version.
- `src/brunel/rest/` creates the FastAPI app and server. Startup loads `RuntimeConfig`, acquires the per-user lock, bootstraps SQLite/Alembic, binds the socket, and runs Uvicorn with one worker.
- `src/brunel/daemon/` owns lifecycle state, subscriber queues, runtime paths, idle shutdown, and event broadcasting. WebSocket clients receive a snapshot followed by sequenced events; queue overflow causes disconnect and snapshot-based recovery.
- `src/brunel/app/` contains configuration, locations/discovery, database access, SQLAlchemy models, and project operations. Project paths are validated as existing absolute directories, canonicalized through symlinks, and persisted idempotently with a unique location.
- Project flow: TUI/client request -> FastAPI endpoint -> canonical path validation -> synchronous SQLAlchemy operation in a threadpool -> typed `project.created` broadcast when insertion is new -> TUI refresh/event update.

## Key Directories

- `src/brunel/` — installable package and CLI entry point.
- `src/brunel/app/` — runtime settings, path locations, project domain logic, SQLAlchemy database/model code.
- `src/brunel/daemon/` — daemon state, socket/runtime paths, subscriber and idle-lifecycle handling.
- `src/brunel/rest/` — FastAPI application, routes, and Uvicorn server startup/cleanup.
- `src/brunel/tui/` — Textual application, screens, and widgets.
- `src/brunel/migrations/` — Alembic environment and versioned SQLite migrations.
- `src/brunel/builtins/` — built-in agent and example skill resources; example asset/reference/script directories are placeholders.
- `tests/` — pytest behavior and integration tests.

## Development Commands

Use the locked `uv` environment:

```sh
uv sync
uv run pytest
uv run pytest tests/test_runtime.py
uv build
```

`pytest` is the repository's declared test dependency; no custom test script is defined. `uv build` uses the configured Hatchling backend but is not a project script. For direct migration work, the repository configuration is:

```sh
alembic -c alembic.ini upgrade head
```

Normal daemon startup bootstraps and migrates the database before accepting clients. Documented application commands:

```sh
brunel
brunel .
brunel open PATH
brunel --help
brunel server
brunel server --service
brunel server --idle-timeout 5
brunel server --config /path/to/brunel.toml
```

## Code Conventions & Common Patterns

- Target Python 3.14. Use the existing layered boundaries rather than adding a second transport or configuration path.
- Keep REST payloads and WebSocket events typed with Pydantic models. Protocol changes require updating `src/brunel/protocol.py` and its protocol version compatibility checks.
- Keep configuration immutable: `Settings`, `RuntimeConfig`, and resolved location structures are frozen. Preserve precedence: explicit CLI/initialization values, environment (`BRUNEL_*`), TOML, then defaults.
- Canonicalize project directories before lookup or persistence. Preserve idempotency for repeated, symlink-alias, and concurrent registrations.
- Keep synchronous SQLAlchemy work out of async FastAPI handlers by using the established threadpool boundary. Dispose engines and clean sockets, locks, subprocesses, and WebSocket tasks through context managers or `finally` paths.
- Preserve bounded event queues and reconnect semantics: a dropped/overflowed client must recover through a fresh snapshot, not an unbounded queue.
- Follow existing Python naming: `snake_case` modules/functions, `PascalCase` classes, and `test_*.py` / `test_*` pytest discovery. No repository formatter, linter, or type-checker configuration is present; do not assume one is enforced.

## Important Files

- `pyproject.toml` — project metadata, Python/dependency requirements, `brunel` console script, and Hatchling package configuration.
- `uv.lock` and `.python-version` — locked dependencies and Python 3.14 selection.
- `README.md` — CLI, daemon, socket, event, configuration, and persistence behavior.
- `src/brunel/cli.py` — command routing and entrypoint.
- `src/brunel/client.py` / `src/brunel/protocol.py` — client transport and typed wire contract.
- `src/brunel/rest/app.py` / `src/brunel/rest/server.py` / `src/brunel/rest/endpoints.py` — API, lifecycle, and project routes.
- `src/brunel/daemon/state.py` / `src/brunel/daemon/paths.py` — event/lifecycle state and Unix-socket runtime paths.
- `src/brunel/app/runtime.py` / `settings.py` / `db.py` / `projects.py` — resolved configuration, precedence, migrations, persistence, and project identity.
- `alembic.ini` and `src/brunel/migrations/` — migration configuration and schema history.

## Runtime/Tooling Preferences

- Required runtime: Python `>=3.14`; `.python-version` selects `3.14`.
- Preferred package/dependency manager: `uv`; `uv.lock` is checked in. No uv version is pinned.
- Build backend: Hatchling. Package source is `src/brunel`.
- Runtime stack includes Typer, Textual, FastAPI/Uvicorn, WebSockets/HTTPX, SQLAlchemy, Alembic, Pydantic Settings, and platformdirs.
- Runtime configuration comes from the platform user config (`brunel.toml` by default), `BRUNEL_*` environment variables, and CLI overrides. Relative configured paths resolve against the selected TOML file.
- `BRUNEL_RUNTIME_DIR` overrides the private Unix-socket directory; it must be user-owned and mode `0700`. The daemon writes detached output to `daemon.log` there.
- No Ruff, Black, mypy, Pyright, CI workflow, Docker, Make/task-runner, or release configuration is present.

## Testing & QA

- Framework: pytest (`pytest>=9.0.3`), with conventional `tests/test_*.py` modules and `test_*` functions. The suite currently has 27 test functions across five modules.
- `tests/test_runtime.py` and `tests/test_db.py` cover settings precedence, path resolution, SQLite URL handling, schema, and Alembic bootstrap/idempotency.
- `tests/test_projects.py` covers API persistence, canonicalization, symlink identity, concurrency, trust flow, failure recovery, WebSocket events, and cross-TUI refresh.
- `tests/test_daemon.py` covers snapshots, sequence/events, bounded queues, idle shutdown, Unix-socket sharing, single-daemon startup, and multi-TUI status.
- `tests/test_cli.py` covers Typer routing, invalid paths/help, server dispatch, and initial Textual screens.
- Isolate filesystem/database state with `tmp_path`; isolate `BRUNEL_*` settings with `monkeypatch`. Integration tests intentionally use FastAPI `TestClient`, WebSockets, subprocesses, SQLite inspection, and Textual `run_test()` where those boundaries matter.
- Assert observable behavior: status codes and payloads, event ordering/sequence, CLI exit codes, TUI state, process lifecycle, schema constraints, and cleanup/error paths. No coverage threshold, snapshot suite, CI gate, or repository-specific pytest configuration is defined.

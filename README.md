# brunel

Run `brunel` to open the main terminal screen, or `brunel .` to open the
current directory's project screen. You can also use `brunel open PATH`.
The screens are placeholders; opening a directory does not register or trust it.

Named commands take precedence over directory names. Use `./server` to open a
directory named `server`. Unknown command names produce a CLI error.

Run `brunel server` to start the REST server in the foreground, or
`brunel --help` to see the available commands.

The TUI discovers or starts one detached daemon per user on this machine.
Open two terminals and run `brunel` in each: both screens show the same daemon
PID and connected-client count. Press `q` to disconnect a TUI. The daemon exits
after 30 seconds with no clients or live execution. Durable tasks waiting for
interaction will not need to keep it alive; task execution is not implemented yet.

`brunel server --service` runs the daemon in the foreground without idle shutdown,
ready for a service manager. This does not install a system service.
`brunel server --idle-timeout 5` changes the idle grace period for that run.
If a daemon is already running, another server invocation exits without replacing it.

Local communication uses HTTP and WebSockets over a Unix socket in a private
`brunel-<uid>` directory under the OS temporary directory. `BRUNEL_RUNTIME_DIR`
can override that directory; it must be owned by you with permissions `0700`.
Detached daemon output goes to `daemon.log` in that directory.

`GET /status` returns daemon state. `/events` sends a typed snapshot followed by
status events with sequence numbers scoped to the daemon run. Each client has a
64-event outgoing queue; overflow disconnects that client so it can reconnect for
a fresh snapshot. The TUI reconnects automatically after connection loss.
Remote connections, task persistence, and project registration remain pending.

The daemon loads `brunel.toml` from Brunel's platform-specific user config
directory. A missing default file uses defaults. Set `BRUNEL_CONFIG_FILE` or run
`brunel server --config /path/to/brunel.toml` to select a different file; an
explicitly selected file must exist. For a daemon started by the TUI, use
`BRUNEL_CONFIG_FILE`.

For example:

```toml
data_dir = "./data"
cache_dir = "./cache"
config_dir = "./discovery"
database_path = "./data/brunel.sqlite3"
idle_timeout = 30
```

All configured relative paths are resolved against the selected config file's
directory, including paths supplied through environment variables. `config_dir`
changes agent, skill, and MCP discovery; it does not cause another config file to
be loaded. By default, the database lives in Brunel's user data directory.

Explicit values (such as `--idle-timeout`) override environment variables, which
override TOML values, which override defaults. Environment names include
`BRUNEL_DATA_DIR`, `BRUNEL_CACHE_DIR`, `BRUNEL_CONFIG_DIR`,
`BRUNEL_DATABASE_PATH`, and `BRUNEL_IDLE_TIMEOUT`. Configuration changes take
effect when the daemon restarts; reconnecting a client does not reload them.
The local socket location remains controlled separately by `BRUNEL_RUNTIME_DIR`.

Only the daemon lock owner creates the database directories and runs Alembic
migrations. Database setup completes before clients can connect, and its engine
is disposed when the daemon stops.

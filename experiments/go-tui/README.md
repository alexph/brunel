# Try the Go TUI

Run the conversation experiment from the repository root.
Go 1.26 or newer is required.

```sh
go -C experiments/go-tui run . -project ../..
```

Enter a prompt and press **Enter**.
The demo streams a fixed conversation with a tool and two child agents.
The conversation shows a **Simulated session** label.
The workspace labels its sample rows separately from current state.
No model calls, work commands, skill loading, or real delegation occur.
Startup reads the Git branch through a bounded, read-only Git lookup.
The project path is display context.

The Python application keeps its existing entry point.
The Go module has its own dependencies and does not connect to the daemon.

## Use the keyboard

- Press **Enter** to send a prompt from the composer.
- Press **Left** from an empty focused composer to open the workspace.
- Press **Alt+Enter** or **Ctrl+J** to insert a newline.
- Press **Tab** to move from the composer to the transcript, then settings, then the composer.
- Press **Shift+Tab** to move in reverse.
- Press **F2** to focus the model and effort settings directly.
- Use **Left** or **Right** in settings to select a field.
- Use **Up**, **Down**, or **Enter** to cycle that field's demo values.
- Press **Esc** in settings to return to the composer without stopping a run.
- Use the arrow keys in the transcript to select a tool or agent.
- Press **Enter** in the transcript to expand the selected details.
- Press **Ctrl+O** to toggle details without leaving the composer.
- Press **Page Up** or **Page Down** to scroll the transcript.
- Press **Ctrl+End** to return to the latest output.
- Press **Esc** to stop the run and keep partial output.
- Press **Ctrl+C** to quit.

Type your next draft while output streams.
Submitting during a run preserves that draft.
The unframed composer starts at one row.
It grows upward as text wraps or you add lines.
Its visible height stops at eight rows, with a smaller cap in short terminals.
Longer drafts scroll within the input without losing text.
Deleting or sending the draft shrinks the input again.
Scrolling up pauses automatic following.
The side pane disappears below 110 columns.
Tool and agent details remain available in the transcript.
Windows smaller than 40 columns or 16 rows show a resize hint.
History retains the ten most recent demo turns in memory.
Quitting discards the session.

The row above the input shows model, effort, local machine, and Git branch.
Model and effort are selectable demo values.
They change the displayed selection, while the conversation remains scripted.
Machine and branch are read-only context.
Branch context is read once at startup.
Detached checkouts show a commit ID.
Unavailable Git context shows **unavailable**.

## Browse the workspace

Press **Left** when the composer is empty and focused.
An available **← workspace** hint appears in the conversation footer.
With any draft text present, Left retains normal cursor editing.

The workspace has **Threads**, **Projects**, **Issues**, and **Machines** tabs.
It combines the current UI conversation, project, and local machine with labelled samples.
The **Source** column and details pane identify sample data.

- Use **Left** and **Right**, or **1** through **4**, to switch tabs.
- Use **Up** and **Down** to select a row in the list.
- Press **Tab** or **Shift+Tab** to switch focus between the list and details.
- Use **Up**, **Down**, **Home**, and **End** to scroll focused details.
- Use **Page Up** and **Page Down** to focus and scroll details directly.
- Press **Enter** on the current thread or project to return to the conversation.
- Press **Enter** on a sample or machine to inspect its details.
- Press **Esc** to return to the conversation without cancelling the run.

Each tab retains its selected row.
Details stack beneath the list in terminals narrower than 100 columns.
The conversation keeps its selected activity, expanded details, and scroll position.
Simulated output continues while you browse.

Sample rows are previews.
They cannot create a live thread, connect to a machine, or ingest an issue.
The current thread remains one in-memory UI conversation.
No durable storage, issue tracker, remote agent transport, or DAG scheduler is connected.

## Check the experiment

```sh
go -C experiments/go-tui test ./...
go -C experiments/go-tui test -race ./...
go -C experiments/go-tui vet ./...
```

## Follow the code

- `main.go` validates the display directory and starts Bubble Tea.
- `model.go` owns input, transcript state, cancellation, and resizing.
- `demo.go` defines the fixed event sequence and schedules one timer at a time.
- `context.go` reads Git context and cycles demo settings.
- `view.go` renders the conversation and the activity pane.
- `workspace.go` owns workspace navigation, current-state projections, and rendering.
- `workspace_samples.go` contains preview-only fixture rows.
- `model_test.go` checks interactions through Bubble Tea messages.
- `workspace_test.go` checks navigation, state preservation, sample actions, and layout.

Only `Update` changes application state.
Each timed event carries a run ID and a step number.
`Update` rejects an event after cancellation or when its step is out of order.
The timers capture event values and never write to the model.
The demo has no producer goroutine, queue, or background service.

This experiment tests the interface and its code structure.
It does not establish real agent performance or parallel execution.
A live harness integration remains a separate decision.

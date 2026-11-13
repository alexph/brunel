from urllib.parse import urlsplit

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive, var
from textual.screen import Screen
from textual.widgets import Collapsible, Footer, Header, Markdown, Static, TextArea

from brunel.tui.conversation import ConversationStore, TranscriptEntry
from brunel.tui.stores import StoreChange, StoreKey, StoreRouter


class TextInput(TextArea):
    DEFAULT_CSS = """
    TextInput {
        height: auto; min-height: 3; max-height: 10;
        border: round $primary; padding: 0 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(
            placeholder="Write a message… (runtime not connected)", **kwargs
        )


class Composer(Vertical):
    DEFAULT_CSS = """
    Composer { dock: bottom; height: auto; padding: 0 1; }
    """

    def compose(self) -> ComposeResult:
        yield TextInput()


class ChatMessage(Vertical):
    DEFAULT_CSS = """
    ChatMessage { height: auto; margin: 0 1 1 1; }
    ChatMessage > Static { height: auto; color: $text-muted; }
    ChatMessage Markdown { height: auto; margin: 0; padding: 0; }
    ChatMessage Collapsible { padding: 0; }
    """
    entry: reactive[TranscriptEntry | None] = reactive(None)

    def __init__(self, entry: TranscriptEntry):
        super().__init__()
        self.initial_entry = entry

    def compose(self) -> ComposeResult:
        yield Static("", markup=False, classes="message-label")
        entry = self.initial_entry
        if entry.role in {"call", "tool", "reasoning", "activity"}:
            with Collapsible(
                title=entry.name or entry.activity_type or entry.role.title()
            ):
                yield Static("", markup=False, classes="message-content")
        else:
            yield Markdown("", open_links=False, classes="message-content")

    def on_mount(self) -> None:
        self.entry = self.initial_entry

    def watch_entry(self, entry: TranscriptEntry | None) -> None:
        if entry is None:
            return
        name = entry.name or entry.role.title()
        attribution = f" · {entry.owner}" if entry.owner else ""
        tool = f" · {entry.tool_call_id}" if entry.tool_call_id else ""
        self.query_one(".message-label", Static).update(
            f"{name}{attribution}{tool} · {entry.status}"
        )
        body = self.query_one(".message-content")
        body.update(entry.content)

    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        event.stop()
        try:
            target = urlsplit(event.href)
        except ValueError:
            return
        if target.scheme in {"http", "https"} and target.hostname:
            self.app.open_url(event.href)


class Transcript(VerticalScroll):
    DEFAULT_CSS = """
    Transcript { height: 1fr; }
    Transcript > #chat-empty { color: $text-muted; margin: 1 2; height: auto; }
    """

    def __init__(self):
        super().__init__()
        self.messages: dict[str, ChatMessage] = {}

    def compose(self) -> ComposeResult:
        yield Static(
            "No messages yet. The agent runtime is not connected.", id="chat-empty"
        )

    async def reconcile(self, store: ConversationStore, change: StoreChange) -> None:
        follow = self.is_vertical_scroll_end
        self.query_one("#chat-empty").display = not store.entries
        if change.structure:
            for key in tuple(self.messages):
                if key not in store.entries:
                    await self.messages.pop(key).remove()
        for key in change.updated:
            entry = store.entries.get(key)
            if entry is None:
                continue
            if key not in self.messages:
                widget = ChatMessage(entry)
                self.messages[key] = widget
                await self.mount(widget)
            else:
                widget = self.messages[key]
                if widget.entry.role != entry.role:
                    await widget.remove()
                    widget = ChatMessage(entry)
                    self.messages[key] = widget
                    await self.mount(widget)
                widget.entry = entry
        if change.structure:
            previous = self.query_one("#chat-empty")
            for key in store.entries:
                widget = self.messages[key]
                self.move_child(widget, after=previous)
                previous = widget
        if follow:
            self.scroll_end(animate=False)


class ChatScreen(Screen):
    DEFAULT_CSS = """
    ChatScreen #chat-body { height: 1fr; }
    ChatScreen #chat-status { height: auto; padding: 0 1; color: $text-muted; }
    """
    revision = var(0)

    def __init__(self, *, store: ConversationStore, router: StoreRouter, key: StoreKey):
        super().__init__()
        self.store = store
        self.router = router
        self.store_key = key
        self._pending = StoreChange()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Vertical(id="chat-body"):
            yield Composer()
            yield Static("", id="chat-status", markup=False)
            yield Transcript()

    async def on_mount(self) -> None:
        await self.query_one(Transcript).reconcile(
            self.store, StoreChange(updated=tuple(self.store.entries), structure=True)
        )
        self.update_status()
        self.query_one(TextInput).focus()

    def apply_event(self, event: object) -> None:
        change = self.router.dispatch(self.store_key, event)
        self.receive_change(change)

    def receive_change(self, change: StoreChange) -> None:
        self._pending = StoreChange(
            updated=tuple(dict.fromkeys((*self._pending.updated, *change.updated))),
            structure=self._pending.structure or change.structure,
            status=self._pending.status or change.status,
        )
        self.revision += 1

    async def watch_revision(self) -> None:
        if not self.is_mounted:
            return
        change, self._pending = self._pending, StoreChange()
        await self.query_one(Transcript).reconcile(self.store, change)
        if change.status:
            self.update_status()

    def update_status(self) -> None:
        steps = ", ".join(
            name for _, name in sorted(self.store.steps, key=lambda step: step[1])
        )
        parts = [self.store.status, steps, self.store.notice]
        self.query_one("#chat-status", Static).update(
            " · ".join(part for part in parts if part)
        )

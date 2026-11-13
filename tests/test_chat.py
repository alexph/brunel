import asyncio

import ag_ui.core as ag
from textual.app import App
from textual.widgets import Collapsible, Footer, Header, Markdown, Static

from brunel.tui.chat import ChatMessage, ChatScreen, Composer, TextInput, Transcript
from brunel.tui.conversation import ConversationStore
from brunel.tui.stores import StoreKey, StoreRouter


def chat_app():
    store = ConversationStore("thread")
    router = StoreRouter()
    key = StoreKey("conversation", "thread")
    router.register(key, store)
    screen = ChatScreen(store=store, router=router, key=key)

    class ChatApp(App):
        def on_mount(self):
            self.push_screen(screen)

    return ChatApp(), screen


def test_docked_composer_grows_to_cap_and_retains_focus():
    async def check():
        app, screen = chat_app()
        async with app.run_test(size=(90, 35)) as pilot:
            await pilot.pause()
            editor = screen.query_one(TextInput)
            composer = screen.query_one(Composer)
            transcript = screen.query_one(Transcript)
            initial_height = editor.size.height
            editor.load_text("\n".join(f"Line {n}" for n in range(5)))
            await pilot.pause()
            assert editor.size.height > initial_height
            editor.load_text("\n".join(f"Line {n}" for n in range(30)))
            await pilot.pause()
            assert editor.outer_size.height <= 10
            assert transcript.region.bottom <= composer.region.y
            assert composer.region.bottom <= screen.query_one(Footer).region.y
            assert (
                screen.query_one(Header).region.bottom
                <= screen.query_one("#chat-status").region.y
            )
            assert app.focused is editor
            assert editor.text.endswith("Line 29")
            editor.load_text("")
            await pilot.pause()
            assert editor.size.height == initial_height

    asyncio.run(check())


def test_targeted_updates_keep_widget_identity_draft_and_collapsed_state():
    async def check():
        app, screen = chat_app()
        async with app.run_test(size=(90, 35)) as pilot:
            await pilot.pause()
            editor = screen.query_one(TextInput)
            editor.load_text("unsent draft")
            screen.apply_event(ag.RunStartedEvent(thread_id="thread", run_id="run"))
            screen.apply_event(ag.TextMessageStartEvent(message_id="message"))
            screen.apply_event(
                ag.TextMessageContentEvent(message_id="message", delta="Hello")
            )
            await pilot.pause()
            transcript = screen.query_one(Transcript)
            widget = transcript.messages["message"]
            assert widget.query_one(Markdown).source == "Hello"
            assert "Assistant" in str(
                widget.query_one(".message-label", Static).content
            )
            screen.apply_event(
                ag.TextMessageContentEvent(message_id="message", delta=" world")
            )
            await pilot.pause()
            assert transcript.messages["message"] is widget
            assert widget.entry.content == "Hello world"
            assert widget.query_one(Markdown).source == "Hello world"
            assert len(screen.query(ChatMessage)) == 1
            assert editor.text == "unsent draft"
            assert app.focused is editor
            screen.apply_event(ag.TextMessageEndEvent(message_id="message"))
            screen.apply_event(ag.RunFinishedEvent(thread_id="thread", run_id="run"))
            await pilot.pause()
            assert widget.entry.status == "complete"

            screen.apply_event(
                ag.ToolCallStartEvent(tool_call_id="tool", tool_call_name="read")
            )
            screen.apply_event(ag.ToolCallArgsEvent(tool_call_id="tool", delta="{}"))
            await pilot.pause()
            details = transcript.messages["tool:tool"].query_one(Collapsible)
            details.collapsed = False
            screen.apply_event(ag.ToolCallEndEvent(tool_call_id="tool"))
            await pilot.pause()
            assert not details.collapsed

    asyncio.run(check())


def test_links_only_open_web_urls():
    async def check():
        app, screen = chat_app()
        opened = []
        app.open_url = opened.append
        async with app.run_test() as pilot:
            screen.apply_event(ag.TextMessageChunkEvent(message_id="m", delta="Links"))
            await pilot.pause()
            widget = screen.query_one(ChatMessage)
            markdown = widget.query_one(Markdown)
            for href in [
                "file:///etc/passwd",
                "javascript:alert(1)",
                "https://example.com",
            ]:
                widget.on_markdown_link_clicked(Markdown.LinkClicked(markdown, href))
            assert opened == ["https://example.com"]

    asyncio.run(check())


def test_stream_does_not_pull_reader_from_earlier_messages():
    async def check():
        app, screen = chat_app()
        async with app.run_test(size=(70, 20)) as pilot:
            for number in range(15):
                screen.apply_event(
                    ag.TextMessageChunkEvent(
                        message_id=str(number), delta="A message\n\nMore content"
                    )
                )
            await pilot.pause()
            transcript = screen.query_one(Transcript)
            transcript.scroll_home(animate=False)
            await pilot.pause()
            screen.apply_event(
                ag.TextMessageChunkEvent(message_id="last", delta="New content")
            )
            await pilot.pause()
            assert transcript.scroll_y == 0
            assert transcript.messages["14"].entry.status == "complete"

    asyncio.run(check())

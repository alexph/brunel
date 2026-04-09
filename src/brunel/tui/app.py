from time import monotonic

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.widgets import TextArea


EXIT_CONFIRMATION_WINDOW_SECONDS = 0.75
_last_ctrl_c_at = 0.0

history = TextArea(
    scrollbar=True,
    wrap_lines=True,
    read_only=True,
    focusable=False,
)


prompt_input = TextArea(
    height=1,
    prompt="brunel> ",
    multiline=True,
    wrap_lines=True,
)

root_container = HSplit([history, prompt_input])

kb = KeyBindings()


@kb.add("enter")
def handle_enter(event):
    text = prompt_input.text.strip()
    if not text:
        prompt_input.buffer.text = ""
        return

    entry = f"brunel> {text}"
    history.buffer.set_document(
        history.buffer.document.insert_after(f"\n{entry}" if history.text else entry),
        bypass_readonly=True,
    )
    prompt_input.buffer.text = ""


@kb.add("c-c")
def handle_ctrl_c(event):
    global _last_ctrl_c_at

    now = monotonic()
    if now - _last_ctrl_c_at <= EXIT_CONFIRMATION_WINDOW_SECONDS:
        event.app.exit()
        return

    _last_ctrl_c_at = now
    history.buffer.set_document(
        history.buffer.document.insert_after(
            "\nPress Ctrl-C again to exit."
            if history.text
            else "Press Ctrl-C again to exit."
        ),
        bypass_readonly=True,
    )


def tui_app():
    layout = Layout(root_container, focused_element=prompt_input)
    app = Application(layout=layout, key_bindings=kb, full_screen=True)
    app.run()

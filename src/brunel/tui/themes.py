from textual.theme import Theme

arctic_theme = Theme(
    name="arctic",
    primary="#88C0D0",
    secondary="#81A1C1",
    accent="#B48EAD",
    foreground="#D8DEE9",
    background="#2E3440",
    success="#A3BE8C",
    warning="#EBCB8B",
    error="#BF616A",
    surface="#3B4252",
    panel="#434C5E",
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#88C0D0",
        "input-selection-background": "#81a1c1 35%",
    },
)

blueprint_theme = Theme(
    name="blueprint",
    primary="#F4F8FF",
    secondary="#A9D4FF",
    accent="#D5EAFF",
    foreground="#F4F8FF",
    background="#003366",
    success="#A8E6CF",
    warning="#FFE4A3",
    error="#FFB3B3",
    surface="#073F73",
    panel="#104B80",
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#F4F8FF",
        "input-selection-background": "#A9D4FF 35%",
    },
)

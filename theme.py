import tkinter.font as tkfont

# Graphite neutrals
BG = "#111113"
SIDEBAR = "#16161a"
SURFACE = "#18181c"
FIELD = "#1b1b1f"
RAISED = "#232328"
HOVER = "#1f1f24"
CODE_BG = "#0c0c0e"
HAIRLINE = "#2a2a2f"

# Text roles
TEXT = "#ececef"
TEXT_2 = "#a3a3ad"
MUTED = "#7e7e88"

# The one accent: highlighter amber
ACCENT = "#f2b441"
ACCENT_HOVER = "#f6c357"
ACCENT_DISABLED = "#3a3220"
ON_ACCENT = "#1a1406"

# The highlighter mark, pre-mixed for each background it sits on
MARK_TEXT = "#ffe2a3"
MARK_ON_CODE = "#43341a"
MARK_ON_RAISED = "#51432e"

MARK_ON_SURFACE = "#483a24"

# Explanation card extras
STRIP = "#151519"
BUBBLE = "#26262c"


def pick_family(candidates):
    installed = set(tkfont.families())
    for name in candidates:
        if name in installed:
            return name
    return candidates[-1]


def font_families():
    ui = pick_family(["Segoe UI Variable Text", "Segoe UI", "Helvetica"])
    mono = pick_family(["Cascadia Mono", "Consolas", "Courier New"])
    return ui, mono
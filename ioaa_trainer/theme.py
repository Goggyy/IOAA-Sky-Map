"""Application-wide visual themes, including red-only observing mode."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

NIGHT_BACKGROUND = "#050000"
NIGHT_SURFACE = "#0d0000"
NIGHT_FIELD = "#160000"
NIGHT_BORDER = "#5a0000"
NIGHT_TEXT = "#ff0000"
NIGHT_MUTED = "#a80000"
NIGHT_ACTIVE = "#360000"
NIGHT_SELECTED = "#700000"


def night_mode_enabled(widget: tk.Misc) -> bool:
    """Return the current process-wide observing-theme state."""
    try:
        root = widget._root()
    except (AttributeError, tk.TclError):
        root = widget.winfo_toplevel()
    return bool(getattr(root, "_ioaa_night_mode", False))


def apply_night_theme(window: tk.Misc, enabled: bool) -> None:
    """Apply or remove the red-only theme for every window in this Tk process."""
    root = window._root()
    style = ttk.Style(root)
    if not hasattr(root, "_ioaa_day_theme"):
        root._ioaa_day_theme = style.theme_use()

    root._ioaa_night_mode = bool(enabled)
    if enabled:
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        _configure_night_ttk(style)
        root.configure(background=NIGHT_BACKGROUND)
        root.option_add("*Background", NIGHT_BACKGROUND)
        root.option_add("*Foreground", NIGHT_TEXT)
        root.option_add("*insertBackground", NIGHT_TEXT)
        root.option_add("*selectBackground", NIGHT_SELECTED)
        root.option_add("*selectForeground", NIGHT_TEXT)
    else:
        try:
            root.option_clear()
        except tk.TclError:
            pass
        try:
            style.theme_use(root._ioaa_day_theme)
        except tk.TclError:
            pass
        try:
            root.configure(background=style.lookup("TFrame", "background"))
        except tk.TclError:
            pass

    refresh_widget_theme(root)


def _configure_night_ttk(style: ttk.Style) -> None:
    common = {
        "background": NIGHT_BACKGROUND,
        "foreground": NIGHT_TEXT,
        "bordercolor": NIGHT_BORDER,
        "lightcolor": NIGHT_BORDER,
        "darkcolor": NIGHT_BORDER,
        "troughcolor": NIGHT_SURFACE,
        "fieldbackground": NIGHT_FIELD,
        "selectbackground": NIGHT_SELECTED,
        "selectforeground": NIGHT_TEXT,
        "insertcolor": NIGHT_TEXT,
        "arrowcolor": NIGHT_TEXT,
    }
    style.configure(".", **common)
    style.configure("TFrame", background=NIGHT_BACKGROUND)
    style.configure("TLabel", background=NIGHT_BACKGROUND, foreground=NIGHT_TEXT)
    style.configure("TLabelframe", background=NIGHT_BACKGROUND, bordercolor=NIGHT_BORDER)
    style.configure(
        "TLabelframe.Label",
        background=NIGHT_BACKGROUND,
        foreground=NIGHT_TEXT,
    )
    style.configure(
        "TButton",
        background=NIGHT_SURFACE,
        foreground=NIGHT_TEXT,
        bordercolor=NIGHT_BORDER,
        focuscolor=NIGHT_BORDER,
    )
    style.map(
        "TButton",
        background=[("pressed", NIGHT_SELECTED), ("active", NIGHT_ACTIVE)],
        foreground=[("disabled", NIGHT_MUTED), ("!disabled", NIGHT_TEXT)],
        bordercolor=[("focus", NIGHT_TEXT), ("!focus", NIGHT_BORDER)],
    )
    style.configure(
        "TEntry",
        fieldbackground=NIGHT_FIELD,
        foreground=NIGHT_TEXT,
        insertcolor=NIGHT_TEXT,
        bordercolor=NIGHT_BORDER,
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", NIGHT_SURFACE), ("readonly", NIGHT_FIELD)],
        foreground=[("disabled", NIGHT_MUTED), ("readonly", NIGHT_TEXT)],
    )
    style.configure(
        "TCombobox",
        fieldbackground=NIGHT_FIELD,
        background=NIGHT_SURFACE,
        foreground=NIGHT_TEXT,
        arrowcolor=NIGHT_TEXT,
        bordercolor=NIGHT_BORDER,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", NIGHT_FIELD), ("disabled", NIGHT_SURFACE)],
        foreground=[("readonly", NIGHT_TEXT), ("disabled", NIGHT_MUTED)],
        selectbackground=[("readonly", NIGHT_FIELD)],
        selectforeground=[("readonly", NIGHT_TEXT)],
    )
    style.configure(
        "TRadiobutton",
        background=NIGHT_BACKGROUND,
        foreground=NIGHT_TEXT,
        indicatorcolor=NIGHT_FIELD,
    )
    style.map(
        "TRadiobutton",
        background=[("active", NIGHT_BACKGROUND)],
        foreground=[("disabled", NIGHT_MUTED), ("!disabled", NIGHT_TEXT)],
        indicatorcolor=[("selected", NIGHT_TEXT), ("!selected", NIGHT_FIELD)],
    )
    style.configure(
        "TNotebook",
        background=NIGHT_BACKGROUND,
        bordercolor=NIGHT_BORDER,
        tabmargins=(2, 2, 2, 0),
    )
    style.configure(
        "TNotebook.Tab",
        background=NIGHT_SURFACE,
        foreground=NIGHT_MUTED,
        bordercolor=NIGHT_BORDER,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", NIGHT_SELECTED), ("active", NIGHT_ACTIVE)],
        foreground=[("selected", NIGHT_TEXT), ("active", NIGHT_TEXT)],
    )
    style.configure(
        "TScale",
        background=NIGHT_BACKGROUND,
        troughcolor=NIGHT_SURFACE,
        bordercolor=NIGHT_BORDER,
    )
    style.configure(
        "TScrollbar",
        background=NIGHT_SURFACE,
        troughcolor=NIGHT_BACKGROUND,
        bordercolor=NIGHT_BORDER,
        arrowcolor=NIGHT_TEXT,
    )
    style.map("TScrollbar", background=[("active", NIGHT_ACTIVE)])
    style.configure("TSeparator", background=NIGHT_BORDER)


def refresh_widget_theme(widget: tk.Misc) -> None:
    """Refresh custom Tk widgets after the process-wide theme changes."""
    enabled = night_mode_enabled(widget)
    refresh = getattr(widget, "refresh_theme", None)
    if callable(refresh):
        refresh()
    elif enabled:
        try:
            if isinstance(widget, (tk.Tk, tk.Toplevel)):
                widget.configure(background=NIGHT_BACKGROUND)
            elif isinstance(widget, tk.Text):
                widget.configure(
                    background=NIGHT_FIELD,
                    foreground=NIGHT_TEXT,
                    insertbackground=NIGHT_TEXT,
                    selectbackground=NIGHT_SELECTED,
                    selectforeground=NIGHT_TEXT,
                )
            elif isinstance(widget, (tk.Entry, tk.Listbox, tk.Spinbox)):
                widget.configure(
                    background=NIGHT_FIELD,
                    foreground=NIGHT_TEXT,
                    insertbackground=NIGHT_TEXT,
                    selectbackground=NIGHT_SELECTED,
                    selectforeground=NIGHT_TEXT,
                )
            elif isinstance(widget, tk.Canvas):
                widget.configure(background=NIGHT_BACKGROUND)
            elif isinstance(widget, tk.Menu):
                widget.configure(
                    background=NIGHT_SURFACE,
                    foreground=NIGHT_TEXT,
                    activebackground=NIGHT_SELECTED,
                    activeforeground=NIGHT_TEXT,
                )
        except tk.TclError:
            pass

    try:
        children = widget.winfo_children()
    except tk.TclError:
        return
    for child in children:
        refresh_widget_theme(child)

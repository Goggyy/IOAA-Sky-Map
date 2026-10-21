"""Small reusable Tkinter widgets used throughout the application."""

from __future__ import annotations

import math
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import scrolledtext, ttk
from typing import Callable

from .theme import (
    NIGHT_ACTIVE,
    NIGHT_BACKGROUND,
    NIGHT_BORDER,
    NIGHT_FIELD,
    NIGHT_MUTED,
    NIGHT_SELECTED,
    NIGHT_TEXT,
    night_mode_enabled,
)


def _ttk_background(widget: tk.Misc) -> str:
    """Return a canvas-safe colour close to the surrounding ttk background."""
    style = ttk.Style(widget)
    candidates = []
    try:
        candidates.append(style.lookup(widget.winfo_class(), "background"))
    except tk.TclError:
        pass
    candidates.extend(
        [
            style.lookup("TFrame", "background"),
            style.lookup("TLabel", "background"),
        ]
    )
    try:
        candidates.append(widget.winfo_toplevel().cget("background"))
    except tk.TclError:
        pass
    for colour in candidates:
        if colour:
            return str(colour)
    return "#ececec"


class ToggleSwitch(ttk.Label):
    """A compact Boolean switch rendered without an opaque container.

    The entire control is one themed ``ttk.Label`` with a transparent
    ``PhotoImage``.  This avoids the pale rectangular background that macOS
    can paint around embedded Tk frames and canvases while retaining a native
    label background in every ttk theme.
    """

    TRACK_WIDTH = 40
    TRACK_HEIGHT = 22
    KNOB_DIAMETER = 16

    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        variable: tk.BooleanVar,
        command: Callable[[], None] | None = None,
        wraplength: int | None = None,
    ) -> None:
        self.variable = variable
        self.command = command
        self._enabled = True
        self._images = self._build_images(master)

        options: dict[str, object] = {
            "text": text,
            "image": self._images["on" if variable.get() else "off"],
            "compound": "left",
            "anchor": "w",
            "justify": "left",
            "cursor": "hand2",
            "takefocus": True,
            "padding": 0,
        }
        if wraplength is not None:
            options["wraplength"] = wraplength
        super().__init__(master, **options)

        self.bind("<Button-1>", self._toggle_from_event)
        self.bind("<space>", self._toggle_from_event)
        self.bind("<Return>", self._toggle_from_event)
        self._trace_id = self.variable.trace_add("write", self._variable_changed)
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._draw()

    def _build_images(self, master: tk.Misc) -> dict[str, tk.PhotoImage]:
        if night_mode_enabled(master):
            return {
                "off": self._make_switch_image(NIGHT_BORDER, NIGHT_MUTED, master),
                "on": self._make_switch_image(NIGHT_TEXT, NIGHT_BACKGROUND, master, on=True),
                "disabled": self._make_switch_image(NIGHT_FIELD, NIGHT_MUTED, master),
            }
        return {
            "off": self._make_switch_image("#8e99a5", "#ffffff", master),
            "on": self._make_switch_image("#3478b8", "#ffffff", master, on=True),
            "disabled": self._make_switch_image("#c8cdd3", "#eef0f2", master),
        }

    def refresh_theme(self) -> None:
        """Rebuild switch artwork for the active application theme."""
        self._images = self._build_images(self)
        self._draw()

    @classmethod
    def _make_switch_image(
        cls,
        track_colour: str,
        knob_colour: str,
        master: tk.Misc,
        *,
        on: bool = False,
    ) -> tk.PhotoImage:
        """Create a rounded switch with transparent pixels outside the track."""
        image = tk.PhotoImage(
            master=master,
            width=cls.TRACK_WIDTH,
            height=cls.TRACK_HEIGHT,
        )
        width = cls.TRACK_WIDTH
        height = cls.TRACK_HEIGHT
        radius = height / 2.0

        # Draw the capsule a scanline at a time. Untouched pixels remain fully
        # transparent, so the active ttk theme shows through around the switch.
        for y in range(height):
            dy = abs((y + 0.5) - radius)
            inset = radius - math.sqrt(max(0.0, radius * radius - dy * dy))
            left = max(0, int(math.floor(inset)))
            right = min(width, int(math.ceil(width - inset)))
            if right > left:
                image.put(track_colour, to=(left, y, right, y + 1))

        knob_radius = cls.KNOB_DIAMETER / 2.0
        knob_margin = (height - cls.KNOB_DIAMETER) / 2.0
        knob_center_x = (
            width - knob_margin - knob_radius
            if on
            else knob_margin + knob_radius
        )
        knob_center_y = radius
        for y in range(height):
            dy = abs((y + 0.5) - knob_center_y)
            if dy >= knob_radius:
                continue
            half_width = math.sqrt(max(0.0, knob_radius * knob_radius - dy * dy))
            left = max(0, int(math.floor(knob_center_x - half_width)))
            right = min(width, int(math.ceil(knob_center_x + half_width)))
            if right > left:
                image.put(knob_colour, to=(left, y, right, y + 1))

        return image

    def _toggle_from_event(self, _event=None) -> str:
        if not self._enabled:
            return "break"
        self.variable.set(not bool(self.variable.get()))
        if self.command is not None:
            self.command()
        self.focus_set()
        return "break"

    def _variable_changed(self, *_args) -> None:
        self._draw()

    def _draw(self) -> None:
        key = "disabled" if not self._enabled else ("on" if self.variable.get() else "off")
        self.configure(image=self._images[key])

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable user interaction with the switch."""
        self._enabled = bool(enabled)
        if self._enabled:
            self.state(["!disabled"])
            self.configure(cursor="hand2")
        else:
            self.state(["disabled"])
            self.configure(cursor="arrow")
        self._draw()

    def _on_destroy(self, event) -> None:
        if event.widget is self:
            try:
                self.variable.trace_remove("write", self._trace_id)
            except (tk.TclError, ValueError):
                pass


class VerticalScrolledFrame(ttk.Frame):
    """A vertically scrollable ttk content frame with eased wheel scrolling."""

    def __init__(self, master: tk.Misc, *, padding: int = 0) -> None:
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        background = _ttk_background(master)
        self.canvas = tk.Canvas(
            self,
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
            background=background,
        )
        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self._scrollbar_command,
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.content = ttk.Frame(self.canvas, padding=padding)
        self._window_id = self.canvas.create_window(
            (0, 0),
            window=self.content,
            anchor="nw",
        )
        self.content.bind("<Configure>", self._content_configured)
        self.canvas.bind("<Configure>", self._canvas_configured)
        self.bind("<Enter>", self._bind_mousewheel)
        self.bind("<Leave>", self._unbind_mousewheel)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.content.bind("<Enter>", self._bind_mousewheel)

        self._scroll_target: float | None = None
        self._scroll_animation: str | None = None
        self._scrollbar_visible = True
        self.after_idle(self._update_scrollbar_visibility)

    def refresh_theme(self) -> None:
        colour = NIGHT_BACKGROUND if night_mode_enabled(self) else _ttk_background(self)
        try:
            self.canvas.configure(background=colour)
        except tk.TclError:
            pass

    def _content_configured(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.after_idle(self._update_scrollbar_visibility)

    def _canvas_configured(self, event) -> None:
        self.canvas.itemconfigure(self._window_id, width=event.width)
        self.after_idle(self._update_scrollbar_visibility)

    def _update_scrollbar_visibility(self) -> None:
        """Show the scrollbar only when the content is taller than the viewport."""
        try:
            bbox = self.canvas.bbox("all")
            viewport_height = self.canvas.winfo_height()
        except tk.TclError:
            return
        content_height = 0 if bbox is None else max(0, bbox[3] - bbox[1])
        needs_scrollbar = content_height > viewport_height + 1
        if needs_scrollbar and not self._scrollbar_visible:
            self.scrollbar.grid()
            self._scrollbar_visible = True
        elif not needs_scrollbar and self._scrollbar_visible:
            self.scrollbar.grid_remove()
            self._scrollbar_visible = False

    def _scrollbar_command(self, *args) -> None:
        self._cancel_scroll_animation()
        self.canvas.yview(*args)

    def _bind_mousewheel(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_linux_wheel)
        self.canvas.bind_all("<Button-5>", self._on_linux_wheel)

    def _unbind_mousewheel(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event) -> str:
        if sys.platform == "darwin":
            # macOS trackpads provide small, frequent deltas. Preserve that
            # granularity rather than converting every event into a full row.
            pixels = -float(event.delta) * 7.0
        else:
            pixels = -float(event.delta) / 120.0 * 48.0
        self._queue_scroll_pixels(pixels)
        return "break"

    def _on_linux_wheel(self, event) -> str:
        self._queue_scroll_pixels(-48.0 if event.num == 4 else 48.0)
        return "break"

    def _queue_scroll_pixels(self, pixels: float) -> None:
        bbox = self.canvas.bbox("all")
        if bbox is None:
            return
        total_height = max(1.0, float(bbox[3] - bbox[1]))
        viewport_height = max(1.0, float(self.canvas.winfo_height()))
        max_first = max(0.0, 1.0 - viewport_height / total_height)
        current = float(self.canvas.yview()[0])
        if self._scroll_target is None:
            self._scroll_target = current
        self._scroll_target = min(
            max_first,
            max(0.0, self._scroll_target + pixels / total_height),
        )
        if self._scroll_animation is None:
            self._animate_scroll()

    def _animate_scroll(self) -> None:
        if self._scroll_target is None or not self.winfo_exists():
            self._scroll_animation = None
            return
        current = float(self.canvas.yview()[0])
        distance = self._scroll_target - current
        if abs(distance) < 0.00015:
            self.canvas.yview_moveto(self._scroll_target)
            self._scroll_target = None
            self._scroll_animation = None
            return
        self.canvas.yview_moveto(current + distance * 0.34)
        self._scroll_animation = self.after(16, self._animate_scroll)

    def _cancel_scroll_animation(self) -> None:
        if self._scroll_animation is not None:
            try:
                self.after_cancel(self._scroll_animation)
            except tk.TclError:
                pass
        self._scroll_animation = None
        self._scroll_target = None


class SmoothScrolledText(scrolledtext.ScrolledText):
    """ScrolledText with eased mouse-wheel and trackpad movement."""

    def __init__(self, master: tk.Misc, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._scroll_target: float | None = None
        self._scroll_animation: str | None = None
        self.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind("<Button-4>", self._on_linux_wheel, add="+")
        self.bind("<Button-5>", self._on_linux_wheel, add="+")

    def refresh_theme(self) -> None:
        try:
            if night_mode_enabled(self):
                self.configure(
                    background=NIGHT_FIELD,
                    foreground=NIGHT_TEXT,
                    insertbackground=NIGHT_TEXT,
                    selectbackground=NIGHT_SELECTED,
                    selectforeground=NIGHT_TEXT,
                )
            else:
                self.configure(
                    background="#ffffff",
                    foreground="#000000",
                    insertbackground="#000000",
                    selectbackground="#4a6984",
                    selectforeground="#ffffff",
                )
        except tk.TclError:
            pass

    def _on_mousewheel(self, event) -> str:
        if sys.platform == "darwin":
            pixels = -float(event.delta) * 7.0
        else:
            pixels = -float(event.delta) / 120.0 * 48.0
        self._queue_scroll_pixels(pixels)
        return "break"

    def _on_linux_wheel(self, event) -> str:
        self._queue_scroll_pixels(-48.0 if event.num == 4 else 48.0)
        return "break"

    def _queue_scroll_pixels(self, pixels: float) -> None:
        try:
            font = tkfont.nametofont(str(self.cget("font")))
            line_height = max(1, int(font.metrics("linespace")))
        except tk.TclError:
            line_height = 16
        line_count = max(1, int(self.index("end-1c").split(".")[0]))
        estimated_height = max(float(self.winfo_height()), line_count * line_height)
        first, last = self.yview()
        max_first = max(0.0, 1.0 - (last - first))
        if self._scroll_target is None:
            self._scroll_target = float(first)
        self._scroll_target = min(
            max_first,
            max(0.0, self._scroll_target + pixels / estimated_height),
        )
        if self._scroll_animation is None:
            self._animate_scroll()

    def _animate_scroll(self) -> None:
        if self._scroll_target is None or not self.winfo_exists():
            self._scroll_animation = None
            return
        current = float(self.yview()[0])
        distance = self._scroll_target - current
        if abs(distance) < 0.00015:
            self.yview_moveto(self._scroll_target)
            self._scroll_target = None
            self._scroll_animation = None
            return
        self.yview_moveto(current + distance * 0.34)
        self._scroll_animation = self.after(16, self._animate_scroll)


class CelestialSphereSelector(ttk.Frame):
    """Interactive equirectangular celestial-sphere zenith selector.

    Drag anywhere on the projection to choose the zenith RA and Dec. The
    spherical-cap boundary shows the current sky-map coverage, including the
    wrap across 0h right ascension.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        ra_variable: tk.DoubleVar,
        dec_variable: tk.DoubleVar,
        sky_radius_variable: tk.DoubleVar,
        command: Callable[[], None] | None = None,
        release_command: Callable[[], None] | None = None,
        height: int = 230,
    ) -> None:
        super().__init__(master)
        self.ra_variable = ra_variable
        self.dec_variable = dec_variable
        self.sky_radius_variable = sky_radius_variable
        self.command = command
        self.release_command = release_command
        self._enabled = True
        self._dragging = False
        self._margin_left = 31.0
        self._margin_right = 12.0
        self._margin_top = 16.0
        self._margin_bottom = 28.0

        self.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self,
            height=height,
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
            background="#0b1421",
            cursor="crosshair",
            takefocus=1,
        )
        self.canvas.grid(row=0, column=0, sticky="ew")
        self.canvas.bind("<Configure>", self._redraw)
        self.canvas.bind("<Button-1>", self._button_press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._button_release)
        self.canvas.bind("<Left>", lambda event: self._nudge(-0.25, 0.0))
        self.canvas.bind("<Right>", lambda event: self._nudge(0.25, 0.0))
        self.canvas.bind("<Up>", lambda event: self._nudge(0.0, 1.0))
        self.canvas.bind("<Down>", lambda event: self._nudge(0.0, -1.0))

        self._traces = (
            (self.ra_variable, self.ra_variable.trace_add("write", self._redraw)),
            (self.dec_variable, self.dec_variable.trace_add("write", self._redraw)),
            (
                self.sky_radius_variable,
                self.sky_radius_variable.trace_add("write", self._redraw),
            ),
        )
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.after_idle(self._redraw)

    def refresh_theme(self) -> None:
        try:
            self.canvas.configure(
                background=NIGHT_BACKGROUND if night_mode_enabled(self) else "#0b1421"
            )
        except tk.TclError:
            pass
        self._redraw()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self.canvas.configure(cursor="crosshair" if self._enabled else "arrow")
        self._redraw()

    def _plot_box(self) -> tuple[float, float, float, float]:
        width = max(240.0, float(self.canvas.winfo_width()))
        height = max(150.0, float(self.canvas.winfo_height()))
        return (
            self._margin_left,
            self._margin_top,
            width - self._margin_right,
            height - self._margin_bottom,
        )

    def _project(self, ra_hours: float, dec_degrees: float) -> tuple[float, float]:
        x0, y0, x1, y1 = self._plot_box()
        # Standard sky-map orientation: RA increases toward the left.
        x = x0 + ((24.0 - (ra_hours % 24.0)) / 24.0) * (x1 - x0)
        y = y0 + ((90.0 - dec_degrees) / 180.0) * (y1 - y0)
        return x, y

    def _unproject(self, x: float, y: float) -> tuple[float, float]:
        x0, y0, x1, y1 = self._plot_box()
        x = min(x1, max(x0, x))
        y = min(y1, max(y0, y))
        ra = (24.0 - (x - x0) / max(1.0, x1 - x0) * 24.0) % 24.0
        dec = 90.0 - (y - y0) / max(1.0, y1 - y0) * 180.0
        return ra, min(90.0, max(-90.0, dec))

    def _button_press(self, event) -> str:
        if not self._enabled:
            return "break"
        self.canvas.focus_set()
        self._dragging = True
        self._set_from_pointer(event.x, event.y, notify=True)
        return "break"

    def _drag(self, event) -> str:
        if self._enabled and self._dragging:
            self._set_from_pointer(event.x, event.y, notify=True)
        return "break"

    def _button_release(self, event) -> str:
        if self._enabled and self._dragging:
            self._set_from_pointer(event.x, event.y, notify=False)
            self._dragging = False
            if self.release_command is not None:
                self.release_command()
        return "break"

    def _set_from_pointer(self, x: float, y: float, *, notify: bool) -> None:
        ra, dec = self._unproject(x, y)
        self.ra_variable.set(ra)
        self.dec_variable.set(dec)
        if notify and self.command is not None:
            self.command()

    def _nudge(self, delta_ra: float, delta_dec: float) -> str:
        if not self._enabled:
            return "break"
        self.ra_variable.set((float(self.ra_variable.get()) + delta_ra) % 24.0)
        self.dec_variable.set(
            min(90.0, max(-90.0, float(self.dec_variable.get()) + delta_dec))
        )
        if self.release_command is not None:
            self.release_command()
        elif self.command is not None:
            self.command()
        return "break"

    def _redraw(self, *_args) -> None:
        if not self.winfo_exists():
            return
        canvas = self.canvas
        canvas.delete("all")
        x0, y0, x1, y1 = self._plot_box()
        if night_mode_enabled(self):
            surface = NIGHT_BACKGROUND if self._enabled else NIGHT_FIELD
            grid = NIGHT_BORDER
            text = NIGHT_TEXT if self._enabled else NIGHT_MUTED
            equator = "#d40000" if self._enabled else NIGHT_MUTED
            ecliptic = "#b50000" if self._enabled else NIGHT_MUTED
            footprint = "#ff0000" if self._enabled else NIGHT_MUTED
            footprint_fill = "#260000" if self._enabled else NIGHT_FIELD
            marker_outline = NIGHT_BACKGROUND
            heading = NIGHT_TEXT
        else:
            surface = "#0b1421" if self._enabled else "#222831"
            grid = "#30445a" if self._enabled else "#444b53"
            text = "#b9c8d8" if self._enabled else "#858b92"
            equator = "#4d8cad" if self._enabled else "#56636d"
            ecliptic = "#a77935" if self._enabled else "#6d6250"
            footprint = "#f0bd45" if self._enabled else "#888888"
            footprint_fill = "#14283d" if self._enabled else "#30363d"
            marker_outline = "#ffffff" if self._enabled else footprint
            heading = "#eef5fc" if self._enabled else text

        canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill=surface,
            outline=grid,
            width=1,
        )
        self._draw_coverage_fill(footprint_fill)

        for hour in range(0, 25, 3):
            x, _ = self._project(float(hour % 24), 0.0)
            if hour == 24:
                x = x0
            canvas.create_line(x, y0, x, y1, fill=grid, width=1)
            label = "24h" if hour == 24 else f"{hour}h"
            canvas.create_text(x, y1 + 13, text=label, fill=text, font=("TkDefaultFont", 8))
        for dec in range(-60, 61, 30):
            _, y = self._project(0.0, float(dec))
            canvas.create_line(x0, y, x1, y, fill=grid, width=1)
            canvas.create_text(
                x0 - 5,
                y,
                text=f"{dec:+d}°" if dec else "0°",
                fill=text,
                anchor="e",
                font=("TkDefaultFont", 8),
            )

        _, equator_y = self._project(0.0, 0.0)
        canvas.create_line(x0, equator_y, x1, equator_y, fill=equator, width=2)
        self._draw_ecliptic(ecliptic)
        self._draw_coverage(footprint)

        ra = float(self.ra_variable.get()) % 24.0
        dec = min(90.0, max(-90.0, float(self.dec_variable.get())))
        x, y = self._project(ra, dec)
        canvas.create_oval(
            x - 7,
            y - 7,
            x + 7,
            y + 7,
            fill=footprint,
            outline=marker_outline,
            width=2,
        )
        canvas.create_line(x - 12, y, x + 12, y, fill=footprint, width=1)
        canvas.create_line(x, y - 12, x, y + 12, fill=footprint, width=1)
        canvas.create_text(
            x0 + 7,
            y0 + 7,
            anchor="nw",
            text=(
                f"Zenith  RA {self._format_ra(ra)}   Dec {dec:+.1f}°\n"
                f"Displayed radius {float(self.sky_radius_variable.get()):.0f}°"
            ),
            fill=heading,
            font=("TkDefaultFont", 9, "bold"),
        )
        canvas.create_text(
            (x0 + x1) / 2,
            y1 + 26,
            text="Right ascension increases to the left — drag to place the zenith",
            fill=text,
            font=("TkDefaultFont", 8),
        )

    def _draw_ecliptic(self, colour: str) -> None:
        points: list[tuple[float, float]] = []
        obliquity = math.radians(23.4393)
        for degree in range(361):
            longitude = math.radians(float(degree))
            ra = math.atan2(
                math.cos(obliquity) * math.sin(longitude),
                math.cos(longitude),
            )
            dec = math.asin(math.sin(obliquity) * math.sin(longitude))
            ra_hours = (math.degrees(ra) % 360.0) / 15.0
            points.append(self._project(ra_hours, math.degrees(dec)))
        self._draw_wrapped_polyline(points, colour=colour, width=1)


    def _draw_coverage_fill(self, colour: str) -> None:
        """Lightly shade the spherical cap represented by the current map.

        The selector uses an equirectangular projection, so the cap is filled
        as narrow declination bands. This handles right-ascension wrapping and
        polar caps without constructing a self-intersecting canvas polygon.
        """
        radius_degrees = min(180.0, max(0.0, float(self.sky_radius_variable.get())))
        if radius_degrees <= 0.05:
            return

        x0, y0, x1, y1 = self._plot_box()
        if radius_degrees >= 179.95:
            self.canvas.create_rectangle(
                x0 + 1,
                y0 + 1,
                x1 - 1,
                y1 - 1,
                fill=colour,
                outline="",
            )
            return

        ra0_hours = float(self.ra_variable.get()) % 24.0
        dec0 = math.radians(float(self.dec_variable.get()))
        cos_radius = math.cos(math.radians(radius_degrees))
        band_count = max(48, min(120, int((y1 - y0) / 2.0)))
        band_height_degrees = 180.0 / band_count

        def draw_ra_interval(start_hours: float, end_hours: float, top: float, bottom: float) -> None:
            start_hours %= 24.0
            end_hours %= 24.0
            if abs((end_hours - start_hours) % 24.0) < 1e-9:
                self.canvas.create_rectangle(
                    x0, top, x1, bottom, fill=colour, outline=""
                )
                return
            if start_hours <= end_hours:
                x_start, _ = self._project(start_hours, 0.0)
                x_end, _ = self._project(end_hours, 0.0)
                self.canvas.create_rectangle(
                    min(x_start, x_end),
                    top,
                    max(x_start, x_end),
                    bottom,
                    fill=colour,
                    outline="",
                )
            else:
                draw_ra_interval(start_hours, 24.0 - 1e-9, top, bottom)
                draw_ra_interval(0.0, end_hours, top, bottom)

        for index in range(band_count):
            dec_top = 90.0 - index * band_height_degrees
            dec_bottom = dec_top - band_height_degrees
            dec_center = math.radians((dec_top + dec_bottom) / 2.0)
            numerator = cos_radius - math.sin(dec_center) * math.sin(dec0)
            denominator = math.cos(dec_center) * math.cos(dec0)

            if abs(denominator) < 1e-10:
                if numerator <= 0.0:
                    half_width_hours = 12.0
                else:
                    continue
            else:
                threshold = numerator / denominator
                if threshold > 1.0:
                    continue
                if threshold <= -1.0:
                    half_width_hours = 12.0
                else:
                    half_width_hours = math.degrees(math.acos(threshold)) / 15.0

            _, top = self._project(0.0, dec_top)
            _, bottom = self._project(0.0, dec_bottom)
            if half_width_hours >= 11.999999:
                self.canvas.create_rectangle(
                    x0, top, x1, bottom, fill=colour, outline=""
                )
            else:
                draw_ra_interval(
                    ra0_hours - half_width_hours,
                    ra0_hours + half_width_hours,
                    top,
                    bottom,
                )

    def _draw_coverage(self, colour: str) -> None:
        radius_degrees = min(180.0, max(0.0, float(self.sky_radius_variable.get())))
        x0, y0, x1, y1 = self._plot_box()
        if radius_degrees >= 179.5:
            self.canvas.create_rectangle(
                x0 + 2,
                y0 + 2,
                x1 - 2,
                y1 - 2,
                outline=colour,
                width=3,
            )
            return

        ra0 = math.radians(float(self.ra_variable.get()) % 24.0 * 15.0)
        dec0 = math.radians(float(self.dec_variable.get()))
        rho = math.radians(radius_degrees)
        points: list[tuple[float, float]] = []
        for bearing_degree in range(361):
            bearing = math.radians(float(bearing_degree))
            dec = math.asin(
                math.sin(dec0) * math.cos(rho)
                + math.cos(dec0) * math.sin(rho) * math.cos(bearing)
            )
            delta_ra = math.atan2(
                math.sin(bearing) * math.sin(rho) * math.cos(dec0),
                math.cos(rho) - math.sin(dec0) * math.sin(dec),
            )
            ra = (ra0 + delta_ra) % (2.0 * math.pi)
            points.append(self._project(math.degrees(ra) / 15.0, math.degrees(dec)))
        self._draw_wrapped_polyline(points, colour=colour, width=2)

    def _draw_wrapped_polyline(
        self,
        points: list[tuple[float, float]],
        *,
        colour: str,
        width: int,
    ) -> None:
        x0, _y0, x1, _y1 = self._plot_box()
        wrap_threshold = (x1 - x0) * 0.55
        segment: list[float] = []
        previous_x: float | None = None
        for x, y in points:
            if previous_x is not None and abs(x - previous_x) > wrap_threshold:
                if len(segment) >= 4:
                    self.canvas.create_line(*segment, fill=colour, width=width, smooth=True)
                segment = []
            segment.extend((x, y))
            previous_x = x
        if len(segment) >= 4:
            self.canvas.create_line(*segment, fill=colour, width=width, smooth=True)

    @staticmethod
    def _format_ra(hours: float) -> str:
        total_minutes = int(round((hours % 24.0) * 60.0)) % (24 * 60)
        hour, minute = divmod(total_minutes, 60)
        return f"{hour:02d}h {minute:02d}m"

    def _on_destroy(self, event) -> None:
        if event.widget is not self:
            return
        for variable, trace_id in self._traces:
            try:
                variable.trace_remove("write", trace_id)
            except (tk.TclError, ValueError):
                pass

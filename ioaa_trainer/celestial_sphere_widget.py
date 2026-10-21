"""Interactive celestial-sphere view for the coordinate-converter tool.

The widget draws the astronomical (navigational) triangle whose vertices are
P = north celestial pole, Z = zenith, and ★ = the selected celestial object.
It also overlays the equator, horizon, meridian, and the coordinate arcs used
by the RA/Dec <-> Alt/Az conversion.
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk
from typing import Sequence

from .coordinate_converter import (
    equatorial_from_horizontal,
    horizontal_from_equatorial,
    parse_degrees,
    parse_hours,
)
from .theme import (
    NIGHT_BACKGROUND,
    NIGHT_BORDER,
    NIGHT_MUTED,
    NIGHT_TEXT,
    night_mode_enabled,
)

Vector3 = tuple[float, float, float]
Matrix3 = tuple[Vector3, Vector3, Vector3]


def _dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(v: Vector3) -> float:
    return math.sqrt(_dot(v, v))


def _unit(v: Vector3) -> Vector3:
    length = _norm(v)
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _mat_mul(a: Matrix3, b: Matrix3) -> Matrix3:
    """Multiply two 3x3 matrices."""
    return tuple(
        tuple(sum(a[row][k] * b[k][col] for k in range(3)) for col in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _mat_vec(matrix: Matrix3, vector: Vector3) -> Vector3:
    """Apply a 3x3 matrix to a vector."""
    return (
        _dot(matrix[0], vector),
        _dot(matrix[1], vector),
        _dot(matrix[2], vector),
    )


def _rotation_x(angle: float) -> Matrix3:
    """Camera-space rotation about the horizontal screen axis."""
    c = math.cos(angle)
    s = math.sin(angle)
    return (
        (1.0, 0.0, 0.0),
        (0.0, c, -s),
        (0.0, s, c),
    )


def _rotation_z(angle: float) -> Matrix3:
    """Camera-space rotation about the vertical screen axis."""
    c = math.cos(angle)
    s = math.sin(angle)
    return (
        (c, -s, 0.0),
        (s, c, 0.0),
        (0.0, 0.0, 1.0),
    )


def _default_view_matrix() -> Matrix3:
    """Observer-centred Alt-Az view: Z up, E right, N on the near horizon."""
    # A slight downward tilt makes the local horizon read as an ellipse while
    # preserving the intuitive Alt-Az layout (zenith up, east to the right).
    return _rotation_x(math.radians(-22.0))


def _cross(a: Vector3, b: Vector3) -> Vector3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _great_circle_arc(a: Vector3, b: Vector3, samples: int = 72) -> list[Vector3]:
    """Return a spherical linear interpolation along the shorter great-circle arc."""
    a = _unit(a)
    b = _unit(b)
    cosine = max(-1.0, min(1.0, _dot(a, b)))
    angle = math.acos(cosine)
    if angle < 1e-8:
        return [a, b]
    if math.pi - angle < 1e-6:
        # Antipodes have no unique connecting great circle. Choose a stable
        # perpendicular direction so the limiting case remains drawable.
        helper = (0.0, 1.0, 0.0) if abs(a[1]) < 0.9 else (1.0, 0.0, 0.0)
        tangent = _unit(_cross(helper, a))
        return [
            _unit(
                (
                    math.cos(math.pi * i / samples) * a[0]
                    + math.sin(math.pi * i / samples) * tangent[0],
                    math.cos(math.pi * i / samples) * a[1]
                    + math.sin(math.pi * i / samples) * tangent[1],
                    math.cos(math.pi * i / samples) * a[2]
                    + math.sin(math.pi * i / samples) * tangent[2],
                )
            )
            for i in range(samples + 1)
        ]
    sine = math.sin(angle)
    points: list[Vector3] = []
    for i in range(samples + 1):
        t = i / samples
        weight_a = math.sin((1.0 - t) * angle) / sine
        weight_b = math.sin(t * angle) / sine
        points.append(
            (
                weight_a * a[0] + weight_b * b[0],
                weight_a * a[1] + weight_b * b[1],
                weight_a * a[2] + weight_b * b[2],
            )
        )
    return points


def _circle_in_plane(u: Vector3, v: Vector3, samples: int = 144) -> list[Vector3]:
    u = _unit(u)
    v = _unit(v)
    return [
        (
            math.cos(2.0 * math.pi * i / samples) * u[0]
            + math.sin(2.0 * math.pi * i / samples) * v[0],
            math.cos(2.0 * math.pi * i / samples) * u[1]
            + math.sin(2.0 * math.pi * i / samples) * v[1],
            math.cos(2.0 * math.pi * i / samples) * u[2]
            + math.sin(2.0 * math.pi * i / samples) * v[2],
        )
        for i in range(samples + 1)
    ]


def _arc_in_plane(
    u: Vector3,
    v: Vector3,
    start_degrees: float,
    end_degrees: float,
    samples: int = 64,
) -> list[Vector3]:
    u = _unit(u)
    v = _unit(v)
    return [
        (
            math.cos(math.radians(start_degrees + (end_degrees - start_degrees) * i / samples)) * u[0]
            + math.sin(math.radians(start_degrees + (end_degrees - start_degrees) * i / samples)) * v[0],
            math.cos(math.radians(start_degrees + (end_degrees - start_degrees) * i / samples)) * u[1]
            + math.sin(math.radians(start_degrees + (end_degrees - start_degrees) * i / samples)) * v[1],
            math.cos(math.radians(start_degrees + (end_degrees - start_degrees) * i / samples)) * u[2]
            + math.sin(math.radians(start_degrees + (end_degrees - start_degrees) * i / samples)) * v[2],
        )
        for i in range(samples + 1)
    ]


class CelestialSphereTriangle(ttk.Frame):
    """Draggable orthographic celestial sphere linked to converter variables."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        latitude_var: tk.StringVar,
        ra_var: tk.StringVar,
        dec_var: tk.StringVar,
        lst_var: tk.StringVar,
        ha_var: tk.StringVar,
        alt_var: tk.StringVar,
        az_var: tk.StringVar,
    ) -> None:
        super().__init__(parent)
        self._vars = {
            "latitude": latitude_var,
            "ra": ra_var,
            "dec": dec_var,
            "lst": lst_var,
            "ha": ha_var,
            "alt": alt_var,
            "az": az_var,
        }
        # View coordinates are observer-centred: local east = screen-right,
        # local north = depth, and zenith = screen-up before the gentle default tilt.
        self._observer_transform: Matrix3 = (
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        )
        self._view_matrix: Matrix3 = _default_view_matrix()
        self._zoom = 0.86
        self._drag_origin: tuple[int, int] | None = None
        self._drag_view: Matrix3 | None = None
        self._redraw_job: str | None = None

        self.columnconfigure(0, weight=1)
        ttk.Label(
            self,
            text="Interactive celestial sphere — astronomical triangle P–Z–★",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            self,
            text=(
                "P is the north celestial pole, Z is the zenith, and ★ is the object. "
                "The default view is observer-centred Alt–Az (Z up, E right); drag to rotate "
                "the sphere and use the mouse wheel to zoom."
            ),
            wraplength=710,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(3, 7))

        self.canvas = tk.Canvas(
            self,
            height=370,
            highlightthickness=1,
            bd=0,
            cursor="fleur",
            takefocus=True,
        )
        self.canvas.grid(row=2, column=0, sticky="ew")
        self.canvas.bind("<Configure>", lambda _event: self._schedule_redraw())
        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_end)
        self.canvas.bind("<Double-Button-1>", lambda _event: self.reset_view())
        self.canvas.bind("<MouseWheel>", self._mouse_wheel)
        self.canvas.bind("<Button-4>", self._linux_wheel)
        self.canvas.bind("<Button-5>", self._linux_wheel)

        controls = ttk.Frame(self)
        controls.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        controls.columnconfigure(0, weight=1)
        self.readout_var = tk.StringVar(value="Enter converter values above to place the star.")
        ttk.Label(
            controls,
            textvariable=self.readout_var,
            wraplength=620,
            justify="left",
            font=("TkDefaultFont", 9, "italic"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(controls, text="Reset view", command=self.reset_view).grid(
            row=0, column=1, sticky="e", padx=(10, 0)
        )

        for variable in self._vars.values():
            variable.trace_add("write", self._values_changed)

        self.refresh_theme()
        self.after_idle(self._redraw)

    # --------------------------------------------------------------- public
    def reset_view(self) -> None:
        self._view_matrix = _default_view_matrix()
        self._drag_origin = None
        self._drag_view = None
        self._zoom = 0.86
        self._schedule_redraw()

    def refresh_theme(self) -> None:
        night = night_mode_enabled(self)
        if night:
            self._palette = {
                "background": NIGHT_BACKGROUND,
                "border": NIGHT_BORDER,
                "sphere": NIGHT_BORDER,
                "back": NIGHT_MUTED,
                "equator": "#980000",
                "horizon": "#d00000",
                "meridian": "#720000",
                "triangle": "#ff3030",
                "coordinate": "#c00000",
                "star": NIGHT_TEXT,
                "point": NIGHT_TEXT,
                "text": NIGHT_TEXT,
                "muted": NIGHT_MUTED,
            }
        else:
            self._palette = {
                "background": "#f7f9fc",
                "border": "#b8c2cf",
                "sphere": "#5b6675",
                "back": "#aeb7c2",
                "equator": "#386cb0",
                "horizon": "#1b8a6b",
                "meridian": "#7a8796",
                "triangle": "#7b3fb2",
                "coordinate": "#c56b00",
                "star": "#b85f00",
                "point": "#293241",
                "text": "#202833",
                "muted": "#66717f",
            }
        self.canvas.configure(
            background=self._palette["background"],
            highlightbackground=self._palette["border"],
            highlightcolor=self._palette["border"],
        )
        self._schedule_redraw()

    # ---------------------------------------------------------- interaction
    def _values_changed(self, *_args) -> None:
        self._schedule_redraw()

    def _schedule_redraw(self) -> None:
        if self._redraw_job is not None:
            try:
                self.after_cancel(self._redraw_job)
            except tk.TclError:
                pass
        self._redraw_job = self.after_idle(self._redraw)

    def _drag_start(self, event: tk.Event) -> None:
        self._drag_origin = (event.x, event.y)
        self._drag_view = self._view_matrix

    def _drag_move(self, event: tk.Event) -> None:
        if self._drag_origin is None or self._drag_view is None:
            return
        dx = event.x - self._drag_origin[0]
        dy = event.y - self._drag_origin[1]

        # Rotate around *camera-space* up/right axes rather than fixed sphere
        # axes. This keeps drag direction consistent after arbitrary tilts.
        # Signs follow a grab-and-drag model: content under the pointer moves
        # in the same left/right and up/down direction as the pointer.
        horizontal = _rotation_z(math.radians(-dx * 0.45))
        vertical = _rotation_x(math.radians(-dy * 0.45))
        drag_rotation = _mat_mul(vertical, horizontal)
        self._view_matrix = _mat_mul(drag_rotation, self._drag_view)
        self._schedule_redraw()

    def _drag_end(self, _event: tk.Event) -> None:
        self._drag_origin = None
        self._drag_view = None

    def _mouse_wheel(self, event: tk.Event) -> str:
        if event.delta != 0:
            self._zoom_by(1.08 if event.delta > 0 else 1.0 / 1.08)
        return "break"

    def _linux_wheel(self, event: tk.Event) -> str:
        self._zoom_by(1.08 if event.num == 4 else 1.0 / 1.08)
        return "break"

    def _zoom_by(self, factor: float) -> None:
        self._zoom = max(0.58, min(1.22, self._zoom * factor))
        self._schedule_redraw()

    # --------------------------------------------------------------- parsing
    def _hours(self, name: str, *, signed: bool) -> float | None:
        text = self._vars[name].get().strip()
        if not text:
            return None
        try:
            return parse_hours(text, signed=signed)
        except ValueError:
            return None

    def _degrees(
        self,
        name: str,
        minimum: float,
        maximum: float,
        *,
        wrap_360: bool = False,
    ) -> float | None:
        text = self._vars[name].get().strip()
        if not text:
            return None
        try:
            return parse_degrees(
                text,
                minimum=minimum,
                maximum=maximum,
                label=name.title(),
                wrap_360=wrap_360,
            )
        except ValueError:
            return None

    # --------------------------------------------------------------- drawing
    def _redraw(self) -> None:
        self._redraw_job = None
        if not self.winfo_exists():
            return
        canvas = self.canvas
        canvas.delete("all")
        width = max(320, canvas.winfo_width())
        height = max(300, canvas.winfo_height())
        cx = width * 0.50
        cy = height * 0.49
        radius = min(width * 0.31, height * 0.39) * self._zoom
        radius = max(98.0, radius)
        self._projection = (cx, cy, radius)

        # Orthographic limb of the celestial sphere.
        p = self._palette
        canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            outline=p["sphere"],
            width=2,
        )

        latitude = self._degrees("latitude", -90.0, 90.0)
        dec = self._degrees("dec", -90.0, 90.0)
        ha = self._hours("ha", signed=True)
        altitude = self._degrees("alt", -90.0, 90.0)
        azimuth = self._degrees("az", 0.0, 360.0, wrap_360=True)

        if latitude is None:
            self._observer_transform = (
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 1.0),
            )
            self._draw_equator()
            self._draw_poles()
            self._draw_center_message("Enter observer latitude to orient the horizon and zenith.")
            self.readout_var.set("Enter observer latitude to begin the celestial-sphere view.")
            return

        # If the star is presently defined only in horizontal coordinates,
        # derive the equivalent Dec/H so it can still be shown immediately.
        if (dec is None or ha is None) and altitude is not None and azimuth is not None:
            try:
                dec, ha = equatorial_from_horizontal(latitude, altitude, azimuth)
            except ValueError:
                pass

        # Conversely, fill geometry-only Alt/Az when equatorial values exist.
        if dec is not None and ha is not None and (altitude is None or azimuth is None):
            try:
                altitude, azimuth = horizontal_from_equatorial(latitude, dec, ha)
            except ValueError:
                pass

        phi = math.radians(latitude)
        north: Vector3 = (-math.sin(phi), 0.0, math.cos(phi))
        east: Vector3 = (0.0, 1.0, 0.0)
        zenith: Vector3 = (math.cos(phi), 0.0, math.sin(phi))
        pole: Vector3 = (0.0, 0.0, 1.0)
        south_pole: Vector3 = (0.0, 0.0, -1.0)

        # Convert equatorial world vectors into the observer's local Alt-Az
        # frame before applying the camera view. Thus changing latitude moves
        # the celestial pole/equator, not the local horizon or zenith.
        self._observer_transform = (east, north, zenith)

        # Reference circles first so the triangle remains visually dominant.
        self._draw_polyline(
            _circle_in_plane((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            front_color=p["equator"],
            back_color=p["back"],
            width=1.5,
        )
        self._draw_polyline(
            _circle_in_plane(north, east),
            front_color=p["horizon"],
            back_color=p["back"],
            width=1.8,
        )
        self._draw_polyline(
            _circle_in_plane((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            front_color=p["meridian"],
            back_color=p["back"],
            width=1.0,
        )
        self._draw_point(pole, "P", "NCP")
        self._draw_point(south_pole, "", "")
        self._draw_point(zenith, "Z", "Zenith")
        self._draw_reference_label((1.0, 0.0, 0.0), "Celestial equator", p["equator"])
        self._draw_reference_label(north, "N", p["horizon"])
        self._draw_reference_label(east, "E", p["horizon"])
        self._draw_reference_label((-north[0], -north[1], -north[2]), "S", p["horizon"])
        self._draw_reference_label((-east[0], -east[1], -east[2]), "W", p["horizon"])

        if dec is None or ha is None:
            self._draw_center_message("Enter enough values above to determine the star position.")
            self.readout_var.set(
                "Sphere oriented for the entered latitude. Add RA/Dec + LST/H, or Alt/Az, to place ★."
            )
            return

        dec_r = math.radians(dec)
        ha_deg = ha * 15.0
        ha_r = math.radians(ha_deg)
        star: Vector3 = (
            math.cos(dec_r) * math.cos(ha_r),
            -math.cos(dec_r) * math.sin(ha_r),
            math.sin(dec_r),
        )

        # Astronomical triangle P-Z-star.
        triangle_arcs = [
            (pole, zenith, f"90°−φ = {90.0 - latitude:.1f}°"),
            (pole, star, f"90°−δ = {90.0 - dec:.1f}°"),
            (
                zenith,
                star,
                f"z = 90°−h = {90.0 - altitude:.1f}°" if altitude is not None else "z = 90°−h",
            ),
        ]
        for start, end, label in triangle_arcs:
            arc = _great_circle_arc(start, end)
            self._draw_polyline(
                arc,
                front_color=p["triangle"],
                back_color=p["back"],
                width=3.0,
            )
            self._draw_arc_label(arc, label, p["triangle"])

        # Coordinate construction arcs: H on the equator, δ along the hour
        # circle, A on the horizon, and h up the vertical circle.
        equator_object: Vector3 = (math.cos(ha_r), -math.sin(ha_r), 0.0)
        h_arc = _arc_in_plane((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), 0.0, ha_deg)
        self._draw_polyline(
            h_arc,
            front_color=p["coordinate"],
            back_color=p["back"],
            width=2.0,
        )
        self._draw_arc_label(h_arc, f"H = {ha:+.2f} h", p["coordinate"], offset=13)

        dec_arc = _great_circle_arc(equator_object, star, samples=38)
        self._draw_polyline(
            dec_arc,
            front_color=p["coordinate"],
            back_color=p["back"],
            width=2.0,
        )
        self._draw_arc_label(dec_arc, f"δ = {dec:+.1f}°", p["coordinate"], offset=13)

        if altitude is not None and azimuth is not None:
            az_r = math.radians(azimuth)
            horizon_foot: Vector3 = (
                math.cos(az_r) * north[0] + math.sin(az_r) * east[0],
                math.cos(az_r) * north[1] + math.sin(az_r) * east[1],
                math.cos(az_r) * north[2] + math.sin(az_r) * east[2],
            )
            az_arc = _arc_in_plane(north, east, 0.0, azimuth, samples=max(24, int(abs(azimuth) / 4) + 1))
            self._draw_polyline(
                az_arc,
                front_color=p["coordinate"],
                back_color=p["back"],
                width=2.0,
            )
            self._draw_arc_label(az_arc, f"A = {azimuth:.1f}°", p["coordinate"], offset=13)

            alt_arc = _great_circle_arc(horizon_foot, star, samples=38)
            self._draw_polyline(
                alt_arc,
                front_color=p["coordinate"],
                back_color=p["back"],
                width=2.0,
            )
            self._draw_arc_label(alt_arc, f"h = {altitude:+.1f}°", p["coordinate"], offset=13)

        self._draw_point(star, "★", "Object", star=True)
        self._draw_angle_hint(pole, f"∠P = |H| = {abs(ha_deg):.1f}°")

        side_text = (
            f"φ={latitude:+.1f}°   δ={dec:+.1f}°   H={ha:+.2f} h"
            + (f"   h={altitude:+.1f}°   A={azimuth:.1f}°" if altitude is not None and azimuth is not None else "")
        )
        self.readout_var.set(side_text)

    def _draw_equator(self) -> None:
        p = self._palette
        self._draw_polyline(
            _circle_in_plane((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            front_color=p["equator"],
            back_color=p["back"],
            width=1.5,
        )

    def _draw_poles(self) -> None:
        self._draw_point((0.0, 0.0, 1.0), "P", "NCP")
        self._draw_point((0.0, 0.0, -1.0), "", "")

    def _rotate(self, point: Vector3) -> Vector3:
        # World (equatorial) -> local observer (E, N, Z) -> camera.
        local = _mat_vec(self._observer_transform, point)
        return _mat_vec(self._view_matrix, local)

    def _project(self, point: Vector3) -> tuple[float, float, float]:
        x, depth, z = self._rotate(point)
        cx, cy, radius = self._projection
        return cx + radius * x, cy - radius * z, depth

    def _draw_polyline(
        self,
        points: Sequence[Vector3],
        *,
        front_color: str,
        back_color: str,
        width: float,
    ) -> None:
        if len(points) < 2:
            return
        projected = [self._project(point) for point in points]
        current_back: bool | None = None
        run: list[float] = []

        def flush() -> None:
            if len(run) < 4 or current_back is None:
                return
            self.canvas.create_line(
                *run,
                fill=back_color if current_back else front_color,
                width=max(1, int(round(width))),
                dash=(4, 4) if current_back else (),
                capstyle="round",
                joinstyle="round",
            )

        for first, second in zip(projected, projected[1:]):
            back = (first[2] + second[2]) * 0.5 < -0.015
            if current_back is None:
                current_back = back
                run = [first[0], first[1], second[0], second[1]]
            elif back == current_back:
                run.extend((second[0], second[1]))
            else:
                flush()
                current_back = back
                run = [first[0], first[1], second[0], second[1]]
        flush()

    def _draw_point(
        self,
        point: Vector3,
        symbol: str,
        description: str,
        *,
        star: bool = False,
    ) -> None:
        x, y, depth = self._project(point)
        p = self._palette
        radius = 7 if star else 4
        fill = p["star"] if star else p["point"]
        outline = p["background"] if depth >= 0 else p["back"]
        if star:
            coordinates: list[float] = []
            for i in range(10):
                angle = math.radians(-90.0 + i * 36.0)
                point_radius = radius if i % 2 == 0 else radius * 0.42
                coordinates.extend(
                    (x + point_radius * math.cos(angle), y + point_radius * math.sin(angle))
                )
            self.canvas.create_polygon(
                *coordinates,
                fill=fill,
                outline=outline,
                width=1,
            )
        else:
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=fill,
                outline=outline,
                width=1,
            )
        if not symbol and not description:
            return
        label = symbol if not description else f"{symbol}  {description}"
        dx = 10 if x <= self._projection[0] else -10
        anchor = "w" if dx > 0 else "e"
        self.canvas.create_text(
            x + dx,
            y - 8,
            text=label,
            fill=p["text"] if depth >= 0 else p["muted"],
            font=("TkDefaultFont", 9, "bold"),
            anchor=anchor,
        )

    def _draw_reference_label(self, point: Vector3, text: str, color: str) -> None:
        x, y, _depth = self._project(point)
        cx, cy, _radius = self._projection
        dx = 12 if x <= cx else -12
        dy = -12 if y >= cy else 12
        self.canvas.create_text(
            x + dx,
            y + dy,
            text=text,
            fill=color,
            font=("TkDefaultFont", 8, "italic"),
            anchor="w" if dx > 0 else "e",
        )

    def _draw_arc_label(
        self,
        arc: Sequence[Vector3],
        text: str,
        color: str,
        *,
        offset: float = 10.0,
    ) -> None:
        if not arc:
            return
        point = arc[len(arc) // 2]
        x, y, depth = self._project(point)
        cx, cy, _radius = self._projection
        vx = x - cx
        vy = y - cy
        length = math.hypot(vx, vy) or 1.0
        x += offset * vx / length
        y += offset * vy / length
        self.canvas.create_text(
            x,
            y,
            text=text,
            fill=color if depth >= -0.05 else self._palette["muted"],
            font=("TkDefaultFont", 8, "bold"),
            anchor="center",
        )

    def _draw_angle_hint(self, point: Vector3, text: str) -> None:
        x, y, _depth = self._project(point)
        cx, _cy, _radius = self._projection
        anchor = "w" if x <= cx else "e"
        dx = 18 if anchor == "w" else -18
        self.canvas.create_text(
            x + dx,
            y + 15,
            text=text,
            fill=self._palette["triangle"],
            font=("TkDefaultFont", 8, "italic"),
            anchor=anchor,
        )

    def _draw_center_message(self, text: str) -> None:
        cx, cy, _radius = self._projection
        self.canvas.create_text(
            cx,
            cy,
            text=text,
            width=300,
            justify="center",
            fill=self._palette["muted"],
            font=("TkDefaultFont", 9, "italic"),
        )

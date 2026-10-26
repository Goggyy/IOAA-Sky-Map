"""Astronomical catalogue loading and coordinate calculations."""

from __future__ import annotations

import math
import threading
import warnings
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import (
    AltAz,
    EarthLocation,
    Galactic,
    GeocentricTrueEcliptic,
    ICRS,
    SkyCoord,
    get_body,
    get_body_barycentric,
)
from astropy.time import Time
from astropy.utils import iers
from astropy.utils.exceptions import AstropyWarning
from skyfield.api import Loader, load_constellation_names
from skyfield.data import hipparcos, stellarium

from .models import (
    ConstellationEdge,
    Curve,
    LabelPoint,
    MapSettings,
    SkyMapModel,
    SolarSystemObject,
    StarLayer,
)

# Avoid a separate IERS network request. Astropy uses its bundled table and
# degrades gracefully for dates outside the table's highest-accuracy interval.
iers.conf.auto_download = False
iers.conf.auto_max_age = None
iers.conf.iers_degraded_accuracy = "warn"

# Polar-motion predictions beyond the bundled IERS table affect this app only
# at the arcsecond level, far below the display resolution of the training map.
# Suppress only this specific warning while retaining other Astropy warnings.
warnings.filterwarnings(
    "ignore",
    message=r"Tried to get polar motions for times after IERS data is valid.*",
    category=AstropyWarning,
)

CACHE_DIRECTORY = Path.home() / ".ioaa_sky_trainer"

# Pinned Stellarium line data used by Skyfield's official plotting example.
CONSTELLATION_URL = (
    "https://raw.githubusercontent.com/Stellarium/stellarium/"
    "eb47095a9282cf6b981f6e37fe1ea3a3ae0fd167/"
    "skycultures/modern_st/constellationship.fab"
)

# HIP identifiers for a compact set of bright, familiar stars.
BRIGHT_STAR_NAMES: dict[int, str] = {
    7588: "Achernar",
    15863: "Mirfak",
    21421: "Aldebaran",
    24436: "Rigel",
    24608: "Capella",
    25336: "Bellatrix",
    25428: "Elnath",
    26311: "Alnilam",
    27989: "Betelgeuse",
    30438: "Canopus",
    32349: "Sirius",
    33579: "Adhara",
    36850: "Castor",
    37279: "Procyon",
    37826: "Pollux",
    45238: "Miaplacidus",
    49669: "Regulus",
    54061: "Dubhe",
    60718: "Acrux",
    61084: "Gacrux",
    62434: "Mimosa",
    62956: "Alioth",
    65474: "Spica",
    68702: "Hadar",
    69673: "Arcturus",
    71683: "Rigil Kentaurus",
    80763: "Antares",
    85927: "Shaula",
    91262: "Vega",
    97649: "Altair",
    102098: "Deneb",
    109268: "Alnair",
    113368: "Fomalhaut",
}


def local_sidereal_time_hours(settings: MapSettings) -> float:
    """Return apparent local sidereal time in decimal hours."""
    observation_time = Time(settings.observation_datetime)
    angle = observation_time.sidereal_time(
        "apparent",
        longitude=float(settings.longitude) * u.deg,
    )
    return float(angle.hour % 24.0)


def format_local_sidereal_time(settings: MapSettings) -> str:
    """Format apparent LST as HH:MM:SS."""
    total_seconds = int(round(local_sidereal_time_hours(settings) * 3600.0))
    total_seconds %= 24 * 3600
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class AstronomyData:
    """Load and cache the catalogue files shared by all exercises."""

    def __init__(self, cache_directory: Path = CACHE_DIRECTORY) -> None:
        self._loader = Loader(str(cache_directory), verbose=False)
        self._lock = threading.Lock()
        self._catalogue: pd.DataFrame | None = None
        self._constellations: list[tuple[str, list[tuple[int, int]]]] | None = None
        self._constellation_names = dict(load_constellation_names())

    def load(
        self,
    ) -> tuple[
        pd.DataFrame,
        list[tuple[str, list[tuple[int, int]]]],
        dict[str, str],
    ]:
        with self._lock:
            if self._catalogue is None:
                with self._loader.open(hipparcos.URL) as file:
                    catalogue = hipparcos.load_dataframe(file)
                catalogue = catalogue.dropna(
                    subset=["ra_degrees", "dec_degrees", "magnitude"]
                ).copy()
                catalogue.index = catalogue.index.astype(int)
                self._catalogue = catalogue

            if self._constellations is None:
                with self._loader.open(CONSTELLATION_URL) as file:
                    self._constellations = stellarium.parse_constellations(file)

        return self._catalogue, self._constellations, self._constellation_names


class SkyMapCalculator:
    """Calculate every layer once so exercises can redraw instantly."""

    def __init__(self, data: AstronomyData | None = None) -> None:
        self._data = data or AstronomyData()

    def calculate(
        self,
        settings: MapSettings,
        progress: Callable[[str], None] | None = None,
    ) -> SkyMapModel:
        report = progress or (lambda _message: None)
        report("Loading star and constellation catalogues…")
        catalogue, constellations, constellation_names = self._data.load()

        report("Transforming stars to the local horizon…")
        observation_time = Time(settings.observation_datetime)
        location = EarthLocation.from_geodetic(
            lon=settings.longitude * u.deg,
            lat=settings.latitude * u.deg,
            height=0 * u.m,
        )
        altaz_frame = AltAz(
            obstime=observation_time,
            location=location,
            pressure=0 * u.hPa,
        )

        stars_to_plot = catalogue[
            catalogue["magnitude"] <= settings.limiting_magnitude
        ]
        star_coords = SkyCoord(
            ra=stars_to_plot["ra_degrees"].to_numpy() * u.deg,
            dec=stars_to_plot["dec_degrees"].to_numpy() * u.deg,
            frame=ICRS(),
        )
        star_altaz = star_coords.transform_to(altaz_frame)
        star_alt = np.asarray(star_altaz.alt.deg, dtype=float)
        star_az = np.asarray(star_altaz.az.deg, dtype=float)
        minimum_altitude = 90.0 - float(settings.sky_radius_degrees)
        visible = (
            np.isfinite(star_alt)
            & np.isfinite(star_az)
            & (star_alt >= minimum_altitude)
        )

        visible_hip = stars_to_plot.index.to_numpy(dtype=int)[visible]
        visible_alt = star_alt[visible]
        visible_az = star_az[visible]
        visible_magnitude = stars_to_plot["magnitude"].to_numpy(dtype=float)[visible]
        stars = StarLayer(
            hip=visible_hip,
            altitude=visible_alt,
            azimuth=visible_az,
            magnitude=visible_magnitude,
        )

        named_star_lookup = {
            int(hip): (float(alt), float(az), float(magnitude))
            for hip, alt, az, magnitude in zip(
                visible_hip,
                visible_alt,
                visible_az,
                visible_magnitude,
            )
        }
        named_stars = tuple(
            LabelPoint(BRIGHT_STAR_NAMES[hip], *named_star_lookup[hip])
            for hip in BRIGHT_STAR_NAMES
            if hip in named_star_lookup
        )

        report("Building constellation layers…")
        constellation_edges, constellation_labels = self._constellation_layers(
            catalogue,
            constellations,
            constellation_names,
            altaz_frame,
            minimum_altitude,
        )

        report("Calculating reference lines and coordinate grid…")
        ecliptic = self._ecliptic_curve(observation_time, altaz_frame)
        celestial_equator = self._equatorial_curve(0.0, altaz_frame)
        galactic_equator = self._galactic_curve(altaz_frame)
        coordinate_grid = self._coordinate_grid(altaz_frame)
        # Keep these positions in every model so the Analyse view can toggle
        # the layer on even when it was hidden on the original exercise map.
        solar_system_objects = self._solar_system_objects(
            observation_time,
            location,
            altaz_frame,
            minimum_altitude,
        )

        return SkyMapModel(
            settings=settings,
            stars=stars,
            named_stars=named_stars,
            constellation_edges=constellation_edges,
            constellation_labels=constellation_labels,
            constellation_names=dict(constellation_names),
            ecliptic=ecliptic,
            celestial_equator=celestial_equator,
            galactic_equator=galactic_equator,
            coordinate_grid=coordinate_grid,
            solar_system_objects=solar_system_objects,
        )


    def _solar_system_objects(
        self,
        observation_time: Time,
        location: EarthLocation,
        altaz_frame: AltAz,
        minimum_altitude: float,
    ) -> tuple[SolarSystemObject, ...]:
        """Calculate topocentric positions using Astropy's built-in ephemeris."""
        object_names = (
            "Sun",
            "Moon",
            "Mercury",
            "Venus",
            "Mars",
            "Jupiter",
            "Saturn",
            "Uranus",
            "Neptune",
        )
        sun_position = get_body_barycentric("sun", observation_time)
        earth_position = get_body_barycentric("earth", observation_time)
        visible: list[SolarSystemObject] = []
        for display_name in object_names:
            coordinate = get_body(
                display_name.lower(),
                observation_time,
                location=location,
            ).transform_to(altaz_frame)
            altitude = float(coordinate.alt.deg)
            azimuth = float(coordinate.az.deg)
            if (
                np.isfinite(altitude)
                and np.isfinite(azimuth)
                and altitude >= minimum_altitude
            ):
                visible.append(
                    SolarSystemObject(
                        name=display_name,
                        altitude=altitude,
                        azimuth=azimuth,
                        magnitude=self._planet_apparent_magnitude(
                            display_name,
                            observation_time,
                            sun_position,
                            earth_position,
                        ),
                    )
                )
        return tuple(visible)

    @staticmethod
    def _planet_apparent_magnitude(
        name: str,
        observation_time: Time,
        sun_position,
        earth_position,
    ) -> float | None:
        """Approximate a planet's visual magnitude from distance and phase.

        The compact formulae are sufficient for matching the visual scale of
        the star catalogue.  The Sun and Moon retain their separate map
        symbols, so no stellar magnitude is assigned to them here.
        """
        if name in {"Sun", "Moon"}:
            return None

        planet_position = get_body_barycentric(name.lower(), observation_time)
        sun_to_planet = planet_position.xyz - sun_position.xyz
        earth_to_planet = planet_position.xyz - earth_position.xyz
        planet_to_sun = -sun_to_planet
        planet_to_earth = -earth_to_planet
        heliocentric_distance = float(np.linalg.norm(sun_to_planet.to_value(u.au)))
        geocentric_distance = float(np.linalg.norm(earth_to_planet.to_value(u.au)))
        cosine_phase = float(
            np.dot(
                planet_to_sun.to_value(u.au),
                planet_to_earth.to_value(u.au),
            )
            / (heliocentric_distance * geocentric_distance)
        )
        phase_angle = math.degrees(math.acos(np.clip(cosine_phase, -1.0, 1.0)))
        distance_term = 5.0 * math.log10(
            heliocentric_distance * geocentric_distance
        )

        if name == "Mercury":
            phase_term = (
                0.0380 * phase_angle
                - 0.000273 * phase_angle**2
                + 0.000002 * phase_angle**3
            )
            return -0.42 + distance_term + phase_term
        if name == "Venus":
            phase_term = (
                0.0009 * phase_angle
                + 0.000239 * phase_angle**2
                - 0.00000065 * phase_angle**3
            )
            return -4.40 + distance_term + phase_term
        if name == "Mars":
            return -1.52 + distance_term + 0.016 * phase_angle
        if name == "Jupiter":
            return -9.40 + distance_term + 0.005 * phase_angle
        if name == "Saturn":
            return -8.88 + distance_term + 0.044 * phase_angle
        if name == "Uranus":
            return -7.19 + distance_term
        if name == "Neptune":
            return -6.87 + distance_term
        return None

    @staticmethod
    def _to_altaz(coords: SkyCoord, frame: AltAz) -> tuple[np.ndarray, np.ndarray]:
        transformed = coords.transform_to(frame)
        return (
            np.asarray(transformed.alt.deg, dtype=float),
            np.asarray(transformed.az.deg, dtype=float),
        )

    def _constellation_layers(
        self,
        catalogue: pd.DataFrame,
        constellations: list[tuple[str, list[tuple[int, int]]]],
        constellation_names: dict[str, str],
        altaz_frame: AltAz,
        minimum_altitude: float,
    ) -> tuple[tuple[ConstellationEdge, ...], tuple[LabelPoint, ...]]:
        endpoint_ids = sorted(
            {
                int(hip)
                for _abbreviation, edges in constellations
                for edge in edges
                for hip in edge
                if int(hip) in catalogue.index
            }
        )
        endpoints = catalogue.loc[endpoint_ids]
        endpoint_coords = SkyCoord(
            ra=endpoints["ra_degrees"].to_numpy() * u.deg,
            dec=endpoints["dec_degrees"].to_numpy() * u.deg,
            frame=ICRS(),
        )
        endpoint_alt, endpoint_az = self._to_altaz(endpoint_coords, altaz_frame)
        horizontal = {
            int(hip): (float(alt), float(az))
            for hip, alt, az in zip(endpoint_ids, endpoint_alt, endpoint_az)
        }

        rendered_edges: list[ConstellationEdge] = []
        centroid_abbreviations: list[str] = []
        centroid_ra: list[float] = []
        centroid_dec: list[float] = []

        for abbreviation, edges in constellations:
            valid_ids = sorted(
                {
                    int(hip)
                    for edge in edges
                    for hip in edge
                    if int(hip) in horizontal
                }
            )
            if not valid_ids:
                continue

            for hip_1, hip_2 in edges:
                hip_1 = int(hip_1)
                hip_2 = int(hip_2)
                if hip_1 not in horizontal or hip_2 not in horizontal:
                    continue
                alt_1, az_1 = horizontal[hip_1]
                alt_2, az_2 = horizontal[hip_2]
                # Keep complete segments within the selected chart coverage.
                if alt_1 < minimum_altitude or alt_2 < minimum_altitude:
                    continue
                rendered_edges.append(
                    ConstellationEdge(
                        abbreviation=abbreviation,
                        altitude_1=alt_1,
                        azimuth_1=az_1,
                        altitude_2=alt_2,
                        azimuth_2=az_2,
                    )
                )

            rows = catalogue.loc[valid_ids]
            mean_ra, mean_dec = self._spherical_mean(
                rows["ra_degrees"].to_numpy(dtype=float),
                rows["dec_degrees"].to_numpy(dtype=float),
            )
            if mean_ra is not None and mean_dec is not None:
                centroid_abbreviations.append(abbreviation)
                centroid_ra.append(mean_ra)
                centroid_dec.append(mean_dec)

        labels: list[LabelPoint] = []
        if centroid_ra:
            centroid_coords = SkyCoord(
                ra=np.asarray(centroid_ra) * u.deg,
                dec=np.asarray(centroid_dec) * u.deg,
                frame=ICRS(),
            )
            centroid_alt, centroid_az = self._to_altaz(centroid_coords, altaz_frame)
            for abbreviation, alt, az in zip(
                centroid_abbreviations,
                centroid_alt,
                centroid_az,
            ):
                if (
                    np.isfinite(alt)
                    and np.isfinite(az)
                    and alt > minimum_altitude + 3.0
                ):
                    labels.append(
                        LabelPoint(
                            constellation_names.get(abbreviation, abbreviation),
                            float(alt),
                            float(az),
                        )
                    )

        return tuple(rendered_edges), tuple(labels)

    @staticmethod
    def _spherical_mean(
        ra_degrees: np.ndarray,
        dec_degrees: np.ndarray,
    ) -> tuple[float | None, float | None]:
        ra = np.deg2rad(ra_degrees)
        dec = np.deg2rad(dec_degrees)
        vector = np.array(
            [
                (np.cos(dec) * np.cos(ra)).mean(),
                (np.cos(dec) * np.sin(ra)).mean(),
                np.sin(dec).mean(),
            ]
        )
        norm = float(np.linalg.norm(vector))
        if norm < 1e-12:
            return None, None
        vector /= norm
        mean_ra = math.degrees(math.atan2(vector[1], vector[0])) % 360.0
        mean_dec = math.degrees(math.asin(float(vector[2])))
        return mean_ra, mean_dec

    def _ecliptic_curve(self, observation_time: Time, altaz_frame: AltAz) -> Curve:
        longitude = np.linspace(0.0, 360.0, 721)
        coords = SkyCoord(
            lon=longitude * u.deg,
            lat=np.zeros_like(longitude) * u.deg,
            frame=GeocentricTrueEcliptic(
                equinox=observation_time,
                obstime=observation_time,
            ),
        )
        altitude, azimuth = self._to_altaz(coords, altaz_frame)
        return Curve(altitude, azimuth)

    def _galactic_curve(self, altaz_frame: AltAz) -> Curve:
        longitude = np.linspace(0.0, 360.0, 721)
        coords = SkyCoord(
            l=longitude * u.deg,
            b=np.zeros_like(longitude) * u.deg,
            frame=Galactic(),
        )
        altitude, azimuth = self._to_altaz(coords, altaz_frame)
        return Curve(altitude, azimuth)

    def _equatorial_curve(self, declination: float, altaz_frame: AltAz) -> Curve:
        ra = np.linspace(0.0, 360.0, 721)
        coords = SkyCoord(
            ra=ra * u.deg,
            dec=np.full_like(ra, declination) * u.deg,
            frame=ICRS(),
        )
        altitude, azimuth = self._to_altaz(coords, altaz_frame)
        return Curve(altitude, azimuth)

    def _right_ascension_curve(self, ra_degrees: float, altaz_frame: AltAz) -> Curve:
        dec = np.linspace(-89.75, 89.75, 361)
        coords = SkyCoord(
            ra=np.full_like(dec, ra_degrees) * u.deg,
            dec=dec * u.deg,
            frame=ICRS(),
        )
        altitude, azimuth = self._to_altaz(coords, altaz_frame)
        return Curve(altitude, azimuth)

    def _coordinate_grid(self, altaz_frame: AltAz) -> tuple[Curve, ...]:
        curves: list[Curve] = []
        for hour in range(0, 24, 2):
            curves.append(self._right_ascension_curve(hour * 15.0, altaz_frame))
        for declination in range(-75, 76, 15):
            curves.append(self._equatorial_curve(float(declination), altaz_frame))
        return tuple(curves)

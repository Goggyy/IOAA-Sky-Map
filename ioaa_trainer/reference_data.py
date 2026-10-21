"""Small curated reference lists used by specialised training exercises."""

from __future__ import annotations

from dataclasses import dataclass


# The 13 IAU constellations crossed by the ecliptic. Ophiuchus is included
# because this is an astronomy trainer rather than an astrological sign list.
ZODIACAL_CONSTELLATION_ABBREVIATIONS: frozenset[str] = frozenset(
    {
        "Ari",  # Aries
        "Tau",  # Taurus
        "Gem",  # Gemini
        "Cnc",  # Cancer
        "Leo",  # Leo
        "Vir",  # Virgo
        "Lib",  # Libra
        "Sco",  # Scorpius
        "Oph",  # Ophiuchus
        "Sgr",  # Sagittarius
        "Cap",  # Capricornus
        "Aqr",  # Aquarius
        "Psc",  # Pisces
    }
)


@dataclass(frozen=True)
class BrightStarIdentity:
    """Identity expected from students in the bright-star naming exercise."""

    hip: int
    iau_name: str
    bayer_full: str
    bayer_short: str

    @property
    def answer(self) -> str:
        return f"{self.iau_name} — {self.bayer_full} ({self.bayer_short})"


# Approximately the 20 brightest individual night-sky stars. Proper names use
# IAU Working Group on Star Names spellings; HIP identifiers match the
# Hipparcos catalogue used by the rest of the application.
BRIGHTEST_STAR_IDENTITIES: tuple[BrightStarIdentity, ...] = (
    BrightStarIdentity(32349, "Sirius", "Alpha Canis Majoris", "α CMa"),
    BrightStarIdentity(30438, "Canopus", "Alpha Carinae", "α Car"),
    BrightStarIdentity(71683, "Rigil Kentaurus", "Alpha Centauri", "α Cen"),
    BrightStarIdentity(69673, "Arcturus", "Alpha Boötis", "α Boo"),
    BrightStarIdentity(91262, "Vega", "Alpha Lyrae", "α Lyr"),
    BrightStarIdentity(24608, "Capella", "Alpha Aurigae", "α Aur"),
    BrightStarIdentity(24436, "Rigel", "Beta Orionis", "β Ori"),
    BrightStarIdentity(37279, "Procyon", "Alpha Canis Minoris", "α CMi"),
    BrightStarIdentity(7588, "Achernar", "Alpha Eridani", "α Eri"),
    BrightStarIdentity(27989, "Betelgeuse", "Alpha Orionis", "α Ori"),
    BrightStarIdentity(68702, "Hadar", "Beta Centauri", "β Cen"),
    BrightStarIdentity(97649, "Altair", "Alpha Aquilae", "α Aql"),
    BrightStarIdentity(60718, "Acrux", "Alpha Crucis", "α Cru"),
    BrightStarIdentity(21421, "Aldebaran", "Alpha Tauri", "α Tau"),
    BrightStarIdentity(80763, "Antares", "Alpha Scorpii", "α Sco"),
    BrightStarIdentity(65474, "Spica", "Alpha Virginis", "α Vir"),
    BrightStarIdentity(37826, "Pollux", "Beta Geminorum", "β Gem"),
    BrightStarIdentity(113368, "Fomalhaut", "Alpha Piscis Austrini", "α PsA"),
    BrightStarIdentity(102098, "Deneb", "Alpha Cygni", "α Cyg"),
    BrightStarIdentity(62434, "Mimosa", "Beta Crucis", "β Cru"),
)

BRIGHTEST_STAR_BY_HIP: dict[int, BrightStarIdentity] = {
    star.hip: star for star in BRIGHTEST_STAR_IDENTITIES
}

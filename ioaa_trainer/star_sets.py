"""Curated HIP identities for bright-star training exercises.

HIP and magnitude membership follows the Hipparcos data used by the app;
proper-name spellings and Bayer cross-identifications were checked against the
IAU star-name catalogue and HYG v4.1 before being stored locally here.
"""

from __future__ import annotations

from dataclasses import dataclass


GREEK_LETTERS = {
    "Alp": ("Alpha", "α"), "Bet": ("Beta", "β"),
    "Gam": ("Gamma", "γ"), "Del": ("Delta", "δ"),
    "Eps": ("Epsilon", "ε"), "Zet": ("Zeta", "ζ"),
    "Eta": ("Eta", "η"), "The": ("Theta", "θ"),
    "Iot": ("Iota", "ι"), "Kap": ("Kappa", "κ"),
    "Lam": ("Lambda", "λ"), "Mu": ("Mu", "μ"),
    "Nu": ("Nu", "ν"), "Xi": ("Xi", "ξ"),
    "Omi": ("Omicron", "ο"), "Pi": ("Pi", "π"),
    "Rho": ("Rho", "ρ"), "Sig": ("Sigma", "σ"),
    "Tau": ("Tau", "τ"), "Ups": ("Upsilon", "υ"),
    "Phi": ("Phi", "φ"), "Chi": ("Chi", "χ"),
    "Psi": ("Psi", "ψ"), "Ome": ("Omega", "ω"),
}

CONSTELLATION_GENITIVES = {
    "And": "Andromedae", "Aql": "Aquilae", "Aqr": "Aquarii",
    "Ari": "Arietis", "Aur": "Aurigae", "Boo": "Boötis",
    "Cap": "Capricorni", "Car": "Carinae", "Cas": "Cassiopeiae",
    "Cen": "Centauri", "Cep": "Cephei", "Cet": "Ceti",
    "CMa": "Canis Majoris", "CMi": "Canis Minoris", "Cnc": "Cancri",
    "Cru": "Crucis", "Cyg": "Cygni", "Eri": "Eridani",
    "Gem": "Geminorum", "Gru": "Gruis", "Hya": "Hydrae",
    "Leo": "Leonis", "Lib": "Librae", "Lyr": "Lyrae",
    "Oph": "Ophiuchi", "Ori": "Orionis", "Pav": "Pavonis",
    "Peg": "Pegasi", "Per": "Persei", "Phe": "Phoenicis",
    "PsA": "Piscis Austrini", "Psc": "Piscium", "Sco": "Scorpii",
    "Sgr": "Sagittarii", "Tau": "Tauri", "TrA": "Trianguli Australis",
    "UMa": "Ursae Majoris", "UMi": "Ursae Minoris", "Vel": "Velorum",
    "Vir": "Virginis",
}

SUPERSCRIPTS = str.maketrans("123", "¹²³")


@dataclass(frozen=True)
class TrainingStarIdentity:
    """A Hipparcos star with a display name and Bayer designation."""

    hip: int
    proper_name: str | None
    bayer_code: str
    constellation: str

    @property
    def _bayer_parts(self) -> tuple[str, str, str]:
        greek_code, separator, component = self.bayer_code.partition("-")
        greek_name, greek_symbol = GREEK_LETTERS[greek_code]
        suffix = component.translate(SUPERSCRIPTS) if separator else ""
        return greek_name, greek_symbol, suffix

    @property
    def bayer_full(self) -> str:
        greek_name, _symbol, suffix = self._bayer_parts
        return f"{greek_name}{suffix} {CONSTELLATION_GENITIVES[self.constellation]}"

    @property
    def bayer_short(self) -> str:
        _name, symbol, suffix = self._bayer_parts
        return f"{symbol}{suffix} {self.constellation}"

    @property
    def name(self) -> str:
        return self.proper_name or self.bayer_full

    @property
    def answer(self) -> str:
        if self.proper_name is None:
            return f"{self.bayer_full} ({self.bayer_short})"
        return f"{self.proper_name} — {self.bayer_full} ({self.bayer_short})"


# Ranked by Hipparcos visual magnitude. Multiple components are retained when
# they appear independently in the catalogue (for example Alpha Centauri A/B).
TOP_60_HIP_IDS = (
    32349, 30438, 69673, 71683, 91262, 24608, 24436, 37279, 7588, 27989,
    68702, 97649, 60718, 21421, 65474, 80763, 37826, 113368, 62434, 102098,
    49669, 33579, 36850, 61084, 85927, 25336, 25428, 45238, 26311,
    109268, 26727, 39953, 62956, 15863, 90185, 54061, 34444, 67301, 41037,
    86228, 28360, 82273, 42913, 31681, 100751, 11767, 30324, 46390, 50583,
    9884, 3419, 92855, 68933, 27366, 72607, 5447, 677, 112122, 86032, 14576,
)


# The full pool combines the standard stars with one principal Alpha, Beta and
# Gamma star from every zodiac constellation and the requested familiar
# constellations. Named stars use IAU spellings where available.
TRAINING_STAR_IDENTITIES = (
    TrainingStarIdentity(32349, "Sirius", "Alp", "CMa"),
    TrainingStarIdentity(30438, "Canopus", "Alp", "Car"),
    TrainingStarIdentity(69673, "Arcturus", "Alp", "Boo"),
    TrainingStarIdentity(71683, "Rigil Kentaurus", "Alp-1", "Cen"),
    TrainingStarIdentity(91262, "Vega", "Alp", "Lyr"),
    TrainingStarIdentity(24608, "Capella", "Alp", "Aur"),
    TrainingStarIdentity(24436, "Rigel", "Bet", "Ori"),
    TrainingStarIdentity(37279, "Procyon", "Alp", "CMi"),
    TrainingStarIdentity(7588, "Achernar", "Alp", "Eri"),
    TrainingStarIdentity(27989, "Betelgeuse", "Alp", "Ori"),
    TrainingStarIdentity(68702, "Hadar", "Bet", "Cen"),
    TrainingStarIdentity(97649, "Altair", "Alp", "Aql"),
    TrainingStarIdentity(60718, "Acrux", "Alp-1", "Cru"),
    TrainingStarIdentity(21421, "Aldebaran", "Alp", "Tau"),
    TrainingStarIdentity(65474, "Spica", "Alp", "Vir"),
    TrainingStarIdentity(80763, "Antares", "Alp", "Sco"),
    TrainingStarIdentity(37826, "Pollux", "Bet", "Gem"),
    TrainingStarIdentity(113368, "Fomalhaut", "Alp", "PsA"),
    TrainingStarIdentity(62434, "Mimosa", "Bet", "Cru"),
    TrainingStarIdentity(102098, "Deneb", "Alp", "Cyg"),
    TrainingStarIdentity(49669, "Regulus", "Alp", "Leo"),
    TrainingStarIdentity(33579, "Adhara", "Eps", "CMa"),
    TrainingStarIdentity(36850, "Castor", "Alp", "Gem"),
    TrainingStarIdentity(61084, "Gacrux", "Gam", "Cru"),
    TrainingStarIdentity(85927, "Shaula", "Lam", "Sco"),
    TrainingStarIdentity(25336, "Bellatrix", "Gam", "Ori"),
    TrainingStarIdentity(25428, "Elnath", "Bet", "Tau"),
    TrainingStarIdentity(45238, "Miaplacidus", "Bet", "Car"),
    TrainingStarIdentity(26311, "Alnilam", "Eps", "Ori"),
    TrainingStarIdentity(109268, "Alnair", "Alp", "Gru"),
    TrainingStarIdentity(26727, "Alnitak", "Zet", "Ori"),
    TrainingStarIdentity(39953, "Regor", "Gam-2", "Vel"),
    TrainingStarIdentity(62956, "Alioth", "Eps", "UMa"),
    TrainingStarIdentity(15863, "Mirfak", "Alp", "Per"),
    TrainingStarIdentity(90185, "Kaus Australis", "Eps", "Sgr"),
    TrainingStarIdentity(54061, "Dubhe", "Alp", "UMa"),
    TrainingStarIdentity(34444, "Wezen", "Del", "CMa"),
    TrainingStarIdentity(67301, "Alkaid", "Eta", "UMa"),
    TrainingStarIdentity(41037, "Avior", "Eps", "Car"),
    TrainingStarIdentity(86228, "Sargas", "The", "Sco"),
    TrainingStarIdentity(28360, "Menkalinan", "Bet", "Aur"),
    TrainingStarIdentity(82273, "Atria", "Alp", "TrA"),
    TrainingStarIdentity(42913, "Alsephina", "Del", "Vel"),
    TrainingStarIdentity(31681, "Alhena", "Gam", "Gem"),
    TrainingStarIdentity(100751, "Peacock", "Alp", "Pav"),
    TrainingStarIdentity(11767, "Polaris", "Alp", "UMi"),
    TrainingStarIdentity(30324, "Mirzam", "Bet", "CMa"),
    TrainingStarIdentity(46390, "Alphard", "Alp", "Hya"),
    TrainingStarIdentity(50583, "Algieba", "Gam-1", "Leo"),
    TrainingStarIdentity(9884, "Hamal", "Alp", "Ari"),
    TrainingStarIdentity(3419, "Diphda", "Bet", "Cet"),
    TrainingStarIdentity(92855, "Nunki", "Sig", "Sgr"),
    TrainingStarIdentity(68933, "Menkent", "The", "Cen"),
    TrainingStarIdentity(27366, "Saiph", "Kap", "Ori"),
    TrainingStarIdentity(72607, "Kochab", "Bet", "UMi"),
    TrainingStarIdentity(5447, "Mirach", "Bet", "And"),
    TrainingStarIdentity(677, "Alpheratz", "Alp", "And"),
    TrainingStarIdentity(112122, "Tiaki", "Bet", "Gru"),
    TrainingStarIdentity(86032, "Rasalhague", "Alp", "Oph"),
    TrainingStarIdentity(9640, "Almach", "Gam-1", "And"),
    TrainingStarIdentity(98036, "Alshain", "Bet", "Aql"),
    TrainingStarIdentity(97278, "Tarazed", "Gam", "Aql"),
    TrainingStarIdentity(109074, "Sadalmelik", "Alp", "Aqr"),
    TrainingStarIdentity(106278, "Sadalsuud", "Bet", "Aqr"),
    TrainingStarIdentity(110395, "Sadachbia", "Gam", "Aqr"),
    TrainingStarIdentity(8903, "Sheratan", "Bet", "Ari"),
    TrainingStarIdentity(8832, "Mesarthim", "Gam-2", "Ari"),
    TrainingStarIdentity(100064, "Algedi", "Alp-2", "Cap"),
    TrainingStarIdentity(100345, "Dabih", "Bet", "Cap"),
    TrainingStarIdentity(106985, "Nashira", "Gam", "Cap"),
    TrainingStarIdentity(3179, "Schedar", "Alp", "Cas"),
    TrainingStarIdentity(746, "Caph", "Bet", "Cas"),
    TrainingStarIdentity(4427, "Cih", "Gam", "Cas"),
    TrainingStarIdentity(61932, "Muhlifain", "Gam", "Cen"),
    TrainingStarIdentity(105199, "Alderamin", "Alp", "Cep"),
    TrainingStarIdentity(106032, "Alfirk", "Bet", "Cep"),
    TrainingStarIdentity(116727, "Errai", "Gam", "Cep"),
    TrainingStarIdentity(14135, "Menkar", "Alp", "Cet"),
    TrainingStarIdentity(12706, "Kaffaljidhma", "Gam", "Cet"),
    TrainingStarIdentity(44066, "Acubens", "Alp", "Cnc"),
    TrainingStarIdentity(40526, "Tarf", "Bet", "Cnc"),
    TrainingStarIdentity(42806, "Asellus Borealis", "Gam", "Cnc"),
    TrainingStarIdentity(95947, "Albireo", "Bet-1", "Cyg"),
    TrainingStarIdentity(100453, "Sadr", "Gam", "Cyg"),
    TrainingStarIdentity(57632, "Denebola", "Bet", "Leo"),
    TrainingStarIdentity(72622, "Zubenelgenubi", "Alp-2", "Lib"),
    TrainingStarIdentity(74785, "Zubeneschamali", "Bet", "Lib"),
    TrainingStarIdentity(76333, "Zubenelhakrabi", "Gam", "Lib"),
    TrainingStarIdentity(92420, "Sheliak", "Bet", "Lyr"),
    TrainingStarIdentity(93194, "Sulafat", "Gam", "Lyr"),
    TrainingStarIdentity(86742, "Cebalrai", "Bet", "Oph"),
    TrainingStarIdentity(87108, None, "Gam", "Oph"),
    TrainingStarIdentity(113963, "Markab", "Alp", "Peg"),
    TrainingStarIdentity(113881, "Scheat", "Bet", "Peg"),
    TrainingStarIdentity(1067, "Algenib", "Gam", "Peg"),
    TrainingStarIdentity(14576, "Algol", "Bet", "Per"),
    TrainingStarIdentity(14328, None, "Gam", "Per"),
    TrainingStarIdentity(2081, "Ankaa", "Alp", "Phe"),
    TrainingStarIdentity(5165, None, "Bet", "Phe"),
    TrainingStarIdentity(6867, None, "Gam", "Phe"),
    TrainingStarIdentity(111188, None, "Bet", "PsA"),
    TrainingStarIdentity(112948, None, "Gam", "PsA"),
    TrainingStarIdentity(9487, "Alrescha", "Alp", "Psc"),
    TrainingStarIdentity(113889, "Fumalsamakah", "Bet", "Psc"),
    TrainingStarIdentity(114971, None, "Gam", "Psc"),
    TrainingStarIdentity(78820, "Acrab", "Bet-1", "Sco"),
    # Modern boundaries leave Scorpius without Gamma; bright Delta Scorpii is
    # included instead as the familiar next Bayer star.
    TrainingStarIdentity(78401, "Dschubba", "Del", "Sco"),
    TrainingStarIdentity(95347, "Rukbat", "Alp", "Sgr"),
    TrainingStarIdentity(95241, "Arkab Prior", "Bet-1", "Sgr"),
    TrainingStarIdentity(88635, "Alnasl", "Gam-2", "Sgr"),
    TrainingStarIdentity(20205, "Prima Hyadum", "Gam", "Tau"),
    TrainingStarIdentity(53910, "Merak", "Bet", "UMa"),
    TrainingStarIdentity(58001, "Phecda", "Gam", "UMa"),
    TrainingStarIdentity(75097, "Pherkad", "Gam", "UMi"),
    TrainingStarIdentity(57757, "Zavijava", "Bet", "Vir"),
    TrainingStarIdentity(61941, "Porrima", "Gam", "Vir"),
)

TRAINING_STAR_BY_HIP = {star.hip: star for star in TRAINING_STAR_IDENTITIES}
TOP_60_STARS = tuple(TRAINING_STAR_BY_HIP[hip] for hip in TOP_60_HIP_IDS)
HARD_MODE_STARS = TRAINING_STAR_IDENTITIES

# Shared selector for exercises that test named stars. Add future pools here.
STAR_SET_CHOICES = (("top_60", "Top 60"), ("extended", "Extended"))
STAR_SETS = {"top_60": TOP_60_STARS, "extended": HARD_MODE_STARS}

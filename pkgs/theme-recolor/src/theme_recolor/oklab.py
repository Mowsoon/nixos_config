import math
import re
from dataclasses import dataclass

from theme_recolor.errors import FormatError

Rgb = tuple[float, float, float]

HEX = re.compile(r"[0-9a-fA-F]{6}|[0-9a-fA-F]{3}")
GAMUT_TOLERANCE = 1e-4


@dataclass(frozen=True, slots=True)
class Lab:
    lightness: float
    a: float
    b: float

    @property
    def chroma(self) -> float:
        return math.hypot(self.a, self.b)

    @property
    def hue(self) -> float:
        return math.atan2(self.b, self.a)

    def mix(self, other: "Lab", weight: float) -> "Lab":
        return Lab(
            self.lightness + (other.lightness - self.lightness) * weight,
            self.a + (other.a - self.a) * weight,
            self.b + (other.b - self.b) * weight,
        )


def parse_hex(text: str) -> Rgb:
    digits = text.removeprefix("#")
    if not HEX.fullmatch(digits):
        raise FormatError(f"invalid hex colour {text!r}")
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    return (
        int(digits[0:2], 16) / 255,
        int(digits[2:4], 16) / 255,
        int(digits[4:6], 16) / 255,
    )


def to_bytes(rgb: Rgb) -> tuple[int, int, int]:
    r, g, b = (round(min(1.0, max(0.0, c)) * 255) for c in rgb)
    return r, g, b


def format_hex(rgb: Rgb) -> str:
    r, g, b = to_bytes(rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gamma(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * math.copysign(abs(c) ** (1 / 2.4), c) - 0.055


def to_lab(rgb: Rgb) -> Lab:
    r, g, b = (_linear(c) for c in rgb)
    lc = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    mc = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    sc = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return Lab(
        0.2104542553 * lc + 0.7936177850 * mc - 0.0040720468 * sc,
        1.9779984951 * lc - 2.4285922050 * mc + 0.4505937099 * sc,
        0.0259040371 * lc + 0.7827717662 * mc - 0.8086757660 * sc,
    )


def from_lab(lab: Lab) -> Rgb:
    lc = (lab.lightness + 0.3963377774 * lab.a + 0.2158037573 * lab.b) ** 3
    mc = (lab.lightness - 0.1055613458 * lab.a - 0.0638541728 * lab.b) ** 3
    sc = (lab.lightness - 0.0894841775 * lab.a - 1.2914855480 * lab.b) ** 3
    return (
        _gamma(4.0767416621 * lc - 3.3077115913 * mc + 0.2309699292 * sc),
        _gamma(-1.2684380046 * lc + 2.6097574011 * mc - 0.3413193965 * sc),
        _gamma(-0.0041960863 * lc - 0.7034186147 * mc + 1.7076147010 * sc),
    )


def in_gamut(rgb: Rgb) -> bool:
    return all(-GAMUT_TOLERANCE <= c <= 1 + GAMUT_TOLERANCE for c in rgb)


def polar(lightness: float, chroma: float, hue: float) -> Lab:
    return Lab(lightness, chroma * math.cos(hue), chroma * math.sin(hue))

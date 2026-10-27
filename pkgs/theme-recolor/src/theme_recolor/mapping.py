import colorsys
from collections.abc import Mapping
from dataclasses import dataclass

from theme_recolor.errors import PaletteError
from theme_recolor.oklab import Lab, Rgb, from_lab, in_gamut, parse_hex, polar, to_lab

SLOTS = tuple(f"base0{digit}" for digit in "0123456789ABCDEF")
NEUTRAL_SLOTS = SLOTS[:8]
HUE_BANDS = (
    (15.0, "red"),
    (36.0, "orange"),
    (70.0, "yellow"),
    (165.0, "green"),
    (195.0, "cyan"),
    (260.0, "blue"),
    (320.0, "purple"),
    (345.0, "pink"),
    (360.0, "red"),
)
DEFAULT_ROLES = {
    "red": "base08",
    "orange": "base09",
    "yellow": "base0A",
    "green": "base0B",
    "cyan": "base0C",
    "blue": "base0D",
    "purple": "base0E",
    "pink": "base0E",
    "brown": "base0F",
}
NEUTRAL_CHROMA = 0.035
BLEND_START = 0.02
BLEND_WIDTH = 0.03
CHROMA_RATIO_CAP = 1.6
GAMUT_STEP = 0.95
MIN_CHROMA = 0.001


@dataclass(frozen=True, slots=True)
class Palette:
    slots: Mapping[str, Lab]

    @classmethod
    def from_hex(cls, colors: Mapping[str, str]) -> "Palette":
        missing = [slot for slot in SLOTS if slot not in colors]
        if missing:
            raise PaletteError(f"palette lacks {', '.join(missing)}")
        return cls({slot: to_lab(parse_hex(colors[slot])) for slot in SLOTS})

    def neutral_at(self, lightness: float) -> Lab:
        ramp = [self.slots[slot] for slot in NEUTRAL_SLOTS]
        if lightness <= ramp[0].lightness:
            return ramp[0]
        for low, high in zip(ramp, ramp[1:], strict=False):
            if lightness <= high.lightness:
                span = high.lightness - low.lightness
                weight = (lightness - low.lightness) / span if span else 1.0
                return low.mix(high, weight)
        return ramp[-1]

    def nearest_neutral(self, lightness: float) -> str:
        return min(NEUTRAL_SLOTS, key=lambda slot: abs(self.slots[slot].lightness - lightness))


def family(rgb: Rgb) -> str:
    hue, lightness, saturation = colorsys.rgb_to_hls(*rgb)
    degrees = hue * 360
    name = next(band for limit, band in HUE_BANDS if degrees < limit)
    if name in {"red", "orange", "yellow"} and lightness < 0.45 and saturation < 0.55:
        return "brown"
    return name


def is_neutral(lab: Lab) -> bool:
    return lab.chroma < NEUTRAL_CHROMA


def chromatic_weight(lab: Lab) -> float:
    return min(1.0, max(0.0, (lab.chroma - BLEND_START) / BLEND_WIDTH))


def fit_gamut(lightness: float, chroma: float, hue: float) -> Lab:
    lab = polar(lightness, chroma, hue)
    while not in_gamut(from_lab(lab)) and chroma > MIN_CHROMA:
        chroma *= GAMUT_STEP
        lab = polar(lightness, chroma, hue)
    return lab

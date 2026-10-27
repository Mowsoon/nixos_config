from collections.abc import Mapping
from dataclasses import dataclass

from theme_recolor.errors import PaletteError
from theme_recolor.mapping import (
    CHROMA_RATIO_CAP,
    DEFAULT_ROLES,
    SLOTS,
    Palette,
    chromatic_weight,
    family,
    fit_gamut,
    is_neutral,
)
from theme_recolor.oklab import Rgb, from_lab, parse_hex, to_lab


@dataclass(frozen=True, slots=True)
class Recolor:
    palette: Palette
    roles: Mapping[str, str]
    reference_chroma: Mapping[str, float]

    def role_of(self, rgb: Rgb) -> str:
        lab = to_lab(rgb)
        if is_neutral(lab):
            return self.palette.nearest_neutral(lab.lightness)
        return self.roles[family(rgb)]

    def apply(self, rgb: Rgb) -> Rgb:
        lab = to_lab(rgb)
        darkest = self.palette.slots["base00"].lightness
        if lab.lightness < darkest:
            return rgb
        lightness = min(lab.lightness, self.palette.slots["base07"].lightness)
        neutral = self.palette.neutral_at(lightness)
        weight = chromatic_weight(lab)
        if weight == 0:
            return from_lab(neutral)
        name = family(rgb)
        role = self.palette.slots[self.roles[name]]
        reference = self.reference_chroma.get(name) or lab.chroma
        chroma = role.chroma * min(CHROMA_RATIO_CAP, lab.chroma / reference)
        colored = fit_gamut(lightness, chroma, role.hue)
        return from_lab(neutral.mix(colored, weight))


def resolve_roles(overrides: Mapping[str, str]) -> dict[str, str]:
    unknown = [name for name in overrides if name not in DEFAULT_ROLES]
    if unknown:
        raise PaletteError(f"unknown colour family {', '.join(sorted(unknown))}")
    invalid = [slot for slot in overrides.values() if slot not in SLOTS]
    if invalid:
        raise PaletteError(f"unknown palette slot {', '.join(sorted(invalid))}")
    return DEFAULT_ROLES | dict(overrides)


def reference_chroma(counts: Mapping[str, int]) -> dict[str, float]:
    best: dict[str, tuple[int, float]] = {}
    for text, count in counts.items():
        rgb = parse_hex(text)
        lab = to_lab(rgb)
        if is_neutral(lab):
            continue
        name = family(rgb)
        if count > best.get(name, (0, 0.0))[0]:
            best[name] = (count, lab.chroma)
    return {name: chroma for name, (_, chroma) in best.items()}


def build(palette: Palette, counts: Mapping[str, int], overrides: Mapping[str, str]) -> Recolor:
    return Recolor(palette, resolve_roles(overrides), reference_chroma(counts))

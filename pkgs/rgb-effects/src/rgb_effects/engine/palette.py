from dataclasses import dataclass

import numpy as np

from rgb_effects.color import Color
from rgb_effects.engine.oklab import Floats

WARMTH = 0.5
DARK_SCALE = 0.3
EMBER_HOT = (1.0, 0.94, 0.82)
EMBER_WARM = (1.0, 0.48, 0.1)
EMBER_COLD = (0.63, 0.09, 0.0)
PHYSICS = frozenset({"hot", "warm", "cold", "glow"})
MIN_TABLE_SIZE = 6
MAX_TABLE_SIZE = 8


@dataclass(frozen=True, slots=True)
class PaletteInputs:
    hue: Color
    ceiling: float
    physics_ceiling: float
    window: Color | None
    accent: Color | None


@dataclass(frozen=True, slots=True, eq=False)
class Palette:
    dark: Floats
    primary: Floats
    blend: Floats
    secondary: Floats
    hot: Floats
    warm: Floats
    cold: Floats
    glow: Floats
    table: Floats

    def gradient(self, values: Floats) -> Floats:
        stops = np.stack([self.dark, self.primary, self.blend, self.secondary])
        position = np.clip(values, 0.0, 1.0) * (len(stops) - 1)
        lower = np.minimum(position.astype(np.intp), len(stops) - 2)
        weight = (position - lower)[..., None]
        return (stops[lower] * (1 - weight) + stops[lower + 1] * weight).astype(np.float32)


def _unit(color: Color) -> Floats:
    return np.array([color.red, color.green, color.blue], dtype=np.float32) / 255.0


def _rotated(color: Floats) -> Floats:
    return np.roll(color, 1).astype(np.float32)


def _envelope(colors: Floats, hue: Color, ceiling: float) -> Floats:
    tint = _unit(hue)
    peak = float(tint.max())
    balance = tint / peak if peak > 0 else np.ones(3, dtype=np.float32)
    warmed = colors * (1 - WARMTH + WARMTH * balance)
    return (warmed * ceiling).astype(np.float32)


def _ordered(named: dict[str, Floats], size: int) -> Floats:
    order = ["black", "primary", "secondary", "hot", "dark", "cold", "glow", "warm"]
    return np.stack([named[name] for name in order[:size]]).astype(np.float32)


def build_palette(inputs: PaletteInputs, size: int) -> Palette:
    if not MIN_TABLE_SIZE <= size <= MAX_TABLE_SIZE:
        raise ValueError(f"palette size {size} is outside 6..8")
    primary = _unit(inputs.window) if inputs.window is not None else _unit(inputs.hue)
    secondary = _unit(inputs.accent) if inputs.accent is not None else _rotated(primary)
    raw = {
        "black": np.zeros(3, dtype=np.float32),
        "dark": primary * DARK_SCALE,
        "primary": primary,
        "blend": (primary + secondary) / 2,
        "secondary": secondary,
        "hot": np.array(EMBER_HOT, dtype=np.float32),
        "warm": np.array(EMBER_WARM, dtype=np.float32),
        "cold": np.array(EMBER_COLD, dtype=np.float32),
        "glow": secondary,
    }
    physics = max(inputs.ceiling, inputs.physics_ceiling)
    named = {
        name: _envelope(color, inputs.hue, physics if name in PHYSICS else inputs.ceiling)
        for name, color in raw.items()
    }
    return Palette(
        dark=named["dark"],
        primary=named["primary"],
        blend=named["blend"],
        secondary=named["secondary"],
        hot=named["hot"],
        warm=named["warm"],
        cold=named["cold"],
        glow=named["glow"],
        table=_ordered(named, size),
    )

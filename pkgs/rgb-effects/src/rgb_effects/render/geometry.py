from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from rgb_effects.render.oklab import Floats

Indices = NDArray[np.intp]


@dataclass(frozen=True, slots=True)
class KeyboardLayout:
    led_names: tuple[str, ...]
    matrix: tuple[tuple[int | None, ...], ...]


@dataclass(frozen=True, slots=True, eq=False)
class Geometry:
    shape: tuple[int, int]
    led_count: int
    sample_rows: Indices
    sample_cols: Indices
    logo: NDArray[np.bool_]
    led_names: tuple[str, ...]

    def cell_of(self, led: int) -> tuple[int, int]:
        return int(self.sample_rows[led]), int(self.sample_cols[led])

    def sample(self, field: Floats, logo_color: Floats) -> Floats:
        leds = field[self.sample_rows, self.sample_cols].astype(np.float32)
        leds[self.logo] = logo_color
        return leds


def _extra_position(name: str, rows: int, cols: int) -> tuple[int, int]:
    if name.startswith("G") and name[1:].isdigit():
        return (int(name[1:]) - 1) % rows, 0
    return 0, cols - 1


def build_geometry(layout: KeyboardLayout) -> Geometry:
    rows = len(layout.matrix)
    cols = max((len(row) for row in layout.matrix), default=0)
    if rows == 0 or cols == 0:
        raise ValueError("keyboard layout has an empty matrix")
    count = len(layout.led_names)
    sample_rows = np.zeros(count, dtype=np.intp)
    sample_cols = np.zeros(count, dtype=np.intp)
    placed = np.zeros(count, dtype=np.bool_)
    for row, cells in enumerate(layout.matrix):
        for col, led in enumerate(cells):
            if led is not None and 0 <= led < count:
                sample_rows[led], sample_cols[led], placed[led] = row, col, True
    for led in np.flatnonzero(~placed):
        sample_rows[led], sample_cols[led] = _extra_position(layout.led_names[led], rows, cols)
    logo = np.array([name == "Logo" for name in layout.led_names], dtype=np.bool_)
    return Geometry((rows, cols), count, sample_rows, sample_cols, logo, layout.led_names)

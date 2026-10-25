import numpy as np
from numpy.typing import NDArray

from rgb_effects.color import Color
from rgb_effects.render.oklab import Floats

CENTERS = 4
ITERATIONS = 6
EDGE_DEPTH = 4
FRESH_SECONDS = 1.0
SMOOTHING = 0.5


def _bins(strip: Floats, count: int, axis: int) -> Floats:
    parts = np.array_split(strip, count, axis=axis)
    return np.stack([part.mean(axis=(0, 1)) for part in parts]).astype(np.float32)


def edge_ring(frame: Floats, shape: tuple[int, int]) -> Floats:
    rows, cols = shape
    ring = np.zeros((rows, cols, 3), dtype=np.float32)
    ring[0] = _bins(frame[:EDGE_DEPTH], cols, axis=1)
    ring[-1] = _bins(frame[-EDGE_DEPTH:], cols, axis=1)
    ring[:, 0] = _bins(frame[:, :EDGE_DEPTH], rows, axis=0)
    ring[:, -1] = _bins(frame[:, -EDGE_DEPTH:], rows, axis=0)
    return ring


def ring_mask(shape: tuple[int, int]) -> NDArray[np.bool_]:
    mask = np.zeros(shape, dtype=np.bool_)
    mask[0, :] = mask[-1, :] = mask[:, 0] = mask[:, -1] = True
    return mask


def dominant_colors(pixels: Floats, seeds: Floats | None) -> Floats:
    if seeds is None:
        order = np.argsort(pixels.sum(axis=1))
        seeds = pixels[order[np.linspace(0, len(pixels) - 1, CENTERS).astype(np.intp)]]
    centers = seeds.astype(np.float32).copy()
    for _ in range(ITERATIONS):
        labels = np.linalg.norm(pixels[:, None] - centers[None], axis=2).argmin(axis=1)
        for index in range(CENTERS):
            members = pixels[labels == index]
            if len(members):
                centers[index] = members.mean(axis=0)
    return centers[np.argsort(centers.sum(axis=1))]


class SceneField:
    def __init__(self, shape: tuple[int, int], palette_seconds: float) -> None:
        self._shape = shape
        self._palette_seconds = palette_seconds
        self._ring: Floats | None = None
        self._centers: Floats | None = None
        self._last_frame: float | None = None
        self._last_palette: float | None = None

    def update(self, frame: NDArray[np.uint8], now: float) -> None:
        image = frame.astype(np.float32) / 255.0
        ring = edge_ring(image, self._shape)
        self._ring = ring if self._ring is None else self._ring * SMOOTHING + ring * (1 - SMOOTHING)
        self._last_frame = now
        due = self._last_palette is None or now - self._last_palette >= self._palette_seconds
        if due:
            self._centers = dominant_colors(image.reshape(-1, 3), self._centers)
            self._last_palette = now

    def active(self, now: float) -> bool:
        return self._last_frame is not None and now - self._last_frame < FRESH_SECONDS

    def ring(self) -> Floats | None:
        return self._ring

    def colors(self) -> tuple[Color, ...] | None:
        if self._centers is None:
            return None
        values = np.clip(np.rint(self._centers * 255), 0, 255).astype(np.int64)
        return tuple(Color(int(r), int(g), int(b)) for r, g, b in values)

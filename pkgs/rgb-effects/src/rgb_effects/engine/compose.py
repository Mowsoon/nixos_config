from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from rgb_effects.color import Color
from rgb_effects.engine.activity import Activity
from rgb_effects.engine.background import Background
from rgb_effects.engine.budget import select_changes
from rgb_effects.engine.geometry import Geometry
from rgb_effects.engine.hud import Hud, Overlay
from rgb_effects.engine.oklab import Floats, to_oklab
from rgb_effects.engine.palette import Palette, PaletteInputs, build_palette
from rgb_effects.engine.physics import Physics
from rgb_effects.engine.quantize import UNKNOWN, Indices, nearest

PRIORITY_BACKGROUND = 0
PRIORITY_PHYSICS = 1
PRIORITY_HUD = 2
BASE_SLOTS = 4
PULSE_LEVEL = 0.6
EMISSION_THRESHOLD = 0.05


@dataclass(frozen=True, slots=True)
class EngineSettings:
    palette_size: int
    sleep_seconds: float
    falling_rate: float
    hysteresis: float = 0.04


@dataclass(frozen=True, slots=True)
class FrameRequest:
    now: float
    minute_of_day: float
    inputs: PaletteInputs
    max_packets: int
    brightness_cap: float | None


def capped(colors: Floats, ceiling: float | None) -> Floats:
    if ceiling is None:
        return colors
    peak = colors.max(axis=-1, keepdims=True)
    scale = np.where(peak > ceiling, ceiling / np.maximum(peak, 1e-6), 1.0)
    return (colors * scale).astype(np.float32)


def hud_table(table: Floats, overlay: Overlay) -> Floats:
    result = (table * overlay.dim).astype(np.float32)
    if not overlay.cells:
        return result
    colors = np.unique(np.stack(list(overlay.cells.values())), axis=0)
    room = len(table) - BASE_SLOTS
    used = colors[:room]
    result[BASE_SLOTS : BASE_SLOTS + len(used)] = used
    return result


def to_bytes(colors: Floats) -> NDArray[np.uint8]:
    return np.clip(np.rint(colors * 255), 0, 255).astype(np.uint8)


def to_colors(values: NDArray[np.uint8]) -> tuple[Color, ...]:
    return tuple(Color(int(r), int(g), int(b)) for r, g, b in values)


class Engine:
    def __init__(
        self,
        geometry: Geometry,
        background: Background,
        physics: Physics,
        activity: Activity,
        hud: Hud,
        settings: EngineSettings,
    ) -> None:
        self._geometry = geometry
        self._background = background
        self._physics = physics
        self._hud = hud
        self._activity = activity
        self._settings = settings
        self._shown = np.full(geometry.led_count, UNKNOWN, dtype=np.intp)
        self._sent: NDArray[np.uint8] | None = None
        self._stepped: float | None = None

    def key_pressed(self, led: int | None, now: float) -> None:
        falling = self._activity.rate(now) < self._settings.falling_rate
        self._activity.record(now)
        if led is None or not 0 <= led < self._geometry.led_count:
            return
        row, col = self._geometry.cell_of(led)
        self._physics.press(row, col, now, falling)

    @property
    def hud(self) -> Hud:
        return self._hud

    def enter(self) -> None:
        self._physics.enter()

    def pulse(self, now: float) -> None:
        self._activity.record(now)
        self._physics.pulse(PULSE_LEVEL)

    def awake(self, now: float) -> bool:
        recent = self._activity.idle_for(now) < self._settings.sleep_seconds
        return recent or self._hud.active(now)

    def frame(self, request: FrameRequest) -> tuple[Color, ...]:
        palette = build_palette(request.inputs, self._settings.palette_size)
        self._advance(request.now)
        desired, priority = self._desired(palette)
        overlay = self._hud.overlay(request.now, request.minute_of_day)
        table = palette.table
        if overlay is not None:
            desired, priority = self._overlaid(desired, priority, overlay)
            table = hud_table(table, overlay)
        table = capped(table, request.brightness_cap)
        sent = self._schedule(capped(desired, request.brightness_cap), priority, table, request)
        return to_colors(sent)

    def _overlaid(
        self, desired: Floats, priority: Indices, overlay: Overlay
    ) -> tuple[Floats, Indices]:
        desired = desired * overlay.dim
        priority = priority.copy()
        for led, color in overlay.cells.items():
            desired[led] = color
            priority[led] = PRIORITY_HUD
        return desired.astype(np.float32), priority

    def _advance(self, now: float) -> None:
        elapsed = 0.0 if self._stepped is None else now - self._stepped
        self._stepped = now
        self._background.advance(now, self._activity.rate(now), self._activity.idle_for(now))
        self._physics.step(elapsed, now)

    def _desired(self, palette: Palette) -> tuple[Floats, Indices]:
        geometry = self._geometry
        background = geometry.sample(self._background.field(palette), palette.primary)
        light = self._physics.emission(palette.hot, palette.warm, palette.cold, palette.glow)
        emitted = light[geometry.sample_rows, geometry.sample_cols]
        lit = emitted.max(axis=1) > EMISSION_THRESHOLD
        priority = np.where(lit, PRIORITY_PHYSICS, PRIORITY_BACKGROUND).astype(np.intp)
        return np.maximum(background, emitted).astype(np.float32), priority

    def _schedule(
        self, desired: Floats, priority: Indices, table: Floats, request: FrameRequest
    ) -> NDArray[np.uint8]:
        lab = to_oklab(desired)
        targets = nearest(lab, to_oklab(table), self._shown, self._settings.hysteresis)
        wanted = to_bytes(table[targets])
        if self._sent is None:
            self._sent, self._shown = wanted, targets
            return wanted.copy()
        changed = np.flatnonzero((wanted != self._sent).any(axis=1))
        _, colors = np.unique(wanted, axis=0, return_inverse=True)
        sent_lab = to_oklab(self._sent.astype(np.float32) / 255)
        error = np.linalg.norm(lab - sent_lab, axis=1).astype(np.float32)
        chosen = select_changes(changed, colors.ravel(), priority, error, request.max_packets)
        self._sent[chosen] = wanted[chosen]
        self._shown[chosen] = targets[chosen]
        return self._sent.copy()

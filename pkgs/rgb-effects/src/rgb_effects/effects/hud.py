import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np

from rgb_effects.color import Color
from rgb_effects.render.oklab import Floats

LEFT_CTRL, RIGHT_CTRL = 29, 97
LEFT_ALT, RIGHT_ALT = 56, 100
LEFT_META, RIGHT_META = 125, 126
MODIFIER_NAMES: Mapping[int, str] = MappingProxyType(
    {
        LEFT_CTRL: "ctrl",
        RIGHT_CTRL: "ctrl",
        LEFT_ALT: "alt",
        RIGHT_ALT: "alt",
        LEFT_META: "super",
        RIGHT_META: "super",
    }
)
MODIFIER_ORDER = ("ctrl", "alt", "super")
FOCUS_KEYS = tuple(f"F{index}" for index in range(1, 13))
HOUR_KEYS = ("F1", "F2", "F3", "F4", "F5")
MINUTE_KEYS = ("&", "é", '"', "'", "(", "-")
FOCUS_CATEGORY = "focus"
CLOCK_CATEGORY = "clock"
DONE_SECONDS = 3.0
DONE_BLINKS_PER_SECOND = 2.0
REMAINING_SCALE = 0.15


@dataclass(frozen=True, slots=True)
class HudSettings:
    bindings: Mapping[str, Mapping[str, tuple[str, ...]]]
    colors: Mapping[str, Color]
    dim: float
    clock_hold_seconds: float


@dataclass(frozen=True, slots=True)
class Overlay:
    dim: float
    cells: Mapping[int, Floats]


@dataclass(slots=True)
class HudState:
    held: set[int] = field(default_factory=set)
    clock_since: float | None = None
    focus_start: float | None = None
    focus_seconds: float = 0.0


def _unit(color: Color) -> Floats:
    return np.array([color.red, color.green, color.blue], dtype=np.float32) / 255.0


def combo(held: set[int]) -> str:
    names = {MODIFIER_NAMES[code] for code in held if code in MODIFIER_NAMES}
    return "+".join(name for name in MODIFIER_ORDER if name in names)


def bits(value: int, width: int) -> tuple[bool, ...]:
    return tuple(bool(value >> shift & 1) for shift in range(width - 1, -1, -1))


class Hud:
    def __init__(self, settings: HudSettings, led_names: Sequence[str]) -> None:
        self._settings = settings
        index: dict[str, int] = {}
        for position, name in enumerate(led_names):
            index.setdefault(name.removeprefix("Key: "), position)
        self._index = MappingProxyType(index)
        self._state = HudState()

    def key_down(self, code: int, now: float) -> None:
        self._state.held.add(code)
        alone = code == RIGHT_CTRL and self._state.held == {RIGHT_CTRL}
        self._state.clock_since = now if alone else None

    def key_up(self, code: int) -> None:
        self._state.held.discard(code)
        if code == RIGHT_CTRL:
            self._state.clock_since = None

    def start_focus(self, seconds: float, now: float) -> None:
        self._state.focus_start, self._state.focus_seconds = now, seconds

    def stop_focus(self) -> None:
        self._state.focus_start = None

    def active(self, now: float) -> bool:
        return bool(combo(self._state.held)) or self._state.focus_start is not None

    def overlay(self, now: float, minute_of_day: float) -> Overlay | None:
        cells: dict[int, Floats] = {}
        mask = combo(self._state.held)
        cells.update(self._bindings(mask))
        cells.update(self._focus(now))
        cells.update(self._clock(now, minute_of_day))
        if not mask and not cells:
            return None
        return Overlay(self._settings.dim if mask else 1.0, MappingProxyType(cells))

    def _paint(self, names: Sequence[str], category: str) -> dict[int, Floats]:
        color = self._settings.colors.get(category)
        if color is None:
            return {}
        return {self._index[name]: _unit(color) for name in names if name in self._index}

    def _bindings(self, mask: str) -> dict[int, Floats]:
        cells: dict[int, Floats] = {}
        for category, names in self._settings.bindings.get(mask, {}).items():
            cells.update(self._paint(names, category))
        return cells

    def _focus(self, now: float) -> dict[int, Floats]:
        state = self._state
        if state.focus_start is None:
            return {}
        elapsed = now - state.focus_start
        if elapsed >= state.focus_seconds + DONE_SECONDS:
            state.focus_start = None
            return {}
        if elapsed >= state.focus_seconds:
            lit = math.floor((elapsed - state.focus_seconds) * DONE_BLINKS_PER_SECOND * 2) % 2 == 0
            return self._paint(FOCUS_KEYS if lit else (), FOCUS_CATEGORY)
        return self._progress(elapsed / max(state.focus_seconds, 1e-6))

    def _progress(self, fraction: float) -> dict[int, Floats]:
        done = math.ceil(fraction * len(FOCUS_KEYS))
        cells = self._paint(FOCUS_KEYS[:done], FOCUS_CATEGORY)
        remaining = self._paint(FOCUS_KEYS[done:], FOCUS_CATEGORY)
        cells.update({led: color * REMAINING_SCALE for led, color in remaining.items()})
        return cells

    def _clock(self, now: float, minute_of_day: float) -> dict[int, Floats]:
        since = self._state.clock_since
        if since is None or now - since < self._settings.clock_hold_seconds:
            return {}
        hours, minutes = divmod(int(minute_of_day) % 1440, 60)
        lit = [n for n, on in zip(HOUR_KEYS, bits(hours, len(HOUR_KEYS)), strict=True) if on]
        lit += [n for n, on in zip(MINUTE_KEYS, bits(minutes, len(MINUTE_KEYS)), strict=True) if on]
        dark = {
            led: np.zeros(3, dtype=np.float32)
            for led in self._paint(HOUR_KEYS + MINUTE_KEYS, CLOCK_CATEGORY)
        }
        dark.update(self._paint(lit, CLOCK_CATEGORY))
        return dark

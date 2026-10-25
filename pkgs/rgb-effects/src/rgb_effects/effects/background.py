from dataclasses import dataclass

import numpy as np

from rgb_effects.render.noise import GradientNoise
from rgb_effects.render.oklab import Floats
from rgb_effects.render.palette import Palette

OFF, ON, DYING = 0, 1, 2


@dataclass(frozen=True, slots=True)
class BackgroundSettings:
    idle_seconds: float
    scale: float = 0.18
    base_speed: float = 0.08
    activity_gain: float = 0.5
    automaton_period: float = 1 / 3
    fade_in_seconds: float = 3.0
    fade_out_seconds: float = 0.5
    seed_threshold: float = 0.65
    reseed_steps: int = 200


class Automaton:
    def __init__(self, shape: tuple[int, int]) -> None:
        self.cells = np.zeros(shape, dtype=np.int8)
        self.steps = 0

    def seed(self, values: Floats, threshold: float) -> None:
        self.cells = np.where(values > threshold, ON, OFF).astype(np.int8)
        self.steps = 0

    def step(self) -> None:
        on = (self.cells == ON).astype(np.int8)
        neighbours = sum(
            np.roll(np.roll(on, dr, axis=0), dc, axis=1)
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if (dr, dc) != (0, 0)
        )
        born = (self.cells == OFF) & (neighbours == 2)
        dying = self.cells == ON
        self.cells = np.where(born, ON, np.where(dying, DYING, OFF)).astype(np.int8)
        self.steps += 1

    @property
    def extinct(self) -> bool:
        return not bool((self.cells == ON).any())


class Background:
    def __init__(self, shape: tuple[int, int], settings: BackgroundSettings, seed: int) -> None:
        self._settings = settings
        self._noise = GradientNoise(seed)
        self._xs = np.arange(shape[1], dtype=np.float64) * settings.scale
        self._ys = np.arange(shape[0], dtype=np.float64) * settings.scale
        self._depth = 0.0
        self._mix = 0.0
        self._last: float | None = None
        self._next_step = 0.0
        self._automaton = Automaton(shape)

    @property
    def mix(self) -> float:
        return self._mix

    def advance(self, now: float, rate: float, idle_seconds: float) -> None:
        elapsed = 0.0 if self._last is None else max(0.0, now - self._last)
        self._last = now
        speed = self._settings.base_speed * (1 + self._settings.activity_gain * rate)
        self._depth += speed * elapsed
        self._fade(elapsed, idle_seconds >= self._settings.idle_seconds)
        if self._mix > 0 and now >= self._next_step:
            self._step_automaton()
            self._next_step = now + self._settings.automaton_period

    def field(self, palette: Palette) -> Floats:
        flowing = palette.gradient(self.values())
        if self._mix <= 0:
            return flowing
        cells = self._automaton.cells
        stack = np.stack([np.zeros(3, dtype=np.float32), palette.secondary, palette.dark])
        automaton = stack[cells]
        return (flowing * (1 - self._mix) + automaton * self._mix).astype(np.float32)

    def values(self) -> Floats:
        noise = self._noise.sample(self._xs, self._ys, self._depth)
        return ((noise + 1) / 2).astype(np.float32)

    def _fade(self, elapsed: float, idle: bool) -> None:
        if idle:
            if self._mix == 0:
                self._automaton.seed(self.values(), self._settings.seed_threshold)
            self._mix = min(1.0, self._mix + elapsed / self._settings.fade_in_seconds)
        else:
            self._mix = max(0.0, self._mix - elapsed / self._settings.fade_out_seconds)

    def _step_automaton(self) -> None:
        if self._automaton.extinct or self._automaton.steps >= self._settings.reseed_steps:
            self._automaton.seed(self.values(), self._settings.seed_threshold)
            return
        self._automaton.step()

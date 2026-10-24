from collections.abc import Sequence

from rgb_effects.color import Color
from rgb_effects.errors import ConfigError

STEP_TOLERANCE = 1e-9


class Ember:
    def __init__(self, palette: Sequence[Color], duration_seconds: float) -> None:
        if not palette:
            raise ConfigError("ember palette is empty")
        if duration_seconds <= 0:
            raise ConfigError("ember duration must be positive")
        self._palette = tuple(palette)
        self._duration = duration_seconds
        self._ignitions: dict[int, float] = {}

    def ignite(self, index: int, now: float) -> None:
        self._ignitions[index] = now

    def ignite_all(self, count: int, now: float, step: int) -> None:
        bounded = min(max(step, 0), len(self._palette) - 1)
        start = now - self._duration * bounded / len(self._palette)
        for index in range(count):
            self._ignitions[index] = max(self._ignitions.get(index, start), start)

    def active(self, now: float) -> bool:
        self._expire(now)
        return bool(self._ignitions)

    def overlay(self, frame: Sequence[Color], now: float) -> tuple[Color, ...]:
        self._expire(now)
        result = list(frame)
        for index, ignited in self._ignitions.items():
            if 0 <= index < len(result):
                result[index] = self._color(now - ignited)
        return tuple(result)

    def _color(self, age: float) -> Color:
        step = int(age / self._duration * len(self._palette) + STEP_TOLERANCE)
        return self._palette[min(max(step, 0), len(self._palette) - 1)]

    def _expire(self, now: float) -> None:
        expired = [i for i, ignited in self._ignitions.items() if now - ignited >= self._duration]
        for index in expired:
            del self._ignitions[index]

from dataclasses import dataclass

import numpy as np

from rgb_effects.audio.analysis import Features
from rgb_effects.engine.oklab import Floats

ATTACK = 0.6
RELEASE = 0.15
FLOOR_DBFS = -60.0
BALANCE_TILT = 0.5
FADE_SECONDS = 2.0
TONAL_SMOOTHING = 0.007
TONAL_CLARITY_GAIN = 3.0
FIFTHS = np.exp(1j * np.deg2rad((np.arange(12) * 7 % 12) * 30.0))


@dataclass(frozen=True, slots=True)
class SoundSettings:
    spectrum_gain: float
    silence_seconds: float
    hue_range: float = 60.0
    speed_gain: float = 4.0


def _smoothed(current: Floats, target: Floats) -> Floats:
    rate = np.where(target > current, ATTACK, RELEASE)
    return (current + (target - current) * rate).astype(np.float32)


def _level(dbfs: float) -> float:
    return float(np.clip((dbfs - FLOOR_DBFS) / -FLOOR_DBFS, 0.0, 1.0))


class SoundField:
    def __init__(self, columns: int, settings: SoundSettings) -> None:
        self._columns = columns
        self._settings = settings
        self._bands = np.zeros(columns, dtype=np.float32)
        self._levels = np.zeros(2, dtype=np.float32)
        self._last_loud: float | None = None
        self._tonal = 0j

    def update(self, features: Features, now: float) -> None:
        source = np.linspace(0.0, 1.0, len(features.bands))
        target = np.interp(np.linspace(0.0, 1.0, self._columns), source, features.bands)
        self._bands = _smoothed(self._bands, target.astype(np.float32))
        levels = np.array([_level(features.left_dbfs), _level(features.right_dbfs)])
        self._levels = _smoothed(self._levels, levels.astype(np.float32))
        if features.loud:
            self._last_loud = now
        if features.chroma is not None and features.loud:
            heading = complex(np.dot(features.chroma, FIFTHS))
            self._tonal += (heading - self._tonal) * TONAL_SMOOTHING

    def active(self, now: float) -> bool:
        return self.quiet_for(now) < self._settings.silence_seconds

    def quiet_for(self, now: float) -> float:
        return float("inf") if self._last_loud is None else max(0.0, now - self._last_loud)

    def envelope(self, now: float) -> float:
        late = self.quiet_for(now) - self._settings.silence_seconds
        return float(np.clip(1.0 - late / FADE_SECONDS, 0.0, 1.0))

    def speed(self, now: float) -> float:
        return self._settings.speed_gain * float(self._levels.mean()) * self.envelope(now)

    def hue_shift(self, now: float) -> float:
        clarity = min(1.0, abs(self._tonal) * TONAL_CLARITY_GAIN)
        direction = float(np.sin(np.angle(self._tonal))) if self._tonal else 0.0
        return self._settings.hue_range * clarity * direction * self.envelope(now)

    def balance(self) -> float:
        left, right = (float(level) for level in self._levels)
        total = left + right
        return 0.0 if total <= 0 else (right - left) / total

    def lift(self, rows: int, now: float) -> tuple[Floats, float]:
        positions = np.linspace(-1.0, 1.0, self._columns)
        tilt = np.clip(1.0 + BALANCE_TILT * self.balance() * positions, 0.0, 2.0)
        heights = np.clip(self._bands * tilt, 0.0, 1.0) * rows
        from_bottom = np.arange(rows - 1, -1, -1, dtype=np.float32)[:, None]
        lit = np.clip(heights[None, :] - from_bottom, 0.0, 1.0).astype(np.float32)
        return lit, self._settings.spectrum_gain * self.envelope(now)

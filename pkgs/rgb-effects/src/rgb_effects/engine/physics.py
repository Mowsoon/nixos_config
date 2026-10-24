import math
from dataclasses import dataclass, field

import numpy as np

from rgb_effects.engine.oklab import Floats

MAX_STEP_SECONDS = 0.1


@dataclass(frozen=True, slots=True)
class PhysicsSettings:
    ember_cold_seconds: float = 0.8
    ember_hot_seconds: float = 2.5
    halo: float = 0.15
    heat_per_press: float = 0.15
    heat_diffusion: float = 0.05
    heat_seconds: float = 180.0
    wave_speed: float = 4.0
    wave_damping: float = 2.5
    wave_hot_reduction: float = 0.7
    particle_fall_seconds: float = 0.15
    sand_per_grain: float = 0.34
    sweep_columns_per_second: float = 42.0
    sweep_strength: float = 0.6


@dataclass(slots=True)
class Particle:
    row: int
    col: int
    next_fall: float


def laplacian(grid: Floats) -> Floats:
    padded = np.pad(grid, 1, mode="edge")
    neighbours = padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
    return (neighbours - 4 * grid).astype(np.float32)


@dataclass(slots=True)
class Fields:
    heat: Floats
    ember: Floats
    wave: Floats
    previous_wave: Floats
    sand: Floats
    particles: list[Particle] = field(default_factory=list)
    sweep_col: float | None = None


def _zeros(shape: tuple[int, int]) -> Floats:
    return np.zeros(shape, dtype=np.float32)


class Physics:
    def __init__(self, shape: tuple[int, int], settings: PhysicsSettings) -> None:
        self._shape = shape
        self._settings = settings
        self._fields = Fields(
            _zeros(shape),
            _zeros(shape),
            _zeros(shape),
            _zeros(shape),
            np.zeros(shape[1], dtype=np.float32),
        )

    @property
    def fields(self) -> Fields:
        return self._fields

    def press(self, row: int, col: int, now: float, falling: bool) -> None:
        if not (0 <= row < self._shape[0] and 0 <= col < self._shape[1]):
            return
        fields = self._fields
        fields.heat[row, col] = min(1.0, fields.heat[row, col] + self._settings.heat_per_press)
        fields.ember[row, col] = 1.0
        fields.wave[row, col] += 1.0
        if falling and row < self._shape[0] - 1:
            fields.particles.append(Particle(row, col, now + self._settings.particle_fall_seconds))

    def pulse(self, level: float) -> None:
        np.maximum(self._fields.ember, level, out=self._fields.ember)

    def enter(self) -> None:
        self._fields.sand[:] = 0.0
        self._fields.particles.clear()
        self._fields.sweep_col = 0.0

    def step(self, elapsed: float, now: float) -> None:
        remaining = max(0.0, elapsed)
        while remaining > 0:
            dt = min(remaining, MAX_STEP_SECONDS)
            self._heat(dt)
            self._ember(dt)
            self._wave(dt)
            self._sweep(dt)
            remaining -= dt
        self._fall(now)

    def _heat(self, dt: float) -> None:
        heat = self._fields.heat
        heat += self._settings.heat_diffusion * laplacian(heat) * dt
        heat *= math.exp(-dt / self._settings.heat_seconds)
        np.clip(heat, 0.0, 1.0, out=heat)

    def _ember(self, dt: float) -> None:
        settings, fields = self._settings, self._fields
        span = settings.ember_hot_seconds - settings.ember_cold_seconds
        lifetime = settings.ember_cold_seconds + span * fields.heat
        fields.ember -= dt / lifetime
        np.maximum(fields.ember, settings.halo * fields.heat, out=fields.ember)
        np.clip(fields.ember, 0.0, 1.0, out=fields.ember)

    def _wave(self, dt: float) -> None:
        settings, fields = self._settings, self._fields
        courant = (settings.wave_speed * dt) ** 2
        damping = settings.wave_damping * (1 - settings.wave_hot_reduction * fields.heat) * dt
        velocity = fields.wave - fields.previous_wave
        following = fields.wave + velocity * (1 - damping) + courant * laplacian(fields.wave)
        fields.previous_wave = fields.wave
        fields.wave = np.clip(following, -2.0, 2.0).astype(np.float32)

    def _sweep(self, dt: float) -> None:
        fields = self._fields
        if fields.sweep_col is None:
            return
        col = int(fields.sweep_col)
        if col >= self._shape[1]:
            fields.sweep_col = None
            return
        fields.wave[self._shape[0] - 1, col] += self._settings.sweep_strength
        fields.sweep_col += self._settings.sweep_columns_per_second * dt

    def _fall(self, now: float) -> None:
        bottom = self._shape[0] - 1
        landed: list[Particle] = []
        for particle in self._fields.particles:
            while particle.next_fall <= now and particle.row < bottom:
                particle.row += 1
                particle.next_fall += self._settings.particle_fall_seconds
            if particle.row >= bottom:
                landed.append(particle)
        for particle in landed:
            self._fields.particles.remove(particle)
            sand = self._fields.sand
            sand[particle.col] = min(1.0, sand[particle.col] + self._settings.sand_per_grain)

    def emission(self, hot: Floats, warm: Floats, cold: Floats, glow: Floats) -> Floats:
        fields = self._fields
        ember = fields.ember[..., None]
        embers = np.where(
            ember > 0.5, _mix(warm, hot, (ember - 0.5) * 2), _mix(cold, warm, ember * 2)
        )
        light = embers * np.minimum(1.0, ember * 3)
        light = np.maximum(light, glow * np.clip(np.abs(fields.wave), 0.0, 1.0)[..., None])
        grains = np.zeros(self._shape, dtype=np.float32)
        grains[-1, :] = fields.sand
        for particle in fields.particles:
            grains[particle.row, particle.col] = 1.0
        light = np.maximum(light, warm * grains[..., None])
        return light.astype(np.float32)


def _mix(low: Floats, high: Floats, weight: Floats) -> Floats:
    return (low * (1 - weight) + high * weight).astype(np.float32)

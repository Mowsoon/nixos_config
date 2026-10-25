from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Floats = NDArray[np.float32]

SAMPLE_RATE = 48000
WINDOW = 4096
LOWEST_HZ = 40.0
HIGHEST_HZ = 16000.0
SILENCE_DBFS = -60.0
PEAK_DECAY_DB = 0.05
DYNAMIC_RANGE_DB = 50.0
PEAK_FLOOR_DB = -70.0
EPSILON = 1e-12
FLUX_HISTORY = 48
ONSET_DEVIATIONS = 2.0
ONSET_MIN_BLOCKS = 7
CHROMA_LOW_HZ = 65.0
CHROMA_HIGH_HZ = 2000.0
PITCH_CLASSES = 12


@dataclass(frozen=True, slots=True, eq=False)
class Features:
    left_dbfs: float
    right_dbfs: float
    bands: Floats
    loud: bool
    onset: float = 0.0
    chroma: Floats | None = None


def dbfs(samples: Floats) -> float:
    rms = float(np.sqrt(np.mean(np.square(samples)) + EPSILON))
    return 20.0 * float(np.log10(rms))


def pitch_classes() -> NDArray[np.intp]:
    frequencies = np.fft.rfftfreq(WINDOW, 1.0 / SAMPLE_RATE)
    valid = (frequencies >= CHROMA_LOW_HZ) & (frequencies <= CHROMA_HIGH_HZ)
    pitches = 12.0 * np.log2(np.maximum(frequencies, EPSILON) / 440.0) + 69.0
    return np.where(valid, np.rint(pitches).astype(np.intp) % PITCH_CLASSES, -1)


def band_edges(count: int) -> NDArray[np.intp]:
    frequencies = np.geomspace(LOWEST_HZ, HIGHEST_HZ, count + 1)
    bins = np.rint(frequencies * WINDOW / SAMPLE_RATE).astype(np.intp)
    return np.maximum.accumulate(np.maximum(bins, np.arange(count + 1) + 1))


class Analyzer:
    def __init__(self, band_count: int) -> None:
        if band_count < 1:
            raise ValueError("band count must be positive")
        self._ring = np.zeros(WINDOW, dtype=np.float32)
        self._window = np.hanning(WINDOW).astype(np.float32)
        self._edges = band_edges(band_count)
        self._peak_db = PEAK_FLOOR_DB
        self._classes = pitch_classes()
        self._previous: Floats | None = None
        self._flux = np.zeros(FLUX_HISTORY, dtype=np.float32)
        self._since_onset = ONSET_MIN_BLOCKS

    def process(self, block: Floats) -> Features:
        if block.ndim != 2 or block.shape[1] != 2 or len(block) == 0:
            raise ValueError("audio block must be a non-empty stereo array")
        left, right = dbfs(block[:, 0]), dbfs(block[:, 1])
        self._push(block.mean(axis=1))
        power = np.abs(np.fft.rfft(self._ring * self._window)) ** 2
        loud = max(left, right) > SILENCE_DBFS
        onset = self._onset(power) if loud else 0.0
        return Features(left, right, self._bands(power), loud, onset, self._chroma(power))

    def _push(self, mono: Floats) -> None:
        count = min(len(mono), WINDOW)
        self._ring = np.roll(self._ring, -count)
        self._ring[-count:] = mono[-count:]

    def _onset(self, power: Floats) -> float:
        magnitude = np.log1p(np.sqrt(power)).astype(np.float32)
        previous, self._previous = self._previous, magnitude
        if previous is None:
            return 0.0
        flux = float(np.maximum(magnitude - previous, 0.0).sum())
        mean, spread = float(self._flux.mean()), float(self._flux.std())
        self._flux = np.roll(self._flux, -1)
        self._flux[-1] = flux
        self._since_onset += 1
        if self._since_onset < ONSET_MIN_BLOCKS or flux <= mean + ONSET_DEVIATIONS * spread:
            return 0.0
        self._since_onset = 0
        return min(1.0, (flux - mean) / max(mean, EPSILON))

    def _chroma(self, power: Floats) -> Floats:
        valid = self._classes >= 0
        chroma = np.bincount(self._classes[valid], weights=power[valid], minlength=PITCH_CLASSES)
        total = float(chroma.sum())
        return (chroma / total if total > 0 else chroma).astype(np.float32)

    def _bands(self, power: Floats) -> Floats:
        energy = np.array(
            [
                power[low:high].mean()
                for low, high in zip(self._edges[:-1], self._edges[1:], strict=True)
            ],
            dtype=np.float32,
        )
        decibels = 10.0 * np.log10(energy + EPSILON)
        self._peak_db = max(self._peak_db - PEAK_DECAY_DB, float(decibels.max()), PEAK_FLOOR_DB)
        floor = self._peak_db - DYNAMIC_RANGE_DB
        return np.clip((decibels - floor) / DYNAMIC_RANGE_DB, 0.0, 1.0).astype(np.float32)

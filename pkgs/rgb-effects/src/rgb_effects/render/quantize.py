import numpy as np
from numpy.typing import NDArray

from rgb_effects.render.oklab import Floats

Indices = NDArray[np.intp]
UNKNOWN = -1


def distances(desired: Floats, table: Floats) -> Floats:
    return np.linalg.norm(desired[:, None, :] - table[None, :, :], axis=2).astype(np.float32)


def nearest(desired: Floats, table: Floats, previous: Indices, hysteresis: float) -> Indices:
    gaps = distances(desired, table)
    best = gaps.argmin(axis=1)
    rows = np.arange(len(desired))
    known = (previous >= 0) & (previous < len(table))
    held = np.where(known, previous, best)
    keep = known & (gaps[rows, held] - gaps[rows, best] < hysteresis)
    return np.where(keep, held, best).astype(np.intp)

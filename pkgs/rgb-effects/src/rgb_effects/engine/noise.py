import numpy as np
from numpy.typing import NDArray

from rgb_effects.engine.oklab import Floats

GRADIENTS = np.array(
    [
        [1, 1, 0],
        [-1, 1, 0],
        [1, -1, 0],
        [-1, -1, 0],
        [1, 0, 1],
        [-1, 0, 1],
        [1, 0, -1],
        [-1, 0, -1],
        [0, 1, 1],
        [0, -1, 1],
        [0, 1, -1],
        [0, -1, -1],
    ],
    dtype=np.float64,
)
TABLE_SIZE = 256
SCALE = 0.95


def _fade(t: NDArray[np.float64]) -> NDArray[np.float64]:
    return t * t * t * (t * (t * 6 - 15) + 10)


class GradientNoise:
    def __init__(self, seed: int) -> None:
        permutation = np.random.default_rng(seed).permutation(TABLE_SIZE)
        self._perm = np.concatenate([permutation, permutation]).astype(np.intp)

    def sample(self, xs: NDArray[np.float64], ys: NDArray[np.float64], z: float) -> Floats:
        x, y = np.meshgrid(xs, ys)
        point = np.stack([x, y, np.full_like(x, z)], axis=-1)
        cell = np.floor(point).astype(np.intp)
        local = point - cell
        cell &= TABLE_SIZE - 1
        weights = _fade(local)
        total = np.zeros(x.shape, dtype=np.float64)
        for corner in np.ndindex(2, 2, 2):
            offset = np.array(corner)
            influence = self._dot(cell + offset, local - offset)
            weight = np.prod(np.where(offset == 1, weights, 1 - weights), axis=-1)
            total += weight * influence
        return np.clip(total * SCALE, -1.0, 1.0).astype(np.float32)

    def _dot(self, corner: NDArray[np.intp], delta: NDArray[np.float64]) -> NDArray[np.float64]:
        perm = self._perm
        hashed = perm[perm[perm[corner[..., 0]] + corner[..., 1]] + corner[..., 2]]
        return np.einsum("...k,...k->...", GRADIENTS[hashed % len(GRADIENTS)], delta)

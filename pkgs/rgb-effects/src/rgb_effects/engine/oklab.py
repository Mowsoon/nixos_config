import numpy as np
from numpy.typing import NDArray

Floats = NDArray[np.float32]

LMS_FROM_LINEAR = np.array(
    [
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005],
    ],
    dtype=np.float32,
)
LAB_FROM_LMS = np.array(
    [
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660],
    ],
    dtype=np.float32,
)


def to_linear(rgb: Floats) -> Floats:
    clipped = np.clip(rgb, 0.0, 1.0)
    curve = np.power((clipped + 0.055) / 1.055, 2.4)
    return np.where(clipped <= 0.04045, clipped / 12.92, curve).astype(np.float32)


def to_oklab(rgb: Floats) -> Floats:
    lms = to_linear(rgb) @ LMS_FROM_LINEAR.T
    return (np.cbrt(lms) @ LAB_FROM_LMS.T).astype(np.float32)

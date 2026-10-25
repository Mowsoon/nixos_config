import numpy as np

from rgb_effects.render.quantize import UNKNOWN, nearest

TABLE = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)


def test_nearest_picks_closest_entry() -> None:
    desired = np.array([[0.9, 0.1, 0.0]], dtype=np.float32)
    previous = np.array([UNKNOWN], dtype=np.intp)
    assert nearest(desired, TABLE, previous, 0.0).tolist() == [1]


def test_nearest_keeps_previous_within_hysteresis() -> None:
    desired = np.array([[0.5, 0.51, 0.0]], dtype=np.float32)
    previous = np.array([1], dtype=np.intp)
    assert nearest(desired, TABLE, previous, 0.1).tolist() == [1]


def test_nearest_switches_beyond_hysteresis() -> None:
    desired = np.array([[0.0, 0.9, 0.0]], dtype=np.float32)
    previous = np.array([1], dtype=np.intp)
    assert nearest(desired, TABLE, previous, 0.1).tolist() == [2]


def test_nearest_ignores_previous_index_outside_the_table() -> None:
    desired = np.array([[0.0, 0.9, 0.0]], dtype=np.float32)
    previous = np.array([7], dtype=np.intp)
    assert nearest(desired, TABLE, previous, 0.1).tolist() == [2]

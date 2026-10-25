from collections import Counter

import numpy as np
import pytest

from rgb_effects.render.budget import packet_cost, select_changes


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        (Counter(), 0),
        (Counter({1: 1}), 2),
        (Counter({1: 1, 2: 1, 3: 1, 4: 1}), 2),
        (Counter({1: 1, 2: 1, 3: 1, 4: 1, 5: 1}), 3),
        (Counter({1: 13}), 2),
        (Counter({1: 14}), 3),
        (Counter({1: 20, 2: 3, 3: 1}), 5),
    ],
)
def test_packet_cost_follows_openrgb_grouping(counts: Counter[int], expected: int) -> None:
    assert packet_cost(counts) == expected


def test_select_changes_keeps_everything_within_budget() -> None:
    changed = np.array([0, 1, 2], dtype=np.intp)
    colors = np.array([1, 1, 2], dtype=np.intp)
    error = np.ones(3, dtype=np.float32)
    priority = np.zeros(3, dtype=np.intp)
    assert select_changes(changed, colors, priority, error, 9).tolist() == [0, 1, 2]


def test_select_changes_prefers_higher_priority() -> None:
    changed = np.arange(5, dtype=np.intp)
    colors = np.arange(1, 6, dtype=np.intp)
    error = np.ones(5, dtype=np.float32)
    priority = np.array([0, 0, 0, 0, 1], dtype=np.intp)
    assert 4 in select_changes(changed, colors, priority, error, 2).tolist()


def test_select_changes_defers_what_exceeds_budget() -> None:
    changed = np.arange(9, dtype=np.intp)
    colors = np.arange(1, 10, dtype=np.intp)
    error = np.ones(9, dtype=np.float32)
    priority = np.zeros(9, dtype=np.intp)
    assert len(select_changes(changed, colors, priority, error, 2)) == 4


def test_select_changes_ignores_unchanged_leds() -> None:
    changed = np.array([2], dtype=np.intp)
    colors = np.array([1, 1, 1], dtype=np.intp)
    error = np.ones(3, dtype=np.float32)
    priority = np.zeros(3, dtype=np.intp)
    assert select_changes(changed, colors, priority, error, 9).tolist() == [2]

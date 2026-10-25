import numpy as np
import pytest

from rgb_effects.effects.scene import SceneField, dominant_colors, edge_ring, ring_mask


def _frame(top: tuple[int, int, int], rest: tuple[int, int, int]) -> np.ndarray:
    frame = np.zeros((36, 64, 3), dtype=np.uint8)
    frame[:] = rest
    frame[:4] = top
    return frame


def test_ring_mask_covers_only_the_outer_keys() -> None:
    mask = ring_mask((6, 21))
    assert int(mask.sum()) == 2 * 21 + 2 * 4 and not mask[2, 10]


def test_edge_ring_takes_the_top_edge_for_the_first_row() -> None:
    ring = edge_ring(_frame((255, 0, 0), (0, 0, 255)).astype(np.float32) / np.float32(255), (6, 21))
    assert ring[0, 10].tolist() == pytest.approx([1.0, 0.0, 0.0])
    assert ring[-1, 10].tolist() == pytest.approx([0.0, 0.0, 1.0])


def test_dominant_colors_find_the_two_halves() -> None:
    pixels = np.concatenate(
        [np.tile([[1.0, 0.0, 0.0]], (100, 1)), np.tile([[0.0, 0.0, 1.0]], (100, 1))]
    ).astype(np.float32)
    centers = dominant_colors(pixels, None)
    found = {tuple(np.round(center, 2)) for center in centers}
    assert (1.0, 0.0, 0.0) in found and (0.0, 0.0, 1.0) in found


def test_scene_is_active_only_while_frames_arrive() -> None:
    scene = SceneField((6, 21), 0.5)
    scene.update(_frame((255, 0, 0), (0, 0, 255)), 10.0)
    assert scene.active(10.5) and not scene.active(11.5)


def test_scene_colors_are_four_and_sorted_by_brightness() -> None:
    scene = SceneField((6, 21), 0.5)
    scene.update(_frame((250, 250, 250), (10, 10, 10)), 0.0)
    colors = scene.colors()
    assert colors is not None and len(colors) == 4
    assert sum((colors[0].red, colors[0].green, colors[0].blue)) <= sum(
        (colors[-1].red, colors[-1].green, colors[-1].blue)
    )


def test_scene_palette_waits_for_its_interval() -> None:
    scene = SceneField((6, 21), 0.5)
    scene.update(_frame((255, 0, 0), (255, 0, 0)), 0.0)
    first = scene.colors()
    scene.update(_frame((0, 0, 255), (0, 0, 255)), 0.1)
    assert scene.colors() == first

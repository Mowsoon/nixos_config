import numpy as np
import pytest

from rgb_effects.render.geometry import KeyboardLayout, build_geometry

LAYOUT = KeyboardLayout(
    led_names=("Key: Escape", "Key: F1", "Key: A", "G2", "Media Mute", "Logo"),
    matrix=((0, 1), (2, None)),
)


def test_matrix_leds_sample_their_cell() -> None:
    geometry = build_geometry(LAYOUT)
    assert (int(geometry.sample_rows[2]), int(geometry.sample_cols[2])) == (1, 0)


def test_g_keys_follow_the_left_column() -> None:
    geometry = build_geometry(LAYOUT)
    assert (int(geometry.sample_rows[3]), int(geometry.sample_cols[3])) == (1, 0)


def test_media_keys_follow_the_top_right_cell() -> None:
    geometry = build_geometry(LAYOUT)
    assert (int(geometry.sample_rows[4]), int(geometry.sample_cols[4])) == (0, 1)


def test_sample_gives_logo_the_given_color() -> None:
    geometry = build_geometry(LAYOUT)
    field = np.zeros((2, 2, 3), dtype=np.float32)
    leds = geometry.sample(field, np.array([1.0, 0.5, 0.0], dtype=np.float32))
    assert leds[5].tolist() == [1.0, 0.5, 0.0]


def test_build_geometry_rejects_empty_matrix() -> None:
    with pytest.raises(ValueError):
        build_geometry(KeyboardLayout(("Logo",), ()))

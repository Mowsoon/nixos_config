import numpy as np
import pytest

from rgb_effects.color import Color
from rgb_effects.engine.palette import PaletteInputs, build_palette, rotate_hue

NEUTRAL = Color(255, 255, 255)
AMBER = Color(255, 128, 0)


def _inputs(hue: Color = NEUTRAL, ceiling: float = 1.0) -> PaletteInputs:
    return PaletteInputs(
        hue=hue, ceiling=ceiling, physics_ceiling=0.6, window=Color(0, 0, 255), accent=None
    )


@pytest.mark.parametrize("size", [6, 7, 8])
def test_table_has_requested_size(size: int) -> None:
    assert build_palette(_inputs(), size).table.shape == (size, 3)


def test_table_starts_with_black() -> None:
    assert build_palette(_inputs(), 8).table[0].tolist() == [0.0, 0.0, 0.0]


def test_ceiling_scales_background_colors() -> None:
    palette = build_palette(_inputs(ceiling=0.2), 8)
    assert float(np.stack([palette.dark, palette.primary, palette.secondary]).max()) <= 0.2 + 1e-6


def test_physics_colors_keep_their_own_ceiling_at_night() -> None:
    assert float(build_palette(_inputs(ceiling=0.2), 8).hot.max()) == pytest.approx(0.6)


def test_warm_hue_removes_blue() -> None:
    neutral = build_palette(_inputs(NEUTRAL), 8).primary[2]
    amber = build_palette(_inputs(AMBER), 8).primary[2]
    assert amber < neutral


def test_missing_accent_gives_a_distinct_secondary() -> None:
    palette = build_palette(_inputs(), 8)
    assert not np.allclose(palette.primary, palette.secondary)


def test_gradient_ends_on_dark_and_secondary() -> None:
    palette = build_palette(_inputs(), 8)
    ends = palette.gradient(np.array([0.0, 1.0], dtype=np.float32))
    assert np.allclose(ends, np.stack([palette.dark, palette.secondary]))


def test_sound_color_replaces_glow_without_warming() -> None:
    inputs = PaletteInputs(AMBER, 0.2, 0.6, Color(0, 0, 255), None, Color(0, 255, 0))
    assert build_palette(inputs, 8).glow.tolist() == pytest.approx([0.0, 0.6, 0.0])


def test_rotate_hue_turns_red_to_green_at_120_degrees() -> None:
    red = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert rotate_hue(red, 120.0).tolist() == pytest.approx([0.0, 1.0, 0.0])


def test_hue_shift_turns_the_master_hues() -> None:
    still = build_palette(_inputs(), 8).primary
    inputs = PaletteInputs(NEUTRAL, 1.0, 0.6, Color(0, 0, 255), None, None, 60.0)
    assert not np.allclose(build_palette(inputs, 8).primary, still)


def test_build_palette_rejects_size_out_of_range() -> None:
    with pytest.raises(ValueError):
        build_palette(_inputs(), 9)

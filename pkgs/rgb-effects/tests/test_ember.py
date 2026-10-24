import pytest

from rgb_effects.color import Color
from rgb_effects.ember import Ember
from rgb_effects.errors import ConfigError

HOT = Color(255, 255, 255)
WARM = Color(255, 100, 0)
COLD = Color(80, 0, 0)
BACKGROUND = Color(0, 0, 10)


def _ember() -> Ember:
    return Ember((HOT, WARM, COLD), 0.9)


def _frame() -> tuple[Color, ...]:
    return (BACKGROUND, BACKGROUND, BACKGROUND)


@pytest.mark.parametrize(("age", "expected"), [(0.0, HOT), (0.35, WARM), (0.7, COLD)])
def test_overlay_cools_along_the_palette(age: float, expected: Color) -> None:
    ember = _ember()
    ember.ignite(1, 10.0)
    assert ember.overlay(_frame(), 10.0 + age)[1] == expected


def test_overlay_restores_background_after_duration() -> None:
    ember = _ember()
    ember.ignite(1, 10.0)
    assert ember.overlay(_frame(), 10.9) == _frame()


def test_overlay_leaves_other_leds_untouched() -> None:
    ember = _ember()
    ember.ignite(1, 10.0)
    assert ember.overlay(_frame(), 10.0)[0] == BACKGROUND


def test_overlay_ignores_index_outside_frame() -> None:
    ember = _ember()
    ember.ignite(7, 10.0)
    assert ember.overlay(_frame(), 10.0) == _frame()


def test_active_is_false_once_every_key_cooled() -> None:
    ember = _ember()
    ember.ignite(0, 10.0)
    assert not ember.active(11.0)


def test_active_is_true_while_a_key_glows() -> None:
    ember = _ember()
    ember.ignite(0, 10.0)
    assert ember.active(10.5)


def test_ignite_all_starts_every_led_part_way_down_the_palette() -> None:
    ember = _ember()
    ember.ignite_all(3, 10.0, 1)
    assert ember.overlay(_frame(), 10.0) == (WARM, WARM, WARM)


def test_ignite_all_keeps_hotter_keys() -> None:
    ember = _ember()
    ember.ignite(0, 10.0)
    ember.ignite_all(3, 10.0, 1)
    assert ember.overlay(_frame(), 10.0)[0] == HOT


@pytest.mark.parametrize(("palette", "duration"), [((), 1.0), ((HOT,), 0.0)])
def test_ember_rejects_invalid_settings(palette: tuple[Color, ...], duration: float) -> None:
    with pytest.raises(ConfigError):
        Ember(palette, duration)


def test_ignite_all_with_step_past_palette_keeps_coldest_color() -> None:
    ember = _ember()
    ember.ignite_all(3, 10.0, 9)
    assert ember.overlay(_frame(), 10.0) == (COLD, COLD, COLD)

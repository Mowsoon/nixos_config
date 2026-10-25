import pytest

from rgb_effects.color import Color
from rgb_effects.errors import ConfigError
from rgb_effects.render.schedule import Keyframe, Schedule

DAWN = Keyframe(minute=360, color=Color(0, 0, 200), brightness=1.0)
DUSK = Keyframe(minute=1080, color=Color(200, 0, 0), brightness=0.5)


def test_color_at_keyframe_time_is_keyframe_color() -> None:
    assert Schedule((DAWN, DUSK)).color_at(360) == Color(0, 0, 200)


def test_color_at_interpolates_color_and_brightness() -> None:
    assert Schedule((DAWN, DUSK)).color_at(720) == Color(75, 0, 75)


def test_color_at_wraps_past_midnight() -> None:
    assert Schedule((DAWN, DUSK)).color_at(0) == Schedule((DAWN, DUSK)).color_at(1440)


def test_color_at_interpolates_across_midnight() -> None:
    assert Schedule((DAWN, DUSK)).color_at(1260) == Color(150, 0, 50).scaled(0.625)


def test_single_keyframe_is_constant() -> None:
    assert Schedule((DUSK,)).color_at(42) == Color(100, 0, 0)


def test_schedule_rejects_empty_keyframes() -> None:
    with pytest.raises(ConfigError):
        Schedule(())


def test_schedule_rejects_unsorted_keyframes() -> None:
    with pytest.raises(ConfigError):
        Schedule((DUSK, DAWN))


@pytest.mark.parametrize(
    "keyframe",
    [
        Keyframe(minute=1440, color=Color(0, 0, 0), brightness=0.5),
        Keyframe(minute=10, color=Color(0, 0, 0), brightness=1.5),
    ],
)
def test_schedule_rejects_out_of_range_keyframe(keyframe: Keyframe) -> None:
    with pytest.raises(ConfigError):
        Schedule((keyframe,))


def test_brightness_at_interpolates_between_keyframes() -> None:
    assert Schedule((DAWN, DUSK)).brightness_at(720) == 0.75

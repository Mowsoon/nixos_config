import numpy as np
import pytest

from rgb_effects.color import Color
from rgb_effects.effects.hud import (
    LEFT_ALT,
    LEFT_CTRL,
    RIGHT_CTRL,
    Hud,
    HudSettings,
    bits,
    combo,
)

NAMES = (
    "Key: F1",
    "Key: F2",
    "Key: F3",
    "Key: F4",
    "Key: F5",
    "Key: F6",
    "Key: F7",
    "Key: F8",
    "Key: F9",
    "Key: F10",
    "Key: F11",
    "Key: F12",
    "Key: &",
    "Key: é",
    'Key: "',
    "Key: '",
    "Key: (",
    "Key: -",
    "Key: C",
    "Key: V",
    "Key: Tab",
)
EDIT, CLOCK, FOCUS = Color(0, 229, 255), Color(255, 255, 255), Color(0, 255, 156)
SETTINGS = HudSettings(
    bindings={"ctrl": {"edit": ("C", "V")}, "alt": {"window": ("Tab",)}},
    colors={"edit": EDIT, "clock": CLOCK, "focus": FOCUS},
    dim=0.25,
    clock_hold_seconds=0.5,
)


def _hud() -> Hud:
    return Hud(SETTINGS, NAMES)


def _unit(color: Color) -> list[float]:
    channels = np.array([color.red, color.green, color.blue], dtype=np.float32) / np.float32(255)
    return [float(channel) for channel in channels]


def test_no_overlay_without_modifier_or_focus() -> None:
    assert _hud().overlay(0.0, 600.0) is None


def test_ctrl_lights_its_bindings_and_dims_the_rest() -> None:
    hud = _hud()
    hud.key_down(LEFT_CTRL, 0.0)
    overlay = hud.overlay(0.1, 600.0)
    assert overlay is not None and overlay.dim == 0.25
    assert {led: color.tolist() for led, color in overlay.cells.items()} == {
        18: _unit(EDIT),
        19: _unit(EDIT),
    }


def test_category_without_color_is_skipped() -> None:
    hud = _hud()
    hud.key_down(LEFT_ALT, 0.0)
    overlay = hud.overlay(0.1, 600.0)
    assert overlay is not None and not overlay.cells


def test_release_ends_the_mask() -> None:
    hud = _hud()
    hud.key_down(LEFT_CTRL, 0.0)
    hud.key_up(LEFT_CTRL)
    assert hud.overlay(0.1, 600.0) is None


@pytest.mark.parametrize(
    ("held", "expected"), [({LEFT_ALT, LEFT_CTRL}, "ctrl+alt"), ({RIGHT_CTRL}, "ctrl"), ({30}, "")]
)
def test_combo_orders_modifier_names(held: set[int], expected: str) -> None:
    assert combo(held) == expected


def test_bits_reads_most_significant_first() -> None:
    assert bits(5, 5) == (False, False, True, False, True)


def test_clock_shows_after_holding_right_ctrl() -> None:
    hud = _hud()
    hud.key_down(RIGHT_CTRL, 0.0)
    overlay = hud.overlay(0.6, 13 * 60 + 37)
    assert overlay is not None
    lit = sorted(led for led, color in overlay.cells.items() if color.any() and led < 18)
    assert lit == [1, 2, 4, 12, 15, 17]


def test_clock_waits_for_the_hold_delay() -> None:
    hud = _hud()
    hud.key_down(RIGHT_CTRL, 0.0)
    overlay = hud.overlay(0.2, 600.0)
    assert overlay is not None and 0 not in overlay.cells


def test_another_key_cancels_the_clock() -> None:
    hud = _hud()
    hud.key_down(RIGHT_CTRL, 0.0)
    hud.key_down(46, 0.1)
    overlay = hud.overlay(0.6, 13 * 60)
    assert overlay is not None and 0 not in overlay.cells


def test_focus_fills_the_function_row() -> None:
    hud = _hud()
    hud.start_focus(120.0, 0.0)
    overlay = hud.overlay(60.0, 600.0)
    assert overlay is not None
    bright = [led for led in range(12) if overlay.cells[led].max() > 0.5]
    assert bright == [0, 1, 2, 3, 4, 5]


def test_focus_ends_after_the_done_blink() -> None:
    hud = _hud()
    hud.start_focus(10.0, 0.0)
    assert hud.overlay(14.0, 600.0) is None and not hud.active(14.0)


def test_stop_focus_clears_the_bar() -> None:
    hud = _hud()
    hud.start_focus(10.0, 0.0)
    hud.stop_focus()
    assert hud.overlay(1.0, 600.0) is None

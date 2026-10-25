import pytest

from rgb_effects.color import Color
from rgb_effects.render.windows import WindowColors

FIREFOX = Color(255, 113, 57)


def _colors() -> WindowColors:
    return WindowColors({"Firefox": FIREFOX, "discord": Color(88, 101, 242)})


def test_activate_known_class_sets_its_color() -> None:
    windows = _colors()
    windows.activate("firefox")
    assert windows.current == FIREFOX


def test_activate_matches_case_insensitively() -> None:
    windows = _colors()
    windows.activate("FIREFOX")
    assert windows.current == FIREFOX


def test_activate_unknown_class_clears_color() -> None:
    windows = _colors()
    windows.activate("firefox")
    windows.activate("org.kde.dolphin")
    assert windows.current is None


def test_activate_reports_change() -> None:
    assert _colors().activate("firefox")


def test_activate_reports_no_change_for_same_color() -> None:
    windows = _colors()
    windows.activate("firefox")
    assert not windows.activate("firefox")


@pytest.mark.parametrize("resource_class", ["fire\nfox", "x" * 300, ""])
def test_activate_ignores_malformed_class(resource_class: str) -> None:
    windows = _colors()
    windows.activate(resource_class)
    assert windows.current is None


def test_color_for_finds_a_notifying_application() -> None:
    windows = _colors()
    assert (windows.color_for("FIREFOX"), windows.current) == (FIREFOX, None)

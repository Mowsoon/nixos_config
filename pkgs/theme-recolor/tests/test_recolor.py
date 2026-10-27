import math

import pytest

from theme_recolor.errors import PaletteError
from theme_recolor.mapping import Palette, family
from theme_recolor.oklab import format_hex, parse_hex, to_lab
from theme_recolor.recolor import build, resolve_roles


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#e74c3c", "red"),
        ("#f57c00", "orange"),
        ("#ffc759", "yellow"),
        ("#4caf50", "green"),
        ("#16a085", "cyan"),
        ("#268bd2", "blue"),
        ("#7e57c2", "purple"),
        ("#f06292", "pink"),
        ("#8d493d", "brown"),
    ],
)
def test_family_follows_hue_bands(text: str, expected: str) -> None:
    assert family(parse_hex(text)) == expected


def test_palette_rejects_missing_slots() -> None:
    with pytest.raises(PaletteError):
        Palette.from_hex({"base00": "000000"})


def test_resolve_roles_rejects_unknown_family() -> None:
    with pytest.raises(PaletteError):
        resolve_roles({"teal": "base0D"})


def test_resolve_roles_rejects_unknown_slot() -> None:
    with pytest.raises(PaletteError):
        resolve_roles({"cyan": "base10"})


def test_colours_darker_than_base00_are_kept(palette: Palette) -> None:
    mapping = build(palette, {}, {})
    assert mapping.apply((0.0, 0.0, 0.0)) == (0.0, 0.0, 0.0)


def test_white_becomes_base07(palette: Palette) -> None:
    mapping = build(palette, {}, {})
    assert format_hex(mapping.apply((1.0, 1.0, 1.0))) == "#faf3f4"


def test_grey_keeps_its_lightness(palette: Palette) -> None:
    grey = parse_hex("#808080")
    result = build(palette, {}, {}).apply(grey)
    assert to_lab(result).lightness == pytest.approx(to_lab(grey).lightness, abs=0.01)


def test_chromatic_colour_takes_the_hue_of_its_role(palette: Palette) -> None:
    blue = parse_hex("#268bd2")
    result = to_lab(build(palette, {"#268bd2": 1}, {}).apply(blue))
    role = palette.slots["base0D"]
    assert math.cos(result.hue - role.hue) == pytest.approx(1.0, abs=0.01)


def test_override_moves_a_family_to_another_role(palette: Palette) -> None:
    mapping = build(palette, {}, {"cyan": "base0D"})
    assert mapping.role_of(parse_hex("#16a085")) == "base0D"

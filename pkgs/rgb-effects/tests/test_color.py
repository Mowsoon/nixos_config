import pytest

from rgb_effects.color import Color, parse_hex
from rgb_effects.errors import ConfigError


def test_parse_hex_reads_each_channel() -> None:
    assert parse_hex("#ff8001") == Color(255, 128, 1)


@pytest.mark.parametrize("text", ["ff8001", "#ff80", "#gg0000", "#ff800100", ""])
def test_parse_hex_rejects_malformed_text(text: str) -> None:
    with pytest.raises(ConfigError):
        parse_hex(text)


def test_color_rejects_channel_out_of_range() -> None:
    with pytest.raises(ValueError):
        Color(256, 0, 0)


def test_scaled_clamps_to_valid_channels() -> None:
    assert Color(200, 100, 0).scaled(2.0) == Color(255, 200, 0)


def test_mixed_at_half_weight_is_midpoint() -> None:
    assert Color(0, 0, 0).mixed(Color(200, 100, 50), 0.5) == Color(100, 50, 25)


@pytest.mark.parametrize(
    ("color", "expected"),
    [(Color(1, 2, 3), Color(1, 2, 2)), (Color(1, 2, 0), Color(1, 2, 1))],
)
def test_nudged_changes_blue_by_one(color: Color, expected: Color) -> None:
    assert color.nudged() == expected


@pytest.mark.parametrize(
    ("color", "expected"),
    [(Color(255, 128, 0), Color(102, 51, 0)), (Color(50, 20, 10), Color(50, 20, 10))],
)
def test_capped_scales_only_colors_brighter_than_ceiling(color: Color, expected: Color) -> None:
    assert color.capped(0.4) == expected

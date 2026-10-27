import pytest

from theme_recolor.errors import FormatError
from theme_recolor.oklab import format_hex, from_lab, parse_hex, to_lab


@pytest.mark.parametrize(
    ("text", "expected"),
    [("#ffffff", (1.0, 1.0, 1.0)), ("000", (0.0, 0.0, 0.0)), ("#F00", (1.0, 0.0, 0.0))],
)
def test_parse_hex_accepts_short_and_long_forms(
    text: str, expected: tuple[float, float, float]
) -> None:
    assert parse_hex(text) == expected


@pytest.mark.parametrize("text", ["#12", "#gggggg", "", "#1234567"])
def test_parse_hex_rejects_malformed_colours(text: str) -> None:
    with pytest.raises(FormatError):
        parse_hex(text)


@pytest.mark.parametrize("text", ["#c04a63", "#1a0e11", "#ffc759", "#808080"])
def test_oklab_round_trip_preserves_colour(text: str) -> None:
    assert format_hex(from_lab(to_lab(parse_hex(text)))) == text

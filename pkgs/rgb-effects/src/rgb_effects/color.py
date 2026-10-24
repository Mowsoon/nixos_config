import re
from dataclasses import dataclass

from rgb_effects.errors import ConfigError

HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


def _clamp_channel(value: float) -> int:
    return max(0, min(255, round(value)))


@dataclass(frozen=True, slots=True)
class Color:
    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        for channel in (self.red, self.green, self.blue):
            if not 0 <= channel <= 255:
                raise ValueError(f"color channel {channel} is outside 0..255")

    def scaled(self, factor: float) -> "Color":
        return Color(
            _clamp_channel(self.red * factor),
            _clamp_channel(self.green * factor),
            _clamp_channel(self.blue * factor),
        )

    def mixed(self, other: "Color", weight: float) -> "Color":
        return Color(
            _clamp_channel(self.red + (other.red - self.red) * weight),
            _clamp_channel(self.green + (other.green - self.green) * weight),
            _clamp_channel(self.blue + (other.blue - self.blue) * weight),
        )

    def capped(self, ceiling: float) -> "Color":
        peak = max(self.red, self.green, self.blue)
        limit = 255 * ceiling
        return self if peak <= limit else self.scaled(limit / peak)

    def nudged(self) -> "Color":
        blue = self.blue - 1 if self.blue > 0 else 1
        return Color(self.red, self.green, blue)


def parse_hex(text: str) -> Color:
    if not HEX_COLOR.fullmatch(text):
        raise ConfigError(f"color {text!r} is not in #rrggbb form")
    return Color(int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16))

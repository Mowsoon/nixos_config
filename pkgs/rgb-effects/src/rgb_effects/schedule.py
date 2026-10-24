from dataclasses import dataclass

from rgb_effects.color import Color
from rgb_effects.errors import ConfigError

MINUTES_PER_DAY = 1440


@dataclass(frozen=True, slots=True)
class Keyframe:
    minute: int
    color: Color
    brightness: float


def _validate_keyframe(keyframe: Keyframe) -> None:
    if not 0 <= keyframe.minute < MINUTES_PER_DAY:
        raise ConfigError(f"keyframe minute {keyframe.minute} is outside the day")
    if not 0.0 <= keyframe.brightness <= 1.0:
        raise ConfigError(f"keyframe brightness {keyframe.brightness} is outside 0..1")


@dataclass(frozen=True, slots=True)
class Schedule:
    keyframes: tuple[Keyframe, ...]

    def __post_init__(self) -> None:
        if not self.keyframes:
            raise ConfigError("schedule has no keyframe")
        for keyframe in self.keyframes:
            _validate_keyframe(keyframe)
        minutes = [keyframe.minute for keyframe in self.keyframes]
        if minutes != sorted(set(minutes)):
            raise ConfigError("schedule keyframes must be sorted with distinct times")

    def color_at(self, minute_of_day: float) -> Color:
        previous, following, weight = self._position(minute_of_day)
        color = previous.color.mixed(following.color, weight)
        return color.scaled(self.brightness_at(minute_of_day))

    def brightness_at(self, minute_of_day: float) -> float:
        previous, following, weight = self._position(minute_of_day)
        return previous.brightness + (following.brightness - previous.brightness) * weight

    def _position(self, minute_of_day: float) -> tuple[Keyframe, Keyframe, float]:
        minute = minute_of_day % MINUTES_PER_DAY
        earlier = [keyframe for keyframe in self.keyframes if keyframe.minute <= minute]
        later = [keyframe for keyframe in self.keyframes if keyframe.minute > minute]
        previous = earlier[-1] if earlier else self.keyframes[-1]
        following = later[0] if later else self.keyframes[0]
        span = (following.minute - previous.minute) % MINUTES_PER_DAY or MINUTES_PER_DAY
        weight = ((minute - previous.minute) % MINUTES_PER_DAY) / span
        return previous, following, weight

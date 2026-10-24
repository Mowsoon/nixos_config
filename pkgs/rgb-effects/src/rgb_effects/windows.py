from collections.abc import Mapping
from types import MappingProxyType

from rgb_effects.color import Color

MAX_RESOURCE_CLASS_LENGTH = 256


class WindowColors:
    def __init__(self, colors: Mapping[str, Color]) -> None:
        self._colors = MappingProxyType({name.lower(): color for name, color in colors.items()})
        self._current: Color | None = None

    @property
    def current(self) -> Color | None:
        return self._current

    def activate(self, resource_class: str) -> bool:
        color = self._colors.get(_normalized(resource_class))
        changed = color != self._current
        self._current = color
        return changed


def _normalized(resource_class: str) -> str:
    if len(resource_class) > MAX_RESOURCE_CLASS_LENGTH or not resource_class.isprintable():
        return ""
    return resource_class.strip().lower()

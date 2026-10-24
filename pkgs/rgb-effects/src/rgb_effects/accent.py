import logging
from pathlib import Path
from typing import Protocol

from rgb_effects.color import Color
from rgb_effects.retry import Sleep

logger = logging.getLogger(__name__)

GENERAL_SECTION = "[General]"
ACCENT_KEY = "AccentColor"


class AccentListener(Protocol):
    def accent_changed(self, color: Color | None) -> None: ...


def _parse_value(value: str) -> Color | None:
    parts = value.strip().split(",")
    if len(parts) < 3:
        return None
    try:
        channels = [int(part) for part in parts[:3]]
    except ValueError:
        return None
    if not all(0 <= channel <= 255 for channel in channels):
        return None
    return Color(*channels)


def parse_accent(text: str) -> Color | None:
    section = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped
            continue
        key, _, value = stripped.partition("=")
        if section == GENERAL_SECTION and key.split("[")[0] == ACCENT_KEY:
            return _parse_value(value)
    return None


class AccentWatcher:
    def __init__(
        self, path: Path, listener: AccentListener, poll_seconds: float, sleep: Sleep
    ) -> None:
        self._path = path
        self._listener = listener
        self._poll_seconds = poll_seconds
        self._sleep = sleep
        self._stamp: float | None = None
        self._color: Color | None = None

    async def run(self) -> None:
        while True:
            self.poll()
            await self._sleep(self._poll_seconds)

    def poll(self) -> None:
        try:
            stamp = self._path.stat().st_mtime
            if stamp == self._stamp:
                return
            text = self._path.read_text(encoding="utf-8")
        except OSError as err:
            logger.warning("read %s: %s", self._path, err.strerror)
            return
        self._stamp = stamp
        color = parse_accent(text)
        if color != self._color:
            self._color = color
            self._listener.accent_changed(color)

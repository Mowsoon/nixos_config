from pathlib import Path

import pytest

from rgb_effects.accent import AccentWatcher, parse_accent
from rgb_effects.color import Color

KDEGLOBALS = """[ColorEffects:Disabled]
AccentColor=1,2,3

[General]
ColorScheme=BreezeDark
AccentColor=61,174,233
"""


def test_parse_accent_reads_general_group_only() -> None:
    assert parse_accent(KDEGLOBALS) == Color(61, 174, 233)


@pytest.mark.parametrize(
    "text",
    [
        "[General]\nColorScheme=Breeze\n",
        "[General]\nAccentColor=red\n",
        "[General]\nAccentColor=1,2\n",
    ],
)
def test_parse_accent_is_none_without_valid_value(text: str) -> None:
    assert parse_accent(text) is None


class Recorder:
    def __init__(self) -> None:
        self.colors: list[Color | None] = []

    def accent_changed(self, color: Color | None) -> None:
        self.colors.append(color)


async def _never(seconds: float) -> None:
    raise AssertionError(seconds)


def test_poll_reports_accent_once(tmp_path: Path) -> None:
    path = tmp_path / "kdeglobals"
    path.write_text(KDEGLOBALS, encoding="utf-8")
    recorder = Recorder()
    watcher = AccentWatcher(path, recorder, 60.0, _never)
    watcher.poll()
    watcher.poll()
    assert recorder.colors == [Color(61, 174, 233)]


def test_poll_survives_missing_file(tmp_path: Path) -> None:
    recorder = Recorder()
    AccentWatcher(tmp_path / "absent", recorder, 60.0, _never).poll()
    assert recorder.colors == []

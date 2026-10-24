import copy
import json
from pathlib import Path
from typing import Any

import pytest

from rgb_effects.color import Color
from rgb_effects.config import load_config, parse_config
from rgb_effects.errors import ConfigError

VALID: dict[str, Any] = {
    "server": {"host": "127.0.0.1", "port": 6742},
    "device": "G915 X LS",
    "refreshSeconds": 60,
    "windowColors": {"firefox": "#ff7139"},
    "fps": 30,
    "batteryFps": 15,
    "lowBattery": {"model": "G915 X LS", "threshold": 20, "brightness": 0.4},
    "keySocket": "/run/rgb-keyreader.sock",
    "engine": {
        "paletteSize": 8,
        "packetsPerSecond": 180,
        "idleSeconds": 30,
        "sleepSeconds": 300,
    },
    "physics": {
        "minimumBrightness": 0.6,
        "emberColdMs": 800,
        "emberHotMs": 2500,
        "sandWordsPerMinute": 15,
    },
    "hud": {
        "bindings": {"ctrl": {"edit": ["C", "V"]}, "alt+ctrl": {"window": ["Tab"]}},
        "colors": {"edit": "#00e5ff"},
        "dim": 0.25,
        "clockHoldMs": 500,
    },
    "schedule": [
        {"time": "06:30", "color": "#9fb8ff", "brightness": 0.35},
        {"time": "18:00", "color": "#ffb070", "brightness": 0.6},
    ],
}


def _with(path: list[str], value: Any) -> dict[str, Any]:
    data = copy.deepcopy(VALID)
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return data


def test_parse_config_reads_schedule_times_as_minutes() -> None:
    config = parse_config(VALID)
    assert [keyframe.minute for keyframe in config.schedule.keyframes] == [390, 1080]


def test_parse_config_reads_keyframe_color() -> None:
    assert parse_config(VALID).schedule.keyframes[1].color == Color(255, 176, 112)


def test_parse_config_reads_window_colors() -> None:
    assert parse_config(VALID).window_colors == {"firefox": Color(255, 113, 57)}


def test_parse_config_reads_ember_durations_in_seconds() -> None:
    physics = parse_config(VALID).physics
    assert (physics.ember_cold_seconds, physics.ember_hot_seconds) == (0.8, 2.5)


def test_parse_config_converts_words_per_minute_to_keys_per_second() -> None:
    assert parse_config(VALID).physics.falling_keys_per_second == 1.25


def test_parse_config_accepts_null_key_socket() -> None:
    assert parse_config(_with(["keySocket"], None)).key_socket is None


def test_parse_config_reads_low_battery_ceiling() -> None:
    assert parse_config(VALID).low_battery.ceiling == 0.4


def test_parse_config_normalises_hud_combinations() -> None:
    assert set(parse_config(VALID).hud.bindings) == {"ctrl", "ctrl+alt"}


def test_parse_config_accepts_integer_refresh() -> None:
    assert parse_config(VALID).refresh_seconds == 60.0


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (["server", "port"], 0),
        (["server", "port"], "6742"),
        (["server", "host"], " "),
        (["device"], ""),
        (["refreshSeconds"], 0.5),
        (["refreshSeconds"], True),
        (["schedule"], []),
        (["schedule"], [{"time": "24:00", "color": "#000000", "brightness": 0.1}]),
        (["schedule"], ["06:30"]),
        (["windowColors"], {"firefox": 1}),
        (["windowColors"], {"firefox": "orange"}),
        (["windowColors"], {"": "#ff7139"}),
        (["fps"], 0),
        (["fps"], 61),
        (["batteryFps"], 0),
        (["lowBattery", "threshold"], 0),
        (["lowBattery", "brightness"], 0),
        (["lowBattery", "model"], ""),
        (["keySocket"], "run/rgb-keyreader.sock"),
        (["keySocket"], 3),
        (["engine", "paletteSize"], 9),
        (["engine", "packetsPerSecond"], 400),
        (["engine", "idleSeconds"], 1),
        (["physics", "minimumBrightness"], 2),
        (["physics", "emberColdMs"], 10),
        (["physics", "emberHotMs"], 700),
        (["physics", "sandWordsPerMinute"], 500),
        (["hud", "bindings"], {"shift": {"edit": ["C"]}}),
        (["hud", "bindings"], {"ctrl": {"edit": "C"}}),
        (["hud", "colors"], {"edit": "cyan"}),
        (["hud", "dim"], 2),
        (["hud", "clockHoldMs"], 10),
    ],
)
def test_parse_config_rejects_invalid_field(path: list[str], value: Any) -> None:
    with pytest.raises(ConfigError):
        parse_config(_with(path, value))


def test_parse_config_rejects_missing_field() -> None:
    data = copy.deepcopy(VALID)
    del data["device"]
    with pytest.raises(ConfigError):
        parse_config(data)


def test_parse_config_rejects_non_object_root() -> None:
    with pytest.raises(ConfigError):
        parse_config([])


def test_load_config_reads_json_file(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(VALID), encoding="utf-8")
    assert load_config(path).device == "G915 X LS"


def test_load_config_raises_config_error_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "absent.json")


def test_load_config_raises_config_error_for_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rgb_effects.color import Color, parse_hex
from rgb_effects.errors import ConfigError
from rgb_effects.schedule import Keyframe, Schedule

CLOCK_TIME = re.compile(r"([01][0-9]|2[0-3]):([0-5][0-9])")


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str
    port: int


@dataclass(frozen=True, slots=True)
class EngineConfig:
    palette_size: int
    packets_per_second: int
    idle_seconds: float
    sleep_seconds: float


@dataclass(frozen=True, slots=True)
class PhysicsConfig:
    minimum_brightness: float
    ember_cold_seconds: float
    ember_hot_seconds: float
    falling_keys_per_second: float


@dataclass(frozen=True, slots=True)
class LowBatteryConfig:
    model: str
    threshold: int
    ceiling: float


@dataclass(frozen=True, slots=True)
class HudConfig:
    bindings: dict[str, dict[str, tuple[str, ...]]]
    colors: dict[str, Color]
    dim: float
    clock_hold_seconds: float


@dataclass(frozen=True, slots=True)
class EffectsConfig:
    server: ServerConfig
    device: str
    schedule: Schedule
    window_colors: dict[str, Color]
    engine: EngineConfig
    physics: PhysicsConfig
    hud: HudConfig
    key_socket: Path | None
    refresh_seconds: float
    fps: int
    battery_fps: int
    low_battery: LowBatteryConfig


def _field(data: dict[str, Any], name: str, kind: type) -> Any:
    if name not in data:
        raise ConfigError(f"missing field {name!r}")
    value = data[name]
    if kind is float and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, kind) or isinstance(value, bool):
        raise ConfigError(f"field {name!r} must be of type {kind.__name__}")
    return value


def _non_empty(text: str, name: str) -> str:
    if not text.strip():
        raise ConfigError(f"field {name!r} is empty")
    return text


def _minute_of_day(text: str) -> int:
    match = CLOCK_TIME.fullmatch(text)
    if match is None:
        raise ConfigError(f"time {text!r} is not in HH:MM form")
    return int(match.group(1)) * 60 + int(match.group(2))


def _keyframe(data: Any) -> Keyframe:
    if not isinstance(data, dict):
        raise ConfigError("schedule entries must be objects")
    return Keyframe(
        minute=_minute_of_day(_field(data, "time", str)),
        color=parse_hex(_field(data, "color", str)),
        brightness=_field(data, "brightness", float),
    )


def _window_colors(data: dict[str, Any]) -> dict[str, Color]:
    colors: dict[str, Color] = {}
    for name, value in data.items():
        if not isinstance(value, str):
            raise ConfigError(f"window colour of {name!r} must be a string")
        colors[_non_empty(name, "windowColors")] = parse_hex(value)
    return colors


def _bounded(data: dict[str, Any], name: str, low: int, high: int) -> int:
    value = _field(data, name, int)
    if not low <= value <= high:
        raise ConfigError(f"{name} {value} is outside {low}..{high}")
    return value


def _engine(data: dict[str, Any]) -> EngineConfig:
    return EngineConfig(
        palette_size=_bounded(data, "paletteSize", 6, 8),
        packets_per_second=_bounded(data, "packetsPerSecond", 30, 320),
        idle_seconds=float(_bounded(data, "idleSeconds", 5, 600)),
        sleep_seconds=float(_bounded(data, "sleepSeconds", 30, 3600)),
    )


def _physics(data: dict[str, Any]) -> PhysicsConfig:
    brightness = _field(data, "minimumBrightness", float)
    if not 0.0 <= brightness <= 1.0:
        raise ConfigError(f"minimumBrightness {brightness} is outside 0..1")
    cold = _bounded(data, "emberColdMs", 50, 10000)
    hot = _bounded(data, "emberHotMs", 50, 10000)
    if hot < cold:
        raise ConfigError("emberHotMs must not be shorter than emberColdMs")
    words = _bounded(data, "sandWordsPerMinute", 0, 200)
    return PhysicsConfig(brightness, cold / 1000, hot / 1000, words * 5 / 60)


def _fps(data: dict[str, Any], name: str) -> int:
    fps = _field(data, name, int)
    if not 1 <= fps <= 60:
        raise ConfigError(f"{name} {fps} is outside 1..60")
    return fps


def _low_battery(data: dict[str, Any]) -> LowBatteryConfig:
    threshold = _field(data, "threshold", int)
    if not 1 <= threshold <= 100:
        raise ConfigError(f"lowBattery threshold {threshold} is outside 1..100")
    ceiling = _field(data, "brightness", float)
    if not 0.0 < ceiling <= 1.0:
        raise ConfigError(f"lowBattery brightness {ceiling} is outside 0..1")
    model = _non_empty(_field(data, "model", str), "model")
    return LowBatteryConfig(model=model, threshold=threshold, ceiling=ceiling)


MODIFIER_ORDER = ("ctrl", "alt", "super")


def _combo(name: str) -> str:
    parts = name.split("+")
    if len(set(parts)) != len(parts) or not set(parts) <= set(MODIFIER_ORDER):
        raise ConfigError(f"hud binding {name!r} must combine ctrl, alt and super")
    return "+".join(part for part in MODIFIER_ORDER if part in parts)


def _labels(value: Any, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(label, str) for label in value):
        raise ConfigError(f"hud keys of {where} must be a list of strings")
    return tuple(value)


def _bindings(data: dict[str, Any]) -> dict[str, dict[str, tuple[str, ...]]]:
    bindings: dict[str, dict[str, tuple[str, ...]]] = {}
    for name, categories in data.items():
        if not isinstance(categories, dict):
            raise ConfigError(f"hud binding {name!r} must map categories to keys")
        bindings[_combo(name)] = {
            category: _labels(keys, f"{name}.{category}") for category, keys in categories.items()
        }
    return bindings


def _hud(data: dict[str, Any]) -> HudConfig:
    dim = _field(data, "dim", float)
    if not 0.0 <= dim <= 1.0:
        raise ConfigError(f"hud dim {dim} is outside 0..1")
    return HudConfig(
        bindings=_bindings(_field(data, "bindings", dict)),
        colors=_window_colors(_field(data, "colors", dict)),
        dim=dim,
        clock_hold_seconds=_bounded(data, "clockHoldMs", 100, 5000) / 1000,
    )


def _key_socket(data: dict[str, Any]) -> Path | None:
    value = data.get("keySocket")
    if value is None:
        return None
    if not isinstance(value, str) or not value.startswith("/"):
        raise ConfigError("keySocket must be an absolute path or null")
    return Path(value)


def _server(data: dict[str, Any]) -> ServerConfig:
    port = _field(data, "port", int)
    if not 1 <= port <= 65535:
        raise ConfigError(f"server port {port} is outside 1..65535")
    return ServerConfig(host=_non_empty(_field(data, "host", str), "host"), port=port)


def parse_config(data: Any) -> EffectsConfig:
    if not isinstance(data, dict):
        raise ConfigError("configuration root must be an object")
    refresh = _field(data, "refreshSeconds", float)
    if not 1.0 <= refresh <= 3600.0:
        raise ConfigError(f"refreshSeconds {refresh} is outside 1..3600")
    return EffectsConfig(
        server=_server(_field(data, "server", dict)),
        device=_non_empty(_field(data, "device", str), "device"),
        schedule=Schedule(tuple(_keyframe(entry) for entry in _field(data, "schedule", list))),
        window_colors=_window_colors(_field(data, "windowColors", dict)),
        engine=_engine(_field(data, "engine", dict)),
        physics=_physics(_field(data, "physics", dict)),
        hud=_hud(_field(data, "hud", dict)),
        key_socket=_key_socket(data),
        refresh_seconds=refresh,
        fps=_fps(data, "fps"),
        battery_fps=_fps(data, "batteryFps"),
        low_battery=_low_battery(_field(data, "lowBattery", dict)),
    )


def load_config(path: Path) -> EffectsConfig:
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError) as err:
        raise ConfigError(f"read configuration {path}") from err
    return parse_config(data)

import argparse
import asyncio
import importlib.resources
import logging
import os
import signal
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from rgb_effects.sources.accent import AccentWatcher
from rgb_effects.sources.audio.analysis import Analyzer
from rgb_effects.sources.audio.capture import AudioCapture
from rgb_effects.config import EffectsConfig, load_config
from rgb_effects.daemon import Daemon, EventWaiter, Pacing, Runtime, Scene
from rgb_effects.render.activity import Activity
from rgb_effects.effects.background import Background, BackgroundSettings
from rgb_effects.render.compose import Engine, EngineSettings
from rgb_effects.render.geometry import KeyboardLayout, build_geometry
from rgb_effects.effects.hud import Hud, HudSettings
from rgb_effects.effects.physics import Physics, PhysicsSettings
from rgb_effects.effects.sound import SoundField, SoundSettings
from rgb_effects.errors import ConfigError, SessionError
from rgb_effects.sdk.client import OpenRgbKeyboard
from rgb_effects.sources.keys.listener import KeySource
from rgb_effects.retry import RetryPolicy
from rgb_effects.sources.power import PowerMonitor
from rgb_effects.sources.screen.portal import ScreenCastPortal, TokenStore
from rgb_effects.sources.screen.capture import ScreenCapture
from rgb_effects.sources.screen.feed import FeedSettings, ScreenFeed
from rgb_effects.effects.scene import SceneField
from rgb_effects.dbus.service import Session
from rgb_effects.sdk.settings import SleepController
from rgb_effects.render.windows import WindowColors

logger = logging.getLogger("rgb_effects")

CLIENT_NAME = "rgb-effects"
RETRY = RetryPolicy(initial_seconds=2.0, maximum_seconds=60.0)
POWER_SUPPLIES = Path("/sys/class/power_supply")
ACTIVITY_SECONDS = 3.0
NOISE_SEED = 1915
BANDS = 21


class SystemClock:
    def minute_of_day(self) -> float:
        now = time.localtime()
        return now.tm_hour * 60 + now.tm_min + now.tm_sec / 60

    def monotonic(self) -> float:
        return time.monotonic()


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="rgb-effects")
    parser.add_argument("--config", type=Path, required=True)
    return parser.parse_args(argv)


def _engine_factory(config: EffectsConfig) -> Callable[[KeyboardLayout], Engine]:
    engine, physics = config.engine, config.physics
    physics_settings = PhysicsSettings(
        ember_cold_seconds=physics.ember_cold_seconds,
        ember_hot_seconds=physics.ember_hot_seconds,
    )
    settings = EngineSettings(
        engine.palette_size,
        engine.sleep_seconds,
        physics.falling_keys_per_second,
        config.audio.color if config.audio is not None else None,
    )
    hud = HudSettings(
        config.hud.bindings, config.hud.colors, config.hud.dim, config.hud.clock_hold_seconds
    )
    audio = config.audio
    scene_seconds = config.screen.palette_seconds if config.screen is not None else 0.5
    sound = SoundSettings(
        spectrum_gain=audio.spectrum_gain if audio is not None else 0.0,
        silence_seconds=audio.silence_seconds if audio is not None else 5.0,
        hue_range=audio.hue_range if audio is not None else 0.0,
    )

    def build(layout: KeyboardLayout) -> Engine:
        geometry = build_geometry(layout)
        background = Background(
            geometry.shape, BackgroundSettings(idle_seconds=engine.idle_seconds), NOISE_SEED
        )
        return Engine(
            geometry,
            background,
            Physics(geometry.shape, physics_settings),
            Activity(ACTIVITY_SECONDS, time.monotonic()),
            Hud(hud, layout.led_names),
            SoundField(geometry.shape[1], sound),
            SceneField(geometry.shape, scene_seconds),
            settings,
        )

    return build


def _sleep_controller(config: EffectsConfig) -> SleepController | None:
    if config.sleep_seconds is None:
        return None
    return SleepController(config.server, CLIENT_NAME, config.sleep_seconds, RETRY, asyncio.sleep)


class FrameRelay:
    def __init__(self) -> None:
        self._target: Daemon | None = None

    def bind(self, target: Daemon) -> None:
        self._target = target

    def screen_frame(self, frame: NDArray[np.uint8]) -> None:
        if self._target is not None:
            self._target.screen_frame(frame)


def _screen_capture(config: EffectsConfig, relay: FrameRelay) -> ScreenCapture | None:
    screen = config.screen
    if screen is None:
        return None
    state = os.environ.get("STATE_DIRECTORY")
    folder = Path(state) if state else Path.home() / ".local" / "state" / "rgb-effects"
    tokens = TokenStore(folder / "screencast-token")
    feed = ScreenFeed(FeedSettings(screen.launcher, screen.plugin_path, screen.fps), relay)
    return ScreenCapture(ScreenCastPortal(), feed, tokens, screen.on_battery)


def _daemon(
    config: EffectsConfig, sleep_policy: SleepController | None, screen: ScreenCapture | None
) -> Daemon:
    scene = Scene(
        schedule=config.schedule,
        windows=WindowColors(config.window_colors),
        engine_factory=_engine_factory(config),
        pacing=Pacing(
            refresh_seconds=config.refresh_seconds,
            frame_seconds=1 / config.fps,
            battery_frame_seconds=1 / config.battery_fps,
            low_battery_ceiling=config.low_battery.ceiling,
            packets_per_second=config.engine.packets_per_second,
        ),
        physics_ceiling=config.physics.minimum_brightness,
    )
    runtime = Runtime(
        keyboard=OpenRgbKeyboard(config.server, config.device, CLIENT_NAME),
        clock=SystemClock(),
        waiter=EventWaiter(),
        sleep=asyncio.sleep,
        retry=RETRY,
        sleep_policy=sleep_policy,
        screen=screen,
    )
    return Daemon(scene, runtime)


def _power_monitor(daemon: Daemon, config: EffectsConfig) -> PowerMonitor:
    battery = (POWER_SUPPLIES, config.low_battery.model, config.low_battery.threshold)
    return PowerMonitor(daemon, battery, config.refresh_seconds, RETRY, asyncio.sleep)


def _accent_watcher(daemon: Daemon, config: EffectsConfig) -> AccentWatcher:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    path = config_home / "kdeglobals"
    return AccentWatcher(path, daemon, config.refresh_seconds, asyncio.sleep)


async def _run_all(
    daemon: Daemon,
    config: EffectsConfig,
    helpers: tuple[SleepController | None, ScreenCapture | None],
) -> None:
    sleep_policy, screen = helpers
    async with asyncio.TaskGroup() as group:
        group.create_task(daemon.run())
        if screen is not None:
            group.create_task(screen.run())
        if sleep_policy is not None:
            group.create_task(sleep_policy.run())
        group.create_task(_power_monitor(daemon, config).run())
        group.create_task(_accent_watcher(daemon, config).run())
        if config.audio is not None:
            capture = AudioCapture(
                config.audio.recorder, Analyzer(BANDS), daemon, RETRY, asyncio.sleep
            )
            group.create_task(capture.run())
        if config.key_socket is not None:
            source = KeySource(config.key_socket, daemon, RETRY, asyncio.sleep)
            group.create_task(source.run())


async def _run_until_stopped(script: Path, config: EffectsConfig) -> None:
    relay = FrameRelay()
    sleep_policy, screen = _sleep_controller(config), _screen_capture(config, relay)
    daemon = _daemon(config, sleep_policy, screen)
    relay.bind(daemon)
    async with Session(daemon, script):
        task = asyncio.create_task(_run_all(daemon, config, (sleep_policy, screen)))
        loop = asyncio.get_running_loop()
        for stop_signal in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(stop_signal, task.cancel)
        try:
            await task
        except asyncio.CancelledError:
            logger.info("stopped")


def _serve(config: EffectsConfig) -> int:
    script = importlib.resources.files("rgb_effects.dbus").joinpath("active_window.js")
    with importlib.resources.as_file(script) as path:
        try:
            asyncio.run(_run_until_stopped(path, config))
        except SessionError:
            logger.exception("session bus link failed")
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    arguments = _arguments(argv)
    try:
        config = load_config(arguments.config)
    except ConfigError:
        logger.exception("invalid configuration")
        return 2
    return _serve(config)


if __name__ == "__main__":
    raise SystemExit(main())

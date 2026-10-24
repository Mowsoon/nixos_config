import argparse
import asyncio
import importlib.resources
import logging
import signal
import time
from pathlib import Path

from rgb_effects.config import EffectsConfig, load_config
from rgb_effects.daemon import Daemon, EventWaiter, Pacing, RetryPolicy, Runtime, Scene
from rgb_effects.ember import Ember
from rgb_effects.errors import ConfigError, SessionError
from rgb_effects.keyboard import OpenRgbKeyboard
from rgb_effects.keys import KeySource
from rgb_effects.power import PowerMonitor
from rgb_effects.session import Session
from rgb_effects.windows import WindowColors

logger = logging.getLogger("rgb_effects")

CLIENT_NAME = "rgb-effects"
RETRY = RetryPolicy(initial_seconds=2.0, maximum_seconds=60.0)
POWER_SUPPLIES = Path("/sys/class/power_supply")


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


def _daemon(config: EffectsConfig) -> Daemon:
    scene = Scene(
        schedule=config.schedule,
        windows=WindowColors(config.window_colors),
        ember=Ember(config.ember.palette, config.ember.duration_seconds),
        pacing=Pacing(
            refresh_seconds=config.refresh_seconds,
            frame_seconds=1 / config.fps,
            battery_frame_seconds=1 / config.battery_fps,
            low_battery_ceiling=config.low_battery.ceiling,
        ),
    )
    runtime = Runtime(
        keyboard=OpenRgbKeyboard(config.server, config.device, CLIENT_NAME),
        clock=SystemClock(),
        waiter=EventWaiter(),
        sleep=asyncio.sleep,
        retry=RETRY,
    )
    return Daemon(scene, runtime)


def _power_monitor(daemon: Daemon, config: EffectsConfig) -> PowerMonitor:
    battery = (POWER_SUPPLIES, config.low_battery.model, config.low_battery.threshold)
    return PowerMonitor(daemon, battery, config.refresh_seconds, RETRY, asyncio.sleep)


async def _run_all(daemon: Daemon, config: EffectsConfig) -> None:
    async with asyncio.TaskGroup() as group:
        group.create_task(daemon.run())
        group.create_task(_power_monitor(daemon, config).run())
        if config.key_socket is not None:
            source = KeySource(config.key_socket, daemon, RETRY, asyncio.sleep)
            group.create_task(source.run())


async def _run_until_stopped(daemon: Daemon, script: Path, config: EffectsConfig) -> None:
    async with Session(daemon, script):
        task = asyncio.create_task(_run_all(daemon, config))
        loop = asyncio.get_running_loop()
        for stop_signal in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(stop_signal, task.cancel)
        try:
            await task
        except asyncio.CancelledError:
            logger.info("stopped")


def _serve(config: EffectsConfig) -> int:
    script = importlib.resources.files("rgb_effects").joinpath("active_window.js")
    with importlib.resources.as_file(script) as path:
        try:
            asyncio.run(_run_until_stopped(_daemon(config), path, config))
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

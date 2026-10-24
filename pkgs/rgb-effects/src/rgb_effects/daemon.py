import asyncio
import logging
import secrets
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from rgb_effects.color import Color
from rgb_effects.ember import Ember
from rgb_effects.errors import KeyboardUnavailableError
from rgb_effects.keymap import led_index_by_code
from rgb_effects.schedule import Schedule
from rgb_effects.windows import WindowColors

logger = logging.getLogger(__name__)

Frame = tuple[Color, ...]
PULSE_STEP = 3
Sleep = Callable[[float], Awaitable[None]]


class Keyboard(Protocol):
    async def connect(self) -> tuple[str, ...]: ...

    async def show(self, colors: Sequence[Color]) -> None: ...

    async def close(self) -> None: ...


class Clock(Protocol):
    def minute_of_day(self) -> float: ...

    def monotonic(self) -> float: ...


class Waiter(Protocol):
    async def wait(self, timeout: float) -> None: ...

    def wake(self) -> None: ...


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    initial_seconds: float
    maximum_seconds: float

    def next_delay(self, current: float) -> float:
        return min(current * 2, self.maximum_seconds)

    def jittered(self, delay: float) -> float:
        return delay * (0.5 + secrets.SystemRandom().random())


@dataclass(frozen=True, slots=True)
class Pacing:
    refresh_seconds: float
    frame_seconds: float
    battery_frame_seconds: float
    low_battery_ceiling: float


@dataclass(frozen=True, slots=True)
class PowerState:
    on_battery: bool
    keyboard_low: bool


@dataclass(frozen=True, slots=True)
class Scene:
    schedule: Schedule
    windows: WindowColors
    ember: Ember
    pacing: Pacing


@dataclass(frozen=True, slots=True)
class Runtime:
    keyboard: Keyboard
    clock: Clock
    waiter: Waiter
    sleep: Sleep
    retry: RetryPolicy


class EventWaiter:
    def __init__(self) -> None:
        self._event = asyncio.Event()

    async def wait(self, timeout: float) -> None:
        try:
            async with asyncio.timeout(timeout):
                await self._event.wait()
        except TimeoutError:
            logger.debug("refresh after %.0f s", timeout)
        finally:
            self._event.clear()

    def wake(self) -> None:
        self._event.set()


def primed(frame: Frame) -> Frame:
    return tuple(color.nudged() for color in frame)


class Daemon:
    def __init__(self, scene: Scene, runtime: Runtime) -> None:
        self._scene = scene
        self._runtime = runtime
        self._led_count = 0
        self._led_index: Mapping[int, int] = {}
        self._power = PowerState(on_battery=False, keyboard_low=False)

    def power_changed(self, state: PowerState) -> None:
        self._power = state
        self._runtime.waiter.wake()

    def window_activated(self, resource_class: str) -> None:
        if self._scene.windows.activate(resource_class):
            self._runtime.waiter.wake()

    def key_pressed(self, code: int | None) -> None:
        now = self._runtime.clock.monotonic()
        if code is None:
            self._scene.ember.ignite_all(self._led_count, now, PULSE_STEP)
        elif code in self._led_index:
            self._scene.ember.ignite(self._led_index[code], now)
        else:
            return
        self._runtime.waiter.wake()

    def render(self) -> Frame:
        minute = self._runtime.clock.minute_of_day()
        schedule = self._scene.schedule
        window = self._scene.windows.current
        if window is None:
            background = schedule.color_at(minute)
        else:
            background = window.scaled(schedule.brightness_at(minute))
        frame = tuple(background for _ in range(self._led_count))
        frame = self._scene.ember.overlay(frame, self._runtime.clock.monotonic())
        if not self._power.keyboard_low:
            return frame
        ceiling = self._scene.pacing.low_battery_ceiling
        return tuple(color.capped(ceiling) for color in frame)

    def _pause_seconds(self) -> float:
        pacing = self._scene.pacing
        if not self._scene.ember.active(self._runtime.clock.monotonic()):
            return pacing.refresh_seconds
        if self._power.on_battery:
            return pacing.battery_frame_seconds
        return pacing.frame_seconds

    async def run(self) -> None:
        retry = self._runtime.retry
        delay = retry.initial_seconds
        try:
            while True:
                try:
                    await self._attach()
                    delay = retry.initial_seconds
                    await self._serve()
                except KeyboardUnavailableError as err:
                    logger.warning(
                        "%s (%s), retrying in %.0f s", err, err.__cause__ or "no cause", delay
                    )
                    await self._runtime.sleep(retry.jittered(delay))
                    delay = retry.next_delay(delay)
        finally:
            await self._runtime.keyboard.close()

    async def _attach(self) -> None:
        led_names = await self._runtime.keyboard.connect()
        self._led_count = len(led_names)
        self._led_index = led_index_by_code(led_names)
        logger.info("connected to the keyboard with %d LEDs", self._led_count)

    async def _serve(self) -> None:
        keyboard = self._runtime.keyboard
        frame = self.render()
        await keyboard.show(primed(frame))
        await keyboard.show(frame)
        while True:
            await self._runtime.waiter.wait(self._pause_seconds())
            current = self.render()
            if current != frame:
                await keyboard.show(current)
                frame = current

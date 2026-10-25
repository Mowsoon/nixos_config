import asyncio
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from rgb_effects.color import Color
from rgb_effects.errors import KeyboardUnavailableError
from rgb_effects.render.compose import FrameRequest
from rgb_effects.render.geometry import KeyboardLayout
from rgb_effects.render.palette import PaletteInputs
from rgb_effects.render.schedule import Schedule
from rgb_effects.render.windows import WindowColors
from rgb_effects.retry import RetryPolicy, Sleep
from rgb_effects.sdk.keymap import led_index_by_code
from rgb_effects.sources.audio.analysis import Features
from rgb_effects.sources.keys.listener import KeyEvent
from rgb_effects.sources.power import PowerState

logger = logging.getLogger(__name__)

Frame = tuple[Color, ...]
MIN_PACKETS_PER_FRAME = 2
ENTER_CODES = frozenset({28, 96})


class HudControl(Protocol):
    def key_down(self, code: int, now: float) -> None: ...

    def key_up(self, code: int) -> None: ...

    def start_focus(self, seconds: float, now: float) -> None: ...

    def stop_focus(self) -> None: ...


class Renderer(Protocol):
    @property
    def hud(self) -> HudControl: ...

    def frame(self, request: FrameRequest) -> Frame: ...

    def key_pressed(self, led: int | None, now: float) -> None: ...

    def pulse(self, now: float) -> None: ...

    def enter(self) -> None: ...

    def audio_features(self, features: Features, now: float) -> None: ...

    def screen_frame(self, frame: NDArray[np.uint8], now: float) -> None: ...

    def notification(self, color: Color | None, now: float) -> None: ...

    def sound_active(self, now: float) -> bool: ...

    def awake(self, now: float) -> bool: ...


EngineFactory = Callable[[KeyboardLayout], Renderer]


class Keyboard(Protocol):
    async def connect(self) -> KeyboardLayout: ...

    async def show(self, colors: Sequence[Color]) -> None: ...

    async def close(self) -> None: ...


class Clock(Protocol):
    def minute_of_day(self) -> float: ...

    def monotonic(self) -> float: ...


class SleepPolicy(Protocol):
    def want(self, allow_sleep: bool) -> None: ...


class Screen(Protocol):
    @property
    def active(self) -> bool: ...

    def fullscreen_changed(self, fullscreen: bool) -> None: ...

    def power_changed(self, on_battery: bool) -> None: ...

    def grant(self) -> None: ...

    def revoke(self) -> None: ...


class Waiter(Protocol):
    async def wait(self, timeout: float) -> None: ...

    def wake(self) -> None: ...


@dataclass(frozen=True, slots=True)
class Pacing:
    refresh_seconds: float
    frame_seconds: float
    battery_frame_seconds: float
    low_battery_ceiling: float
    packets_per_second: int


@dataclass(frozen=True, slots=True)
class Scene:
    schedule: Schedule
    windows: WindowColors
    engine_factory: EngineFactory
    pacing: Pacing
    physics_ceiling: float


@dataclass(frozen=True, slots=True)
class Runtime:
    keyboard: Keyboard
    clock: Clock
    waiter: Waiter
    sleep: Sleep
    retry: RetryPolicy
    sleep_policy: SleepPolicy | None = None
    screen: Screen | None = None


class EventWaiter:
    def __init__(self) -> None:
        self._event = asyncio.Event()

    async def wait(self, timeout: float) -> None:
        try:
            async with asyncio.timeout(timeout):
                await self._event.wait()
        except TimeoutError:
            logger.debug("refresh after %.2f s", timeout)
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
        self._engine: Renderer | None = None
        self._led_index: Mapping[int, int] = {}
        self._power = PowerState(on_battery=False, keyboard_low=False)
        self._accent: Color | None = None

    def window_activated(self, resource_class: str) -> None:
        if self._scene.windows.activate(resource_class):
            self._runtime.waiter.wake()

    def accent_changed(self, color: Color | None) -> None:
        self._accent = color
        self._runtime.waiter.wake()

    def power_changed(self, state: PowerState) -> None:
        self._power = state
        if self._runtime.screen is not None:
            self._runtime.screen.power_changed(state.on_battery)
        self._runtime.waiter.wake()

    def fullscreen_changed(self, fullscreen: bool) -> None:
        if self._runtime.screen is not None:
            self._runtime.screen.fullscreen_changed(fullscreen)

    def screen_grant(self) -> None:
        if self._runtime.screen is not None:
            self._runtime.screen.grant()

    def screen_revoke(self) -> None:
        if self._runtime.screen is not None:
            self._runtime.screen.revoke()

    def key_event(self, event: KeyEvent) -> None:
        engine = self._engine
        if engine is None:
            return
        now = self._runtime.clock.monotonic()
        if event.code is None:
            engine.pulse(now)
        elif event.pressed:
            self._press(engine, event.code, now)
        else:
            engine.hud.key_up(event.code)
        self._runtime.waiter.wake()

    def audio_features(self, features: Features) -> None:
        engine = self._engine
        if engine is not None:
            engine.audio_features(features, self._runtime.clock.monotonic())

    def screen_frame(self, frame: NDArray[np.uint8]) -> None:
        engine = self._engine
        if engine is not None:
            engine.screen_frame(frame, self._runtime.clock.monotonic())

    def notification_shown(self, app_name: str) -> None:
        engine = self._engine
        if engine is not None:
            color = self._scene.windows.color_for(app_name)
            engine.notification(color, self._runtime.clock.monotonic())
            self._runtime.waiter.wake()

    def focus_started(self, seconds: float) -> None:
        engine = self._engine
        if engine is not None:
            engine.hud.start_focus(seconds, self._runtime.clock.monotonic())
            self._runtime.waiter.wake()

    def focus_stopped(self) -> None:
        engine = self._engine
        if engine is not None:
            engine.hud.stop_focus()
            self._runtime.waiter.wake()

    def _press(self, engine: Renderer, code: int, now: float) -> None:
        engine.hud.key_down(code, now)
        engine.key_pressed(self._led_index.get(code), now)
        if code in ENTER_CODES:
            engine.enter()

    def render(self) -> Frame:
        engine = self._engine
        if engine is None:
            return ()
        self._apply_sleep_policy(engine)
        return engine.frame(self._request())

    def _apply_sleep_policy(self, engine: Renderer) -> None:
        policy = self._runtime.sleep_policy
        if policy is None:
            return
        strict = self._power.on_battery or self._power.keyboard_low
        playing = engine.sound_active(self._runtime.clock.monotonic())
        watching = self._runtime.screen is not None and self._runtime.screen.active
        policy.want(strict or not (playing or watching))

    def _request(self) -> FrameRequest:
        clock, schedule, pacing = self._runtime.clock, self._scene.schedule, self._scene.pacing
        minute = clock.minute_of_day()
        inputs = PaletteInputs(
            hue=schedule.hue_at(minute),
            ceiling=schedule.brightness_at(minute),
            physics_ceiling=self._scene.physics_ceiling,
            window=self._scene.windows.current,
            accent=self._accent,
        )
        frame_seconds = self._frame_seconds()
        packets = max(MIN_PACKETS_PER_FRAME, int(pacing.packets_per_second * frame_seconds))
        cap = pacing.low_battery_ceiling if self._power.keyboard_low else None
        return FrameRequest(clock.monotonic(), minute, inputs, packets, cap)

    def _frame_seconds(self) -> float:
        pacing = self._scene.pacing
        return pacing.battery_frame_seconds if self._power.on_battery else pacing.frame_seconds

    def _pause_seconds(self) -> float:
        return self._frame_seconds() if self._awake() else self._scene.pacing.refresh_seconds

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
        layout = await self._runtime.keyboard.connect()
        self._led_index = led_index_by_code(layout.led_names)
        self._engine = self._scene.engine_factory(layout)
        logger.info("connected to the keyboard with %d LEDs", len(layout.led_names))

    async def _serve(self) -> None:
        keyboard = self._runtime.keyboard
        frame = self.render()
        await keyboard.show(primed(frame))
        await keyboard.show(frame)
        while True:
            await self._runtime.waiter.wait(self._pause_seconds())
            current = self.render()
            if current != frame or self._awake():
                await keyboard.show(current)
                frame = current

    def _awake(self) -> bool:
        engine = self._engine
        return engine is not None and engine.awake(self._runtime.clock.monotonic())

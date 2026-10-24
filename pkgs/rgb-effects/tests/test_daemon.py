from collections.abc import Callable, Sequence

import pytest

from rgb_effects.color import Color
from evdev import ecodes

from rgb_effects.daemon import (
    Daemon,
    EventWaiter,
    Pacing,
    PowerState,
    RetryPolicy,
    Runtime,
    Scene,
    primed,
)
from rgb_effects.ember import Ember
from rgb_effects.errors import KeyboardUnavailableError
from rgb_effects.schedule import Keyframe, Schedule
from rgb_effects.windows import WindowColors

LED_NAMES = ("Key: Escape", "Key: A", "Logo")
LED_COUNT = len(LED_NAMES)
HOT = Color(255, 255, 255)
COLD = Color(90, 0, 0)
DAY = Schedule(
    (
        Keyframe(minute=0, color=Color(0, 0, 100), brightness=1.0),
        Keyframe(minute=720, color=Color(100, 0, 0), brightness=0.5),
    )
)
RETRY = RetryPolicy(initial_seconds=1.0, maximum_seconds=4.0)
FIREFOX = Color(200, 100, 50)


class StopLoop(Exception):
    pass


class FakeKeyboard:
    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.frames: list[tuple[Color, ...]] = []
        self.closed = False

    async def connect(self) -> tuple[str, ...]:
        if self.failures > 0:
            self.failures -= 1
            raise KeyboardUnavailableError("server down")
        return LED_NAMES

    async def show(self, colors: Sequence[Color]) -> None:
        self.frames.append(tuple(colors))

    async def close(self) -> None:
        self.closed = True


class FakeClock:
    def __init__(self, minutes: list[float]) -> None:
        self.minutes = minutes

    def minute_of_day(self) -> float:
        return self.minutes.pop(0) if len(self.minutes) > 1 else self.minutes[0]

    def monotonic(self) -> float:
        return 100.0


class CountingSleep:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)
        if len(self.delays) >= self.limit:
            raise StopLoop


class ScriptedWaiter:
    def __init__(self, limit: int, on_wait: list[str] | None = None) -> None:
        self.limit = limit
        self.calls = 0
        self.woken = 0
        self.on_wait = on_wait or []
        self.daemon: Daemon | None = None

    async def wait(self, timeout: float) -> None:
        self.calls += 1
        if self.on_wait and self.daemon is not None:
            self.daemon.window_activated(self.on_wait.pop(0))
        if self.calls >= self.limit:
            raise StopLoop

    def wake(self) -> None:
        self.woken += 1


class RecordingWaiter(ScriptedWaiter):
    def __init__(self, limit: int) -> None:
        super().__init__(limit)
        self.timeouts: list[float] = []
        self.on_first: Callable[[], None] = lambda: None

    async def wait(self, timeout: float) -> None:
        self.timeouts.append(timeout)
        if len(self.timeouts) == 1:
            self.on_first()
        await super().wait(timeout)


def _daemon(
    keyboard: FakeKeyboard,
    clock: FakeClock,
    waiter: ScriptedWaiter,
    sleep: CountingSleep | None = None,
) -> Daemon:
    pacing = Pacing(60.0, 0.05, 0.1, 0.4)
    scene = Scene(DAY, WindowColors({"firefox": FIREFOX}), Ember((HOT, COLD), 1.0), pacing)
    runtime = Runtime(keyboard, clock, waiter, sleep or CountingSleep(100), RETRY)
    daemon = Daemon(scene, runtime)
    waiter.daemon = daemon
    return daemon


def _uniform(color: Color) -> tuple[Color, ...]:
    return tuple(color for _ in range(LED_COUNT))


async def test_run_sends_primed_then_real_frame_on_connect() -> None:
    keyboard = FakeKeyboard()
    with pytest.raises(StopLoop):
        await _daemon(keyboard, FakeClock([0]), ScriptedWaiter(1)).run()
    expected = _uniform(Color(0, 0, 100))
    assert keyboard.frames == [primed(expected), expected]


async def test_run_skips_unchanged_frames() -> None:
    keyboard = FakeKeyboard()
    with pytest.raises(StopLoop):
        await _daemon(keyboard, FakeClock([0]), ScriptedWaiter(3)).run()
    assert len(keyboard.frames) == 2


async def test_run_sends_frame_when_schedule_moves() -> None:
    keyboard = FakeKeyboard()
    with pytest.raises(StopLoop):
        await _daemon(keyboard, FakeClock([0, 720]), ScriptedWaiter(2)).run()
    assert keyboard.frames[-1] == _uniform(Color(50, 0, 0))


async def test_run_paints_active_window_color_at_schedule_brightness() -> None:
    keyboard = FakeKeyboard()
    waiter = ScriptedWaiter(2, on_wait=["firefox"])
    with pytest.raises(StopLoop):
        await _daemon(keyboard, FakeClock([720]), waiter).run()
    assert keyboard.frames[-1] == _uniform(FIREFOX.scaled(0.5))


async def test_window_activation_wakes_the_waiter() -> None:
    waiter = ScriptedWaiter(1)
    _daemon(FakeKeyboard(), FakeClock([0]), waiter).window_activated("firefox")
    assert waiter.woken == 1


async def test_unknown_window_after_known_one_restores_schedule() -> None:
    keyboard = FakeKeyboard()
    waiter = ScriptedWaiter(3, on_wait=["firefox", "org.kde.dolphin"])
    with pytest.raises(StopLoop):
        await _daemon(keyboard, FakeClock([0]), waiter).run()
    assert keyboard.frames[-1] == _uniform(Color(0, 0, 100))


async def test_run_retries_with_growing_delay_until_connected() -> None:
    sleep = CountingSleep(3)
    with pytest.raises(StopLoop):
        await _daemon(FakeKeyboard(failures=3), FakeClock([0]), ScriptedWaiter(5), sleep).run()
    bounds = [(0.5, 1.5), (1.0, 3.0), (2.0, 6.0)]
    assert all(low <= delay <= high for delay, (low, high) in zip(sleep.delays, bounds))


async def test_run_closes_keyboard_when_stopped() -> None:
    keyboard = FakeKeyboard()
    with pytest.raises(StopLoop):
        await _daemon(keyboard, FakeClock([0]), ScriptedWaiter(1)).run()
    assert keyboard.closed


async def test_event_waiter_returns_early_when_woken() -> None:
    waiter = EventWaiter()
    waiter.wake()
    await waiter.wait(3600)


async def test_event_waiter_returns_after_timeout() -> None:
    await EventWaiter().wait(0.01)


@pytest.mark.parametrize(("current", "expected"), [(1.0, 2.0), (3.0, 4.0), (4.0, 4.0)])
def test_retry_delay_doubles_up_to_maximum(current: float, expected: float) -> None:
    assert RETRY.next_delay(current) == expected


def test_retry_jitter_stays_within_half_and_one_and_a_half() -> None:
    assert 1.0 <= RETRY.jittered(2.0) <= 3.0


async def test_key_press_lights_the_mapped_led() -> None:
    keyboard = FakeKeyboard()
    waiter = ScriptedWaiter(1)
    daemon = _daemon(keyboard, FakeClock([0]), waiter)
    with pytest.raises(StopLoop):
        await daemon.run()
    daemon.key_pressed(ecodes.KEY_Q)
    assert daemon.render()[1] == HOT


def test_unmapped_key_press_does_not_wake_the_waiter() -> None:
    waiter = ScriptedWaiter(1)
    _daemon(FakeKeyboard(), FakeClock([0]), waiter).key_pressed(ecodes.KEY_F24)
    assert waiter.woken == 0


async def test_pulse_lights_every_led() -> None:
    keyboard = FakeKeyboard()
    daemon = _daemon(keyboard, FakeClock([0]), ScriptedWaiter(1))
    with pytest.raises(StopLoop):
        await daemon.run()
    daemon.key_pressed(None)
    assert daemon.render() == (COLD, COLD, COLD)


async def test_glowing_key_switches_waiting_to_frame_rate() -> None:
    keyboard = FakeKeyboard()
    waiter = RecordingWaiter(2)
    daemon = _daemon(keyboard, FakeClock([0]), waiter)
    waiter.on_first = lambda: daemon.key_pressed(ecodes.KEY_ESC)
    with pytest.raises(StopLoop):
        await daemon.run()
    assert waiter.timeouts == [60.0, 0.05]


async def test_glowing_key_on_battery_uses_battery_frame_rate() -> None:
    waiter = RecordingWaiter(2)
    daemon = _daemon(FakeKeyboard(), FakeClock([0]), waiter)
    daemon.power_changed(PowerState(on_battery=True, keyboard_low=False))

    def press() -> None:
        daemon.key_pressed(ecodes.KEY_ESC)

    waiter.on_first = press
    with pytest.raises(StopLoop):
        await daemon.run()
    assert waiter.timeouts == [60.0, 0.1]


async def test_low_keyboard_battery_caps_brightness() -> None:
    keyboard = FakeKeyboard()
    daemon = _daemon(keyboard, FakeClock([0]), ScriptedWaiter(1))
    with pytest.raises(StopLoop):
        await daemon.run()
    daemon.power_changed(PowerState(on_battery=False, keyboard_low=True))
    daemon.key_pressed(ecodes.KEY_Q)
    assert daemon.render()[1] == Color(102, 102, 102)


def test_power_change_wakes_the_waiter() -> None:
    waiter = ScriptedWaiter(1)
    _daemon(FakeKeyboard(), FakeClock([0]), waiter).power_changed(PowerState(True, False))
    assert waiter.woken == 1

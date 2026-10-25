from collections.abc import Callable, Sequence

import pytest
from evdev import ecodes

from rgb_effects.color import Color
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
from rgb_effects.render.compose import FrameRequest
from rgb_effects.render.geometry import KeyboardLayout
from rgb_effects.errors import KeyboardUnavailableError
from rgb_effects.sources.keys.listener import KeyEvent
from rgb_effects.render.schedule import Keyframe, Schedule
from rgb_effects.render.windows import WindowColors

LAYOUT = KeyboardLayout(("Key: Escape", "Key: A", "Logo"), ((0, 1),))
DAY = Schedule((Keyframe(minute=0, color=Color(0, 0, 100), brightness=0.5),))
RETRY = RetryPolicy(initial_seconds=1.0, maximum_seconds=4.0)
PACING = Pacing(60.0, 0.05, 0.1, 0.4, 180)
FIREFOX = Color(200, 100, 50)


class StopLoop(Exception):
    pass


class FakeHud:
    def __init__(self) -> None:
        self.down: list[int] = []
        self.up: list[int] = []
        self.focus: list[float | None] = []

    def key_down(self, code: int, now: float) -> None:
        self.down.append(code)

    def key_up(self, code: int) -> None:
        self.up.append(code)

    def start_focus(self, seconds: float, now: float) -> None:
        self.focus.append(seconds)

    def stop_focus(self) -> None:
        self.focus.append(None)


class FakeEngine:
    def __init__(self) -> None:
        self.hud = FakeHud()
        self.requests: list[FrameRequest] = []
        self.presses: list[int | None] = []
        self.pulses = 0
        self.enters = 0
        self.is_awake = True
        self.constant = False
        self.playing = False
        self.notices: list[Color | None] = []
        self.audio: list[object] = []

    def frame(self, request: FrameRequest) -> tuple[Color, ...]:
        self.requests.append(request)
        shade = 1 if self.constant else len(self.requests) % 256
        return (Color(shade, 0, 0), Color(0, shade, 0), Color(0, 0, shade))

    def key_pressed(self, led: int | None, now: float) -> None:
        self.presses.append(led)

    def pulse(self, now: float) -> None:
        self.pulses += 1

    def enter(self) -> None:
        self.enters += 1

    def audio_features(self, features: object, now: float) -> None:
        self.audio.append(features)

    def awake(self, now: float) -> bool:
        return self.is_awake

    def sound_active(self, now: float) -> bool:
        return self.playing

    def notification(self, color: Color | None, now: float) -> None:
        self.notices.append(color)


class FakeKeyboard:
    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.frames: list[tuple[Color, ...]] = []
        self.closed = False

    async def connect(self) -> KeyboardLayout:
        if self.failures > 0:
            self.failures -= 1
            raise KeyboardUnavailableError("server down")
        return LAYOUT

    async def show(self, colors: Sequence[Color]) -> None:
        self.frames.append(tuple(colors))

    async def close(self) -> None:
        self.closed = True


class FakeClock:
    def minute_of_day(self) -> float:
        return 0.0

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
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.timeouts: list[float] = []
        self.woken = 0
        self.on_first: Callable[[], None] = lambda: None

    async def wait(self, timeout: float) -> None:
        self.timeouts.append(timeout)
        if len(self.timeouts) == 1:
            self.on_first()
        if len(self.timeouts) >= self.limit:
            raise StopLoop

    def wake(self) -> None:
        self.woken += 1


class FakeScreen:
    def __init__(self) -> None:
        self.active = False
        self.events: list[object] = []

    def fullscreen_changed(self, fullscreen: bool) -> None:
        self.events.append(("fullscreen", fullscreen))

    def power_changed(self, on_battery: bool) -> None:
        self.events.append(("battery", on_battery))

    def grant(self) -> None:
        self.events.append("grant")

    def revoke(self) -> None:
        self.events.append("revoke")


class FakePolicy:
    def __init__(self) -> None:
        self.wanted: list[bool] = []

    def want(self, allow_sleep: bool) -> None:
        self.wanted.append(allow_sleep)


def _daemon(
    keyboard: FakeKeyboard,
    waiter: ScriptedWaiter,
    engine: FakeEngine,
    sleep: CountingSleep,
    policy: FakePolicy | None = None,
    screen: FakeScreen | None = None,
) -> Daemon:
    scene = Scene(DAY, WindowColors({"firefox": FIREFOX}), lambda layout: engine, PACING, 0.6)
    return Daemon(scene, Runtime(keyboard, FakeClock(), waiter, sleep, RETRY, policy, screen))


async def _run(daemon: Daemon) -> None:
    with pytest.raises(StopLoop):
        await daemon.run()


async def test_run_sends_primed_then_real_frame_on_connect() -> None:
    keyboard, engine = FakeKeyboard(), FakeEngine()
    await _run(_daemon(keyboard, ScriptedWaiter(1), engine, CountingSleep(9)))
    first = (Color(1, 0, 0), Color(0, 1, 0), Color(0, 0, 1))
    assert keyboard.frames == [primed(first), first]


async def test_run_sends_each_new_frame() -> None:
    keyboard = FakeKeyboard()
    await _run(_daemon(keyboard, ScriptedWaiter(3), FakeEngine(), CountingSleep(9)))
    assert len(keyboard.frames) == 4


async def test_awake_engine_resends_an_unchanged_frame() -> None:
    keyboard, engine = FakeKeyboard(), FakeEngine()
    engine.constant = True
    await _run(_daemon(keyboard, ScriptedWaiter(3), engine, CountingSleep(9)))
    assert len(keyboard.frames) == 4


async def test_sleeping_engine_does_not_resend_an_unchanged_frame() -> None:
    keyboard, engine = FakeKeyboard(), FakeEngine()
    engine.constant, engine.is_awake = True, False
    await _run(_daemon(keyboard, ScriptedWaiter(3), engine, CountingSleep(9)))
    assert len(keyboard.frames) == 2


async def test_awake_engine_waits_one_frame() -> None:
    waiter = ScriptedWaiter(2)
    await _run(_daemon(FakeKeyboard(), waiter, FakeEngine(), CountingSleep(9)))
    assert waiter.timeouts == [0.05, 0.05]


async def test_sleeping_engine_waits_the_refresh_interval() -> None:
    waiter, engine = ScriptedWaiter(1), FakeEngine()
    engine.is_awake = False
    await _run(_daemon(FakeKeyboard(), waiter, engine, CountingSleep(9)))
    assert waiter.timeouts == [60.0]


async def test_battery_lowers_frame_rate_and_raises_packet_budget() -> None:
    waiter, engine = ScriptedWaiter(2), FakeEngine()
    daemon = _daemon(FakeKeyboard(), waiter, engine, CountingSleep(9))
    daemon.power_changed(PowerState(on_battery=True, keyboard_low=False))
    await _run(daemon)
    assert (waiter.timeouts[-1], engine.requests[-1].max_packets) == (0.1, 18)


async def test_low_keyboard_battery_requests_a_brightness_cap() -> None:
    engine = FakeEngine()
    daemon = _daemon(FakeKeyboard(), ScriptedWaiter(1), engine, CountingSleep(9))
    daemon.power_changed(PowerState(on_battery=False, keyboard_low=True))
    await _run(daemon)
    assert engine.requests[-1].brightness_cap == 0.4


async def test_active_window_and_accent_feed_the_palette() -> None:
    engine = FakeEngine()
    daemon = _daemon(FakeKeyboard(), ScriptedWaiter(1), engine, CountingSleep(9))
    daemon.window_activated("firefox")
    daemon.accent_changed(Color(1, 2, 3))
    await _run(daemon)
    inputs = engine.requests[-1].inputs
    assert (inputs.window, inputs.accent, inputs.ceiling) == (FIREFOX, Color(1, 2, 3), 0.5)


async def test_key_press_reaches_the_engine_with_its_led() -> None:
    waiter, engine = ScriptedWaiter(2), FakeEngine()
    daemon = _daemon(FakeKeyboard(), waiter, engine, CountingSleep(9))
    waiter.on_first = lambda: daemon.key_event(KeyEvent(ecodes.KEY_Q, True))
    await _run(daemon)
    assert engine.presses == [1]


async def test_enter_starts_the_sweep() -> None:
    waiter, engine = ScriptedWaiter(2), FakeEngine()
    daemon = _daemon(FakeKeyboard(), waiter, engine, CountingSleep(9))
    waiter.on_first = lambda: daemon.key_event(KeyEvent(ecodes.KEY_ENTER, True))
    await _run(daemon)
    assert engine.enters == 1


async def test_release_reaches_only_the_hud() -> None:
    waiter, engine = ScriptedWaiter(2), FakeEngine()
    daemon = _daemon(FakeKeyboard(), waiter, engine, CountingSleep(9))
    waiter.on_first = lambda: daemon.key_event(KeyEvent(ecodes.KEY_LEFTCTRL, False))
    await _run(daemon)
    assert (engine.presses, engine.hud.up) == ([], [ecodes.KEY_LEFTCTRL])


async def test_press_reaches_the_hud() -> None:
    waiter, engine = ScriptedWaiter(2), FakeEngine()
    daemon = _daemon(FakeKeyboard(), waiter, engine, CountingSleep(9))
    waiter.on_first = lambda: daemon.key_event(KeyEvent(ecodes.KEY_LEFTCTRL, True))
    await _run(daemon)
    assert engine.hud.down == [ecodes.KEY_LEFTCTRL]


async def test_focus_requests_reach_the_hud() -> None:
    waiter, engine = ScriptedWaiter(2), FakeEngine()
    daemon = _daemon(FakeKeyboard(), waiter, engine, CountingSleep(9))

    def focus() -> None:
        daemon.focus_started(1500.0)
        daemon.focus_stopped()

    waiter.on_first = focus
    await _run(daemon)
    assert engine.hud.focus == [1500.0, None]


async def test_pulse_reaches_the_engine() -> None:
    waiter, engine = ScriptedWaiter(2), FakeEngine()
    daemon = _daemon(FakeKeyboard(), waiter, engine, CountingSleep(9))
    waiter.on_first = lambda: daemon.key_event(KeyEvent(None, True))
    await _run(daemon)
    assert engine.pulses == 1


async def test_audio_features_reach_the_engine() -> None:
    waiter, engine = ScriptedWaiter(2), FakeEngine()
    daemon = _daemon(FakeKeyboard(), waiter, engine, CountingSleep(9))
    waiter.on_first = lambda: daemon.audio_features("features")
    await _run(daemon)
    assert engine.audio == ["features"]


async def test_playing_sound_suspends_keyboard_sleep() -> None:
    engine, policy = FakeEngine(), FakePolicy()
    engine.playing = True
    await _run(_daemon(FakeKeyboard(), ScriptedWaiter(1), engine, CountingSleep(9), policy))
    assert set(policy.wanted) == {False}


async def test_silence_allows_keyboard_sleep() -> None:
    engine, policy = FakeEngine(), FakePolicy()
    await _run(_daemon(FakeKeyboard(), ScriptedWaiter(1), engine, CountingSleep(9), policy))
    assert set(policy.wanted) == {True}


@pytest.mark.parametrize(
    "state", [PowerState(on_battery=True, keyboard_low=False), PowerState(False, True)]
)
async def test_battery_forces_keyboard_sleep_even_with_sound(state: PowerState) -> None:
    engine, policy = FakeEngine(), FakePolicy()
    engine.playing = True
    daemon = _daemon(FakeKeyboard(), ScriptedWaiter(1), engine, CountingSleep(9), policy)
    daemon.power_changed(state)
    await _run(daemon)
    assert set(policy.wanted) == {True}


async def test_notification_reaches_the_engine_with_its_color() -> None:
    waiter, engine = ScriptedWaiter(2), FakeEngine()
    daemon = _daemon(FakeKeyboard(), waiter, engine, CountingSleep(9))

    def notify() -> None:
        daemon.notification_shown("Firefox")
        daemon.notification_shown("notify-send")

    waiter.on_first = notify
    await _run(daemon)
    assert engine.notices == [FIREFOX, None]


def test_screen_events_reach_the_capture() -> None:
    screen = FakeScreen()
    daemon = _daemon(
        FakeKeyboard(), ScriptedWaiter(1), FakeEngine(), CountingSleep(9), None, screen
    )
    daemon.fullscreen_changed(True)
    daemon.power_changed(PowerState(on_battery=True, keyboard_low=False))
    daemon.screen_grant()
    daemon.screen_revoke()
    assert screen.events == [("fullscreen", True), ("battery", True), "grant", "revoke"]


async def test_screen_capture_suspends_keyboard_sleep() -> None:
    screen, policy = FakeScreen(), FakePolicy()
    screen.active = True
    daemon = _daemon(
        FakeKeyboard(), ScriptedWaiter(1), FakeEngine(), CountingSleep(9), policy, screen
    )
    await _run(daemon)
    assert set(policy.wanted) == {False}


def test_key_press_before_connection_is_ignored() -> None:
    waiter = ScriptedWaiter(1)
    daemon = _daemon(FakeKeyboard(), waiter, FakeEngine(), CountingSleep(9))
    daemon.key_event(KeyEvent(ecodes.KEY_Q, True))
    assert waiter.woken == 0


async def test_run_retries_with_growing_delay_until_connected() -> None:
    sleep = CountingSleep(3)
    await _run(_daemon(FakeKeyboard(failures=3), ScriptedWaiter(5), FakeEngine(), sleep))
    bounds = [(0.5, 1.5), (1.0, 3.0), (2.0, 6.0)]
    assert all(low <= delay <= high for delay, (low, high) in zip(sleep.delays, bounds))


async def test_run_closes_keyboard_when_stopped() -> None:
    keyboard = FakeKeyboard()
    await _run(_daemon(keyboard, ScriptedWaiter(1), FakeEngine(), CountingSleep(9)))
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

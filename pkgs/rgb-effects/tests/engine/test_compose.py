from collections import Counter

import numpy as np

from rgb_effects.color import Color
from rgb_effects.engine.activity import Activity
from rgb_effects.engine.background import Background, BackgroundSettings
from rgb_effects.engine.budget import packet_cost
from rgb_effects.engine.compose import Engine, EngineSettings, FrameRequest, capped, hud_table
from rgb_effects.engine.geometry import KeyboardLayout, build_geometry
from rgb_effects.engine.hud import LEFT_ALT, LEFT_CTRL, Hud, HudSettings, Overlay
from rgb_effects.engine.palette import PaletteInputs
from rgb_effects.engine.physics import Physics, PhysicsSettings

NAMES = tuple(f"Key: {index}" for index in range(126))
LAYOUT = KeyboardLayout(NAMES, tuple(tuple(r * 21 + c for c in range(21)) for r in range(6)))
HUD = HudSettings(
    {"ctrl": {"edit": ("7", "8")}, "alt": {"window": ("9",)}},
    {"edit": Color(0, 255, 255), "window": Color(255, 0, 255)},
    0.25,
    0.5,
)
INPUTS = PaletteInputs(Color(255, 255, 255), 0.3, 0.6, Color(0, 0, 255), Color(255, 0, 0))


def _engine() -> Engine:
    geometry = build_geometry(LAYOUT)
    return Engine(
        geometry,
        Background(geometry.shape, BackgroundSettings(idle_seconds=30.0), 3),
        Physics(geometry.shape, PhysicsSettings()),
        Activity(3.0, 0.0),
        Hud(HUD, NAMES),
        EngineSettings(palette_size=8, sleep_seconds=300.0, falling_rate=1.25),
    )


def _request(now: float, packets: int = 9) -> FrameRequest:
    return FrameRequest(now, 600.0, INPUTS, packets, None)


def _luma(color: Color) -> int:
    return color.red + color.green + color.blue


def test_first_frame_paints_every_led() -> None:
    assert len(_engine().frame(_request(0.0))) == 126


def test_frame_uses_at_most_palette_size_colors() -> None:
    assert len(set(_engine().frame(_request(0.0)))) <= 8


def test_pressed_key_is_the_brightest_led() -> None:
    engine = _engine()
    engine.frame(_request(0.0))
    engine.key_pressed(30, 1.0)
    frame = engine.frame(_request(1.0))
    assert _luma(frame[30]) == max(_luma(color) for color in frame)


def test_pressed_key_is_brighter_than_the_night_background() -> None:
    engine = _engine()
    before = engine.frame(_request(0.0))
    engine.key_pressed(30, 1.0)
    assert _luma(engine.frame(_request(1.0))[30]) > _luma(before[30])


def test_later_frames_respect_the_packet_budget() -> None:
    engine = _engine()
    first = engine.frame(_request(0.0))
    second = engine.frame(_request(30.0, packets=2))
    counts = Counter(b for a, b in zip(first, second, strict=True) if a != b)
    assert packet_cost(counts) <= 2


def test_held_ctrl_paints_its_bindings_first() -> None:
    engine = _engine()
    engine.frame(_request(0.0))
    engine.hud.key_down(LEFT_CTRL, 1.0)
    frame = engine.frame(_request(1.0, packets=2))
    assert frame[7] == frame[8] == Color(0, 255, 255)


def test_modifier_toggles_stay_within_the_packet_budget() -> None:
    engine = _engine()
    previous = engine.frame(_request(0.0))
    costs = []
    for step in range(1, 30):
        now = step * 0.05
        if step == 5:
            engine.hud.key_down(LEFT_CTRL, now)
        if step == 15:
            engine.hud.key_up(LEFT_CTRL)
        frame = engine.frame(_request(now))
        costs.append(
            packet_cost(Counter(b for a, b in zip(previous, frame, strict=True) if a != b))
        )
        previous = frame
    assert max(costs) <= 9


def test_mask_completes_within_a_few_frames() -> None:
    engine = _engine()
    engine.frame(_request(0.0))
    engine.hud.key_down(LEFT_CTRL, 0.05)
    frames = [engine.frame(_request(0.05 * step)) for step in range(1, 6)]
    assert frames[-1] == frames[-2]


def test_switching_from_ctrl_to_alt_keeps_rendering() -> None:
    engine = _engine()
    for step in range(40):
        now = step * 0.05
        if step == 5:
            engine.hud.key_down(LEFT_CTRL, now)
        if step == 15:
            engine.hud.key_up(LEFT_CTRL)
            engine.hud.key_down(LEFT_ALT, now)
        if step == 25:
            engine.hud.key_up(LEFT_ALT)
        frame = engine.frame(_request(now))
    assert len(frame) == 126


def test_hud_table_keeps_the_palette_size() -> None:
    table = np.ones((8, 3), dtype=np.float32)
    overlay = Overlay(0.25, {0: np.array([0.0, 1.0, 1.0], dtype=np.float32)})
    assert hud_table(table, overlay).shape == (8, 3)


def test_engine_stays_awake_while_a_modifier_is_held() -> None:
    engine = _engine()
    engine.hud.key_down(LEFT_CTRL, 0.0)
    assert engine.awake(1000.0)


def test_engine_sleeps_after_the_sleep_delay() -> None:
    engine = _engine()
    engine.key_pressed(None, 10.0)
    assert engine.awake(100.0) and not engine.awake(400.0)


def test_capped_limits_the_brightest_channel() -> None:
    colors = np.array([[1.0, 0.5, 0.0], [0.2, 0.1, 0.0]], dtype=np.float32)
    assert np.allclose(capped(colors, 0.4), [[0.4, 0.2, 0.0], [0.2, 0.1, 0.0]])

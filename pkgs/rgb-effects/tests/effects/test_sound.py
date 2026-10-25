import numpy as np
import pytest

from rgb_effects.effects.sound import SoundField, SoundSettings
from rgb_effects.sources.audio.analysis import Features

SETTINGS = SoundSettings(spectrum_gain=0.7, silence_seconds=5.0)


def _features(
    level: float, loud: bool = True, left: float = -10.0, right: float = -10.0
) -> Features:
    return Features(left, right, np.full(21, level, dtype=np.float32), loud)


def test_silent_field_is_inactive() -> None:
    assert not SoundField(21, SETTINGS).active(0.0)


def test_loud_features_activate_the_field() -> None:
    field = SoundField(21, SETTINGS)
    field.update(_features(0.5), 10.0)
    assert field.active(12.0) and not field.active(16.0)


def test_envelope_fades_after_silence() -> None:
    field = SoundField(21, SETTINGS)
    field.update(_features(0.5), 0.0)
    assert (field.envelope(4.0), field.envelope(6.0), field.envelope(8.0)) == (1.0, 0.5, 0.0)


def test_strong_bands_light_full_columns() -> None:
    field = SoundField(21, SETTINGS)
    for step in range(20):
        field.update(_features(1.0), step * 0.02)
    lit, weight = field.lift(6, 0.5)
    assert lit.shape == (6, 21) and float(lit.min()) > 0.99 and weight == pytest.approx(0.7)


def test_weak_bands_light_only_the_bottom_rows() -> None:
    field = SoundField(21, SETTINGS)
    for step in range(20):
        field.update(_features(0.3), step * 0.02)
    lit, _ = field.lift(6, 0.5)
    assert float(lit[-1].mean()) > 0.9 and float(lit[0].mean()) < 0.01


def test_right_heavy_sound_tilts_towards_the_right() -> None:
    field = SoundField(21, SETTINGS)
    for step in range(20):
        field.update(_features(0.5, left=-40.0, right=-5.0), step * 0.02)
    lit, _ = field.lift(6, 0.5)
    assert float(lit[:, -1].sum()) > float(lit[:, 0].sum())


def test_sound_speeds_up_the_background_while_active() -> None:
    field = SoundField(21, SETTINGS)
    field.update(_features(0.5), 0.0)
    assert field.speed(1.0) > 0 and field.speed(20.0) == 0.0


def _with_chroma(pitch_class: int) -> Features:
    chroma = np.zeros(12, dtype=np.float32)
    chroma[pitch_class] = 1.0
    return Features(-10.0, -10.0, np.zeros(21, dtype=np.float32), True, 0.0, chroma)


def test_hue_shift_is_zero_without_harmony() -> None:
    assert SoundField(21, SETTINGS).hue_shift(0.0) == 0.0


def test_clear_harmony_turns_the_hue_within_its_range() -> None:
    field = SoundField(21, SoundSettings(0.7, 5.0, hue_range=60.0))
    for step in range(2000):
        field.update(_with_chroma(2), step * 0.02)
    shift = field.hue_shift(40.0)
    assert 0 < abs(shift) <= 60.0


def test_hue_shift_moves_slowly() -> None:
    field = SoundField(21, SoundSettings(0.7, 5.0, hue_range=60.0))
    field.update(_with_chroma(2), 0.0)
    assert abs(field.hue_shift(0.0)) < 5.0

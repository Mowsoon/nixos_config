import numpy as np
import pytest

from rgb_effects.effects.physics import Physics, PhysicsSettings, laplacian

SHAPE = (6, 21)
WHITE = np.ones(3, dtype=np.float32)


def _physics() -> Physics:
    return Physics(SHAPE, PhysicsSettings())


def test_laplacian_of_flat_grid_is_zero() -> None:
    assert not laplacian(np.ones(SHAPE, dtype=np.float32)).any()


def test_press_heats_and_lights_the_key() -> None:
    physics = _physics()
    physics.press(2, 5, 0.0, falling=False)
    fields = physics.fields
    heat, ember = float(fields.heat[2, 5]), float(fields.ember[2, 5])
    assert (heat, ember) == pytest.approx((0.15, 1.0))


def test_press_outside_grid_is_ignored() -> None:
    physics = _physics()
    physics.press(9, 5, 0.0, falling=False)
    assert not physics.fields.ember.any()


def test_cold_ember_dies_in_cold_lifetime() -> None:
    physics = _physics()
    physics.press(2, 5, 0.0, falling=False)
    physics.fields.heat[:] = 0.0
    physics.step(0.85, 0.85)
    assert float(physics.fields.ember[2, 5]) == 0.0


def test_hot_ember_outlives_cold_lifetime() -> None:
    physics = _physics()
    physics.press(2, 5, 0.0, falling=False)
    physics.fields.heat[2, 5] = 1.0
    physics.step(0.85, 0.85)
    assert float(physics.fields.ember[2, 5]) > 0.5


def test_hot_zone_keeps_a_halo() -> None:
    physics = _physics()
    physics.fields.heat[:] = 1.0
    physics.step(5.0, 5.0)
    assert float(physics.fields.ember[2, 5]) >= 0.14


def test_heat_diffuses_to_neighbours() -> None:
    physics = _physics()
    physics.fields.heat[2, 5] = 1.0
    physics.step(1.0, 1.0)
    assert float(physics.fields.heat[2, 6]) > 0.0


def test_wave_spreads_from_the_press() -> None:
    physics = _physics()
    physics.press(2, 10, 0.0, falling=False)
    physics.step(0.3, 0.3)
    assert abs(float(physics.fields.wave[2, 12])) > 0.0


def test_wave_travels_further_in_hot_zones() -> None:
    cold, hot = _physics(), _physics()
    hot.fields.heat[:] = 1.0
    for physics in (cold, hot):
        physics.press(2, 10, 0.0, falling=False)
        physics.step(1.0, 1.0)
    assert np.abs(hot.fields.wave).sum() > np.abs(cold.fields.wave).sum()


def test_falling_grain_lands_on_the_bottom_row() -> None:
    physics = _physics()
    physics.press(1, 7, 0.0, falling=True)
    physics.step(1.0, 1.0)
    assert float(physics.fields.sand[7]) > 0.0 and not physics.fields.particles


def test_enter_clears_sand_and_starts_sweep() -> None:
    physics = _physics()
    physics.fields.sand[3] = 1.0
    physics.enter()
    physics.step(0.05, 0.05)
    assert float(physics.fields.sand[3]) == 0.0 and float(physics.fields.wave[5, 0]) != 0.0


def test_emission_is_dark_when_nothing_happens() -> None:
    assert not _physics().emission(WHITE, WHITE, WHITE, WHITE).any()


def test_emission_lights_the_pressed_key() -> None:
    physics = _physics()
    physics.press(2, 5, 0.0, falling=False)
    assert physics.emission(WHITE, WHITE, WHITE, WHITE)[2, 5].tolist() == [1.0, 1.0, 1.0]


def test_pulse_raises_every_ember() -> None:
    physics = _physics()
    physics.pulse(0.6)
    assert float(physics.fields.ember.min()) == pytest.approx(0.6)


def test_impulse_adds_to_the_wave() -> None:
    physics = _physics()
    physics.impulse(2, 10, 0.8)
    assert float(physics.fields.wave[2, 10]) == pytest.approx(0.8)


def test_impulse_outside_grid_is_ignored() -> None:
    physics = _physics()
    physics.impulse(2, 40, 0.8)
    assert not physics.fields.wave.any()


def test_repeated_impulses_settle_back_to_rest() -> None:
    physics = _physics()
    for step in range(40):
        physics.impulse(2, 10, 1.2)
        physics.step(0.55, step * 0.55)
    physics.step(5.0, 30.0)
    assert float(np.abs(physics.fields.wave).max()) < 0.05


def test_wave_lights_only_its_crest() -> None:
    physics = _physics()
    physics.impulse(2, 10, 1.0)
    physics.step(0.3, 0.3)
    light = physics.emission(WHITE, WHITE, WHITE, WHITE)
    assert set(np.unique(light).tolist()) <= {0.0, 1.0}


def test_plane_wave_starts_on_both_edges() -> None:
    physics = _physics()
    physics.plane(1.0)
    wave = physics.fields.wave
    assert float(wave[:, 0].min()) == 1.0 and float(wave[:, -1].min()) == 1.0
    assert not wave[:, 1:-1].any()

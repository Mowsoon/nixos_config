import numpy as np

from rgb_effects.render.noise import GradientNoise

XS = np.arange(21, dtype=np.float64) * 0.18
YS = np.arange(6, dtype=np.float64) * 0.18


def test_sample_has_one_value_per_cell() -> None:
    assert GradientNoise(1).sample(XS, YS, 0.3).shape == (6, 21)


def test_sample_stays_in_signed_unit_range() -> None:
    values = GradientNoise(1).sample(XS, YS, 0.3)
    assert float(values.min()) >= -1.0 and float(values.max()) <= 1.0


def test_sample_is_deterministic_for_a_seed() -> None:
    assert np.array_equal(
        GradientNoise(5).sample(XS, YS, 1.7), GradientNoise(5).sample(XS, YS, 1.7)
    )


def test_sample_varies_smoothly_with_depth() -> None:
    noise = GradientNoise(5)
    step = np.abs(noise.sample(XS, YS, 1.0) - noise.sample(XS, YS, 1.01)).max()
    assert float(step) < 0.05


def test_sample_is_not_flat() -> None:
    assert float(GradientNoise(5).sample(XS, YS, 0.5).std()) > 0.01

import pytest

from rgb_effects.engine.activity import Activity


def test_rate_rises_with_events() -> None:
    activity = Activity(2.0, 0.0)
    activity.record(0.0)
    activity.record(0.0)
    assert activity.rate(0.0) == pytest.approx(1.0)


def test_rate_decays_without_events() -> None:
    activity = Activity(2.0, 0.0)
    activity.record(0.0)
    assert activity.rate(20.0) < 0.01


def test_idle_counts_from_last_event() -> None:
    activity = Activity(2.0, 0.0)
    activity.record(5.0)
    assert activity.idle_for(12.0) == 7.0


def test_activity_rejects_non_positive_time_constant() -> None:
    with pytest.raises(ValueError):
        Activity(0.0, 0.0)

from pathlib import Path

import pytest

from rgb_effects.power import is_low, keyboard_capacity


def _supply(root: Path, name: str, model: str, capacity: str) -> None:
    folder = root / name
    folder.mkdir()
    (folder / "model_name").write_text(model + "\n", encoding="utf-8")
    (folder / "capacity").write_text(capacity + "\n", encoding="utf-8")


def test_keyboard_capacity_reads_matching_model(tmp_path: Path) -> None:
    _supply(tmp_path, "BAT0", "GA50358", "88")
    _supply(tmp_path, "hidpp_battery_1", "G915 X LS", "57")
    assert keyboard_capacity(tmp_path, "G915 X LS") == 57


def test_keyboard_capacity_is_none_without_matching_model(tmp_path: Path) -> None:
    _supply(tmp_path, "BAT0", "GA50358", "88")
    assert keyboard_capacity(tmp_path, "G915 X LS") is None


def test_keyboard_capacity_skips_unreadable_capacity(tmp_path: Path) -> None:
    _supply(tmp_path, "hidpp_battery_1", "G915 X LS", "unknown")
    assert keyboard_capacity(tmp_path, "G915 X LS") is None


@pytest.mark.parametrize(
    ("capacity", "expected"), [(None, False), (21, False), (20, True), (5, True)]
)
def test_is_low_compares_with_threshold(capacity: int | None, expected: bool) -> None:
    assert is_low(capacity, 20) is expected

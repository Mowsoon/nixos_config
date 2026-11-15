from pathlib import Path

import pytest

from pcr12 import state
from pcr12.errors import InputError
from pcr12.state import Enrollment


def test_save_then_load_returns_the_enrollments(tmp_path: Path) -> None:
    enrollments = [Enrollment("07", "12", "ab"), Enrollment("07", "13", "cd")]
    state.save(tmp_path / "pcr12" / "enrollment.json", enrollments)
    assert state.load(tmp_path / "pcr12" / "enrollment.json") == enrollments


def test_load_reads_the_single_slot_format(tmp_path: Path) -> None:
    path = tmp_path / "enrollment.json"
    path.write_text('{"pcr7": "07", "pcr12": "12", "policy_hash": "ab"}', encoding="utf-8")
    assert state.load(path) == [Enrollment("07", "12", "ab")]


def test_save_keeps_the_file_private(tmp_path: Path) -> None:
    path = tmp_path / "enrollment.json"
    state.save(path, [Enrollment("07", "12", "ab")])
    assert path.stat().st_mode & 0o777 == 0o600


def test_load_returns_nothing_before_the_first_enrollment(tmp_path: Path) -> None:
    assert state.load(tmp_path / "enrollment.json") == []


@pytest.mark.parametrize(
    "content", ["not json", "[]", '{"pcr7": "07"}', '{"slots": 1}', '{"slots": [{"pcr7": "07"}]}']
)
def test_load_refuses_a_damaged_file(tmp_path: Path, content: str) -> None:
    path = tmp_path / "enrollment.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(InputError):
        state.load(path)

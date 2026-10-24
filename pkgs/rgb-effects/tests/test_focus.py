import pytest

from rgb_effects.focus import FocusError, parse_duration, request


@pytest.mark.parametrize(
    ("text", "seconds"), [("25m", 1500), ("90s", 90), ("1h", 3600), ("25", 1500), (" 5M ", 300)]
)
def test_parse_duration_reads_units(text: str, seconds: int) -> None:
    assert parse_duration(text) == seconds


@pytest.mark.parametrize("text", ["", "m", "25 min", "-5m", "0s", "25h"])
def test_parse_duration_rejects_invalid_text(text: str) -> None:
    with pytest.raises(FocusError):
        parse_duration(text)


def test_request_starts_focus_with_seconds() -> None:
    message = request("25m")
    assert (message.member, message.body) == ("StartFocus", [1500])


def test_request_stop_has_no_argument() -> None:
    message = request("stop")
    assert (message.member, message.body) == ("StopFocus", [])

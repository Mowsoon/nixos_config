import pytest
from evdev import ecodes

from rgb_effects.keyreader import PULSE_PACKET, ActivationError, Mode, encode, inherited_listener


def test_encode_sends_code_of_key_press() -> None:
    assert encode(ecodes.EV_KEY, ecodes.KEY_Q, 1, Mode.POSITION) == b"\x00\x10\x01"


@pytest.mark.parametrize("value", [0, 2])
def test_encode_drops_release_and_repeat_of_ordinary_keys(value: int) -> None:
    assert encode(ecodes.EV_KEY, ecodes.KEY_Q, value, Mode.POSITION) is None


def test_encode_sends_release_of_modifiers() -> None:
    assert encode(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 0, Mode.POSITION) == b"\x00\x1d\x00"


def test_encode_drops_modifier_release_in_pulse_mode() -> None:
    assert encode(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 0, Mode.PULSE) is None


def test_encode_drops_non_key_events() -> None:
    assert encode(ecodes.EV_MSC, ecodes.MSC_SCAN, 1, Mode.POSITION) is None


def test_encode_hides_key_identity_in_pulse_mode() -> None:
    assert encode(ecodes.EV_KEY, ecodes.KEY_Q, 1, Mode.PULSE) == PULSE_PACKET


def test_encode_drops_code_that_collides_with_pulse() -> None:
    assert encode(ecodes.EV_KEY, 0xFFFF, 1, Mode.POSITION) is None


@pytest.mark.parametrize(
    "environ",
    [{}, {"LISTEN_PID": "1", "LISTEN_FDS": "1"}, {"LISTEN_PID": "42", "LISTEN_FDS": "2"}],
)
def test_inherited_listener_requires_one_socket_for_this_process(environ: dict[str, str]) -> None:
    with pytest.raises(ActivationError):
        inherited_listener(environ, 42)

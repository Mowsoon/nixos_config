import pytest

from rgb_effects.sources.keys.listener import KeyEvent, decode


def test_decode_reads_press_of_a_code() -> None:
    assert decode(b"\x00\x10\x01") == KeyEvent(16, True)


def test_decode_reads_release() -> None:
    assert decode(b"\x00\x1d\x00") == KeyEvent(29, False)


def test_decode_reads_pulse_without_code() -> None:
    assert decode(b"\xff\xff\x01") == KeyEvent(None, True)


@pytest.mark.parametrize("packet", [b"", b"\x00\x10", b"\x00\x10\x01\x00", b"\x00\x10\x07"])
def test_decode_rejects_malformed_packet(packet: bytes) -> None:
    with pytest.raises(ValueError):
        decode(packet)

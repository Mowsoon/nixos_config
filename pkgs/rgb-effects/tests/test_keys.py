import pytest

from rgb_effects.keys import decode


def test_decode_reads_big_endian_code() -> None:
    assert decode(b"\x00\x10") == 16


def test_decode_reads_pulse_as_none() -> None:
    assert decode(b"\xff\xff") is None


@pytest.mark.parametrize("packet", [b"", b"\x00", b"\x00\x10\x00"])
def test_decode_rejects_wrong_length(packet: bytes) -> None:
    with pytest.raises(ValueError):
        decode(packet)

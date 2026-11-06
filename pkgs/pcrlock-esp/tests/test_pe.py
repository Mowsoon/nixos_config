import struct

import pytest

from pcrlock_esp import pe
from pcrlock_esp.errors import InputError
from tests import builders


def test_sections_reads_every_section_by_name() -> None:
    image = builders.pe_image({".osrel": b"ID=lanza\n", ".cmdline": b"quiet"})
    assert pe.sections(image) == {".osrel": b"ID=lanza\n", ".cmdline": b"quiet"}


def test_sections_trims_the_file_alignment_padding_to_the_virtual_size() -> None:
    image = builders.pe_image({".osrel": b"ID=lanza\n"}, padding=7)
    assert pe.sections(image)[".osrel"] == b"ID=lanza\n"


def test_sections_raises_when_the_mz_header_is_missing() -> None:
    image = b"XX" + builders.pe_image({".osrel": b"x"})[2:]
    with pytest.raises(InputError):
        pe.sections(image)


def test_sections_raises_when_the_pe_signature_is_missing() -> None:
    image = bytearray(builders.pe_image({".osrel": b"x"}))
    image[builders.PE_OFFSET : builders.PE_OFFSET + 4] = b"NOPE"
    with pytest.raises(InputError):
        pe.sections(bytes(image))


def test_sections_raises_when_the_header_is_truncated() -> None:
    with pytest.raises(InputError):
        pe.sections(b"MZ")


def test_sections_raises_when_a_section_extends_past_the_image() -> None:
    image = bytearray(builders.pe_image({".osrel": b"ID=lanza\n"}))
    section = builders.PE_OFFSET + 24
    struct.pack_into("<I", image, section + 20, len(image))
    with pytest.raises(InputError):
        pe.sections(bytes(image))

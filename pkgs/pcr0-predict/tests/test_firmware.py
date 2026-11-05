import pytest

from pcr0_predict import firmware
from pcr0_predict.errors import FirmwareError
from tests import builders


def test_strip_capsule_returns_the_image(current_image: bytes) -> None:
    assert firmware.strip_capsule(builders.capsule(current_image)) == current_image


@pytest.mark.parametrize("cut", [1, 100])
def test_strip_capsule_raises_when_sizes_disagree(current_image: bytes, cut: int) -> None:
    with pytest.raises(FirmwareError, match="not an EFI capsule"):
        firmware.strip_capsule(builders.capsule(current_image)[:-cut])


def test_strip_capsule_raises_on_short_file() -> None:
    with pytest.raises(FirmwareError, match="too short"):
        firmware.strip_capsule(b"\x00" * 10)


def test_volumes_finds_named_volumes(current_image: bytes) -> None:
    found = firmware.volumes(current_image)
    assert [(volume.offset, volume.name) for volume in found] == [
        (builders.MAIN_OFFSET, builders.MAIN_NAME),
        (builders.MAIN_OFFSET + len(found[0].data), builders.BOOT_NAME),
    ]


def test_volume_at_rejects_a_bad_checksum(current_image: bytes) -> None:
    damaged = bytearray(current_image)
    damaged[builders.MAIN_OFFSET + 0x32] ^= 0xFF
    assert firmware.volume_at(bytes(damaged), builders.MAIN_OFFSET) is None


def test_modules_descend_into_compressed_volumes(current_image: bytes) -> None:
    boot = firmware.volumes(current_image)[1]
    assert [module.guid for module in firmware.modules(boot.data)] == [builders.TPM_MODULE]


def test_modules_raise_when_zlib_payload_is_corrupt() -> None:
    packed = builders.zlib_section(b"irrelevant")[:-4] + b"\x00\x00\x00\x00"
    body = builders.section_stream(packed)
    broken = builders.volume(builders.BOOT_NAME, builders.ffs_file(builders.BOOT_FILE, 0x0B, body))
    with pytest.raises(FirmwareError, match="does not inflate"):
        list(firmware.modules(broken))


def test_modules_skip_freeform_files_holding_raw_data() -> None:
    raw = builders.ffs_file(builders.DRIVER, 0x02, b"RIFF" + b"\xff" * 12)
    assert list(firmware.modules(builders.volume(builders.MAIN_NAME, raw))) == []

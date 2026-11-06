import hashlib

import pytest

from pcrlock_esp.errors import InputError
from pcrlock_esp.records import Record, boot_loader_config_variants, generation_records
from tests import builders


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _replay(records: list[Record]) -> bytes:
    pcr = bytes(32)
    for record in records:
        pcr = _sha256(pcr + record.digest)
    return pcr


def _expected_pcr11() -> bytes:
    pcr = bytes(32)
    contents = (builders.KERNEL, builders.OSREL, builders.CMDLINE, builders.INITRD)
    for name, content in zip((".linux", ".osrel", ".cmdline", ".initrd"), contents, strict=True):
        pcr = _sha256(pcr + _sha256(name.encode() + b"\0"))
        pcr = _sha256(pcr + _sha256(content))
    return pcr


def test_generation_records_replay_to_the_pcr_11_of_a_unified_kernel_image() -> None:
    assert _replay(generation_records(builders.stub_sections())) == _expected_pcr11()


def test_generation_records_all_measure_pcr_11() -> None:
    assert {record.pcr for record in generation_records(builders.stub_sections())} == {11}


def test_generation_records_raise_when_a_measured_section_is_missing() -> None:
    sections = builders.stub_sections()
    del sections[".cmdline"]
    with pytest.raises(InputError):
        generation_records(sections)


def test_generation_records_raise_when_a_hash_section_is_not_a_sha256_digest() -> None:
    sections = builders.stub_sections()
    sections[".linuxh"] = b"short"
    with pytest.raises(InputError):
        generation_records(sections)


def test_boot_loader_config_variants_measure_the_gpt_before_each_image_or_once() -> None:
    gpt = bytes(range(32))
    loader = Record(5, _sha256(b"default nixos-*\n"))
    assert boot_loader_config_variants(gpt, b"default nixos-*\n") == {
        "300-gpt-before-each-image": [Record(5, gpt), loader, Record(5, gpt)],
        "600-gpt-once": [Record(5, gpt), loader],
    }


def test_boot_loader_config_variants_raise_when_the_gpt_digest_is_not_sha256() -> None:
    with pytest.raises(InputError):
        boot_loader_config_variants(b"short", b"")

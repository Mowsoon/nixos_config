import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

from pcrlock_esp.errors import InputError

BOOT_LOADER_CONFIG_PCR = 5
KERNEL_BOOT_PCR = 11
DIGEST_SIZE = 32
MEASURED_SECTIONS = (".linux", ".osrel", ".cmdline", ".initrd")
HASH_SECTIONS = {".linux": ".linuxh", ".initrd": ".initrdh"}


@dataclass(frozen=True, slots=True)
class Record:
    pcr: int
    digest: bytes


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def generation_records(sections: Mapping[str, bytes]) -> list[Record]:
    records: list[Record] = []
    for name in MEASURED_SECTIONS:
        records.append(Record(KERNEL_BOOT_PCR, sha256(name.encode("ascii") + b"\0")))
        records.append(Record(KERNEL_BOOT_PCR, _content_digest(sections, name)))
    return records


def boot_loader_config_variants(gpt: bytes, loader_conf: bytes) -> dict[str, list[Record]]:
    _require_digest(gpt, "GPT")
    head = [
        Record(BOOT_LOADER_CONFIG_PCR, gpt),
        Record(BOOT_LOADER_CONFIG_PCR, sha256(loader_conf)),
    ]
    return {
        "300-gpt-before-each-image": [*head, Record(BOOT_LOADER_CONFIG_PCR, gpt)],
        "600-gpt-once": head,
    }


def _content_digest(sections: Mapping[str, bytes], name: str) -> bytes:
    hash_section = HASH_SECTIONS.get(name)
    if hash_section is None:
        return sha256(_section(sections, name))
    digest = _section(sections, hash_section)
    _require_digest(digest, hash_section)
    return digest


def _section(sections: Mapping[str, bytes], name: str) -> bytes:
    content = sections.get(name)
    if content is None:
        raise InputError(f"the stub has no {name} section")
    return content


def _require_digest(digest: bytes, name: str) -> None:
    if len(digest) != DIGEST_SIZE:
        raise InputError(f"{name} is not a SHA-256 digest")

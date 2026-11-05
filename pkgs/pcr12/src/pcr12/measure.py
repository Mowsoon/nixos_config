import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

PREFIX = ".extra/global_credentials"
ANCESTOR_MODE = 0o555
DIRECTORY_MODE = 0o500
FILE_MODE = 0o400
S_IFDIR = 0o040000
S_IFREG = 0o100000
TRAILER = "TRAILER!!!"
MAGIC = b"070701"
EMPTY_PCR = bytes(32)


@dataclass(frozen=True, slots=True)
class Credential:
    name: str
    data: bytes


def _pad(data: bytes) -> bytes:
    return data + b"\x00" * (-len(data) % 4)


def _entry(name: str, inode: int, mode: int, data: bytes = b"") -> bytes:
    encoded = name.encode("utf-8")
    fields = (inode, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(encoded) + 1, 0)
    header = MAGIC + b"".join(b"%08x" % field for field in fields) + encoded + b"\x00"
    return _pad(header) + _pad(data)


def _directories() -> list[tuple[str, int]]:
    parts = PREFIX.split("/")
    paths = ["/" + "/".join(parts[: index + 1]) for index in range(len(parts))]
    return [(path, ANCESTOR_MODE) for path in paths[:-1]] + [(paths[-1], DIRECTORY_MODE)]


def archive(credentials: Sequence[Credential]) -> bytes:
    entries = [(path, mode | S_IFDIR, b"") for path, mode in _directories()]
    entries += [
        (f"{PREFIX}/{credential.name}", FILE_MODE | S_IFREG, credential.data)
        for credential in sorted(credentials, key=lambda credential: credential.name)
    ]
    entries.append((TRAILER, S_IFREG, b""))
    return b"".join(
        _entry(name, inode, mode, data) for inode, (name, mode, data) in enumerate(entries, 1)
    )


def records(credentials: Sequence[Credential]) -> list[bytes]:
    if not credentials:
        return []
    return [hashlib.sha256(archive(credentials)).digest()]


def replay(digests: Sequence[bytes]) -> bytes:
    value = EMPTY_PCR
    for digest in digests:
        value = hashlib.sha256(value + digest).digest()
    return value

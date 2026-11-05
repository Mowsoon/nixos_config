import hashlib
import struct
import zlib
from dataclasses import dataclass
from uuid import UUID

FFS2 = UUID("8c8ce578-8a3d-4f1c-9935-896185c32dd3")
AMI_ZLIB = UUID("ce3233f5-2cd6-4d87-9152-4a238bb6d1c4")
MAIN_NAME = UUID("4f1c52d3-d824-4d2a-a2f0-ec40c23c5916")
BOOT_NAME = UUID("61c0f511-a691-4f54-974f-b9a42172ce53")
TPM_MODULE = UUID("0d8039ff-49e9-4cc9-a806-bb7c31b0bcb0")
DRIVER = UUID("11111111-2222-3333-4444-555555555555")
BOOT_FILE = UUID("3e3b6dc0-064d-4b01-9203-7836c9b498e7")
CRTM = bytes.fromhex("052b10a7c7d9654181402adde94af63c")
MAIN_OFFSET = 0x1000
SHA256 = 0x000B
VOLUME_HEADER = 0x48


def _pad(data: bytes, alignment: int, fill: bytes = b"\x00") -> bytes:
    return data + fill * (-len(data) % alignment)


def section(section_type: int, body: bytes) -> bytes:
    return (4 + len(body)).to_bytes(3, "little") + bytes([section_type]) + body


def section_stream(*parts: bytes) -> bytes:
    return b"".join(_pad(part, 4) for part in parts)


def zlib_section(inner: bytes) -> bytes:
    header = AMI_ZLIB.bytes_le + struct.pack("<HH", 24, 1)
    return section(0x02, header + b"\x00" * 0x100 + zlib.compress(inner))


def ffs_file(guid: UUID, file_type: int, body: bytes) -> bytes:
    size = (24 + len(body)).to_bytes(3, "little")
    return guid.bytes_le + b"\x00\x00" + bytes([file_type, 0]) + size + b"\xf8" + body


def volume(name: UUID, *files: bytes) -> bytes:
    extension = name.bytes_le + struct.pack("<I", 20)
    body = _pad(extension, 8, b"\xff") + b"".join(_pad(file, 8, b"\xff") for file in files)
    body += b"\xff" * (-(VOLUME_HEADER + len(body)) % 16)
    length = VOLUME_HEADER + len(body)
    header = bytearray(b"\x00" * 16 + FFS2.bytes_le)
    header += struct.pack("<Q4sIHHHBB", length, b"_FVH", 0x0004FEFF, VOLUME_HEADER, 0, 0x48, 0, 2)
    header += struct.pack("<IIII", length // 0x1000 or 1, 0x1000, 0, 0)
    words = struct.unpack(f"<{len(header) // 2}H", bytes(header))
    struct.pack_into("<H", header, 0x32, -sum(words) & 0xFFFF)
    return bytes(header) + body


def stores(constant: bytes) -> bytes:
    words = [constant[index : index + 4] for index in range(0, len(constant), 4)]
    stores_ = [
        b"\xc7\x44\x24" + bytes([0x0C + 4 * index]) + word for index, word in enumerate(words)
    ]
    return b"\x56\x57" + b"\x8d\x54\x24\x08".join(stores_) + b"\xc3"


def boot_volume(code: bytes) -> bytes:
    peim = ffs_file(TPM_MODULE, 0x06, section_stream(section(0x12, code)))
    nested = volume(UUID("44a2d731-d551-4594-93b4-bd2b60351e0e"), peim)
    packed = zlib_section(section_stream(section(0x19, b"\x00" * 24), section(0x17, nested)))
    return volume(BOOT_NAME, ffs_file(BOOT_FILE, 0x0B, section_stream(packed)))


def main_volume(payload: bytes) -> bytes:
    return volume(MAIN_NAME, ffs_file(DRIVER, 0x07, section_stream(section(0x10, payload))))


def image(payload: bytes, code: bytes) -> bytes:
    return b"\xff" * MAIN_OFFSET + main_volume(payload) + boot_volume(code)


def capsule(firmware: bytes) -> bytes:
    header_size = 64
    header = UUID("4a3ca68b-7723-48fb-803d-578cc1fec44d").bytes_le
    header += struct.pack("<III", header_size, 0x10000, header_size + len(firmware))
    return _pad(header, header_size) + firmware


@dataclass(frozen=True, slots=True)
class LogEvent:
    pcr: int
    event_type: int
    data: bytes
    measured: bytes | None = None

    @property
    def digest(self) -> bytes:
        return hashlib.sha256(self.data if self.measured is None else self.measured).digest()


def event_log(events: list[LogEvent], algorithms: tuple[int, ...] = (SHA256,)) -> bytes:
    spec = b"Spec ID Event03\x00" + b"\x00" * 4 + bytes([0, 2, 0, 2])
    spec += struct.pack("<I", len(algorithms))
    spec += b"".join(struct.pack("<HH", algorithm, 32) for algorithm in algorithms)
    log = struct.pack("<II", 0, 0x3) + b"\x00" * 20 + struct.pack("<I", len(spec)) + spec
    for event in events:
        log += struct.pack("<IIIH", event.pcr, event.event_type, 1, algorithms[0]) + event.digest
        log += struct.pack("<I", len(event.data)) + event.data
    return log


def blob2(base: int, length: int) -> bytes:
    return bytes([7]) + b"FV_MAIN" + struct.pack("<QQ", base, length)


def firmware_events(firmware: bytes, payload: bytes) -> list[LogEvent]:
    main = main_volume(payload)
    assert firmware[MAIN_OFFSET : MAIN_OFFSET + len(main)] == main
    return [
        LogEvent(0, 0x8, CRTM),
        LogEvent(0, 0x8000000A, blob2(MAIN_OFFSET, len(main)), main),
        LogEvent(7, 0x80000001, b"SecureBoot"),
        LogEvent(0, 0x4, b"\x00" * 4),
    ]

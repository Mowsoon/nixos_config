import lzma
import struct
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

from pcr0_predict.errors import FirmwareError

CAPSULE_HEADER = 28
VOLUME_SIGNATURE = b"_FVH"
VOLUME_SIGNATURE_OFFSET = 0x28
VOLUME_MIN_HEADER = 0x38
FILE_SYSTEMS = frozenset(
    {UUID("8c8ce578-8a3d-4f1c-9935-896185c32dd3"), UUID("5473c07a-3dcb-4dca-bd6f-1e9689e7349a")}
)
AMI_ZLIB = UUID("ce3233f5-2cd6-4d87-9152-4a238bb6d1c4")
AMI_ZLIB_HEADER = 0x100
LZMA_CUSTOM = UUID("ee4e5898-3914-4259-9d6e-dc7bd79403cf")
DECOMPRESSED_LIMIT = 64 * 1024 * 1024
FILE_HEADER = 24
LARGE_FILE_HEADER = 32
SECTION_HEADER = 4
LARGE_SECTION_HEADER = 8
PROCESSING_REQUIRED = 0x01
LARGE_FILE = 0x01
GUID_DEFINED = 0x02
PE32 = 0x10
TE = 0x12
FV_IMAGE = 0x17
SECTIONED_FILE_TYPES = range(0x03, 0x10)


@dataclass(frozen=True, slots=True)
class Volume:
    offset: int
    data: bytes
    name: UUID | None


@dataclass(frozen=True, slots=True)
class Module:
    guid: UUID
    code: tuple[bytes, ...]


@dataclass(frozen=True, slots=True)
class Section:
    section_type: int
    raw: bytes
    header: int

    @property
    def body(self) -> bytes:
        return self.raw[self.header :]


def _align(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def strip_capsule(data: bytes) -> bytes:
    if len(data) < CAPSULE_HEADER:
        raise FirmwareError("file is too short for an EFI capsule")
    header_size, _flags, image_size = struct.unpack_from("<III", data, 16)
    if image_size != len(data) or not CAPSULE_HEADER <= header_size < len(data):
        raise FirmwareError("file is not an EFI capsule: header sizes do not match the file")
    return data[header_size:]


def _checksum_valid(header: bytes) -> bool:
    words: tuple[int, ...] = struct.unpack(f"<{len(header) // 2}H", header)
    return sum(words) & 0xFFFF == 0


def volume_at(data: bytes, offset: int) -> Volume | None:
    if offset < 0 or offset + VOLUME_MIN_HEADER > len(data):
        return None
    if data[offset + VOLUME_SIGNATURE_OFFSET : offset + 0x2C] != VOLUME_SIGNATURE:
        return None
    if UUID(bytes_le=data[offset + 16 : offset + 32]) not in FILE_SYSTEMS:
        return None
    (length,) = struct.unpack_from("<Q", data, offset + 0x20)
    (header_length,) = struct.unpack_from("<H", data, offset + 0x30)
    if header_length < VOLUME_MIN_HEADER or header_length % 2 or offset + length > len(data):
        return None
    if length < header_length or not _checksum_valid(data[offset : offset + header_length]):
        return None
    volume = data[offset : offset + length]
    return Volume(offset, volume, _volume_name(volume))


def _volume_name(volume: bytes) -> UUID | None:
    (extension,) = struct.unpack_from("<H", volume, 0x34)
    if extension == 0 or extension + 20 > len(volume):
        return None
    return UUID(bytes_le=volume[extension : extension + 16])


def volumes(image: bytes) -> list[Volume]:
    found: list[Volume] = []
    position = image.find(VOLUME_SIGNATURE)
    while position >= 0:
        volume = volume_at(image, position - VOLUME_SIGNATURE_OFFSET)
        if volume is None:
            position = image.find(VOLUME_SIGNATURE, position + 1)
            continue
        found.append(volume)
        position = image.find(VOLUME_SIGNATURE, volume.offset + len(volume.data))
    return found


def _files_start(volume: bytes) -> int:
    (extension,) = struct.unpack_from("<H", volume, 0x34)
    if extension == 0:
        return int.from_bytes(volume[0x30:0x32], "little")
    (size,) = struct.unpack_from("<I", volume, extension + 16)
    return _align(extension + size, 8)


def _files(volume: bytes) -> Iterator[tuple[UUID, bytes]]:
    offset = _files_start(volume)
    while offset + FILE_HEADER <= len(volume):
        header = volume[offset : offset + FILE_HEADER]
        if header == b"\xff" * FILE_HEADER:
            return
        size = int.from_bytes(header[0x14:0x17], "little")
        header_size = FILE_HEADER
        if size == 0 and header[0x13] & LARGE_FILE:
            (size,) = struct.unpack_from("<Q", volume, offset + FILE_HEADER)
            header_size = LARGE_FILE_HEADER
        if size < header_size or offset + size > len(volume):
            raise FirmwareError(f"file at {offset:#x} overruns its volume")
        if header[0x12] in SECTIONED_FILE_TYPES:
            yield UUID(bytes_le=header[:16]), volume[offset + header_size : offset + size]
        offset = _align(offset + size, 8)


def _sections(data: bytes) -> Iterator[Section]:
    offset = 0
    while offset + SECTION_HEADER <= len(data):
        size = int.from_bytes(data[offset : offset + 3], "little")
        header = SECTION_HEADER
        if size == 0xFFFFFF:
            (size,) = struct.unpack_from("<I", data, offset + SECTION_HEADER)
            header = LARGE_SECTION_HEADER
        if size < header or offset + size > len(data):
            raise FirmwareError(f"section at {offset:#x} overruns its container")
        yield Section(data[offset + 3], data[offset : offset + size], header)
        offset = _align(offset + size, 4)


def _inflate(payload: bytes) -> bytes:
    inflater = zlib.decompressobj()
    try:
        data = inflater.decompress(payload, DECOMPRESSED_LIMIT)
    except zlib.error as err:
        raise FirmwareError("AMI zlib section does not inflate") from err
    if inflater.unconsumed_tail:
        raise FirmwareError("AMI zlib section inflates beyond the size limit")
    return data


def _unlzma(payload: bytes) -> bytes:
    decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    try:
        data = decompressor.decompress(payload, DECOMPRESSED_LIMIT)
    except lzma.LZMAError as err:
        raise FirmwareError("LZMA section does not decompress") from err
    if not decompressor.eof:
        raise FirmwareError("LZMA section decompresses beyond the size limit")
    return data


def _guided(section: Section) -> bytes | None:
    start = section.header
    guid = UUID(bytes_le=section.raw[start : start + 16])
    data_offset, attributes = struct.unpack_from("<HH", section.raw, start + 16)
    payload = section.raw[data_offset:]
    if guid == AMI_ZLIB:
        return _inflate(payload[AMI_ZLIB_HEADER:])
    if guid == LZMA_CUSTOM:
        return _unlzma(payload)
    if attributes & PROCESSING_REQUIRED:
        return None
    return payload


def _leaves(data: bytes) -> Iterator[Section]:
    for section in _sections(data):
        if section.section_type != GUID_DEFINED:
            yield section
            continue
        decoded = _guided(section)
        if decoded is not None:
            yield from _leaves(decoded)


def modules(volume: bytes) -> Iterator[Module]:
    for guid, body in _files(volume):
        leaves = list(_leaves(body))
        code = tuple(leaf.body for leaf in leaves if leaf.section_type in (PE32, TE))
        if code:
            yield Module(guid, code)
        for leaf in leaves:
            if leaf.section_type != FV_IMAGE:
                continue
            nested = volume_at(leaf.body, 0)
            if nested is None:
                raise FirmwareError(f"volume image section of file {guid} holds no volume")
            yield from modules(nested.data)

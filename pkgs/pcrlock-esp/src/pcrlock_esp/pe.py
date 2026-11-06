import struct

from pcrlock_esp.errors import InputError

DOS_MAGIC = b"MZ"
PE_SIGNATURE = b"PE\0\0"
PE_OFFSET_POINTER = 0x3C
COFF_HEADER_SIZE = 20
SECTION_HEADER_SIZE = 40
SECTION_NAME_SIZE = 8


def sections(image: bytes) -> dict[str, bytes]:
    if image[: len(DOS_MAGIC)] != DOS_MAGIC:
        raise InputError("not a PE image: no MZ header")
    signature = _unpack("<I", image, PE_OFFSET_POINTER)
    if image[signature : signature + len(PE_SIGNATURE)] != PE_SIGNATURE:
        raise InputError("not a PE image: no PE signature")
    coff = signature + len(PE_SIGNATURE)
    count = _unpack("<H", image, coff + 2)
    optional_size = _unpack("<H", image, coff + 16)
    table = coff + COFF_HEADER_SIZE + optional_size
    found: dict[str, bytes] = {}
    for index in range(count):
        name, content = _section(image, table + index * SECTION_HEADER_SIZE)
        found[name] = content
    return found


def _section(image: bytes, offset: int) -> tuple[str, bytes]:
    header = image[offset : offset + SECTION_HEADER_SIZE]
    if len(header) < SECTION_HEADER_SIZE:
        raise InputError("truncated PE section table")
    try:
        name = header[:SECTION_NAME_SIZE].rstrip(b"\0").decode("ascii")
    except UnicodeDecodeError as err:
        raise InputError("PE section name is not ASCII") from err
    virtual_size, _, raw_size, raw_offset = struct.unpack_from("<IIII", header, SECTION_NAME_SIZE)
    size = min(virtual_size, raw_size)
    if raw_offset + size > len(image):
        raise InputError(f"PE section {name} extends past the image")
    return name, image[raw_offset : raw_offset + size]


def _unpack(layout: str, image: bytes, offset: int) -> int:
    try:
        (value,) = struct.unpack_from(layout, image, offset)
    except struct.error as err:
        raise InputError("truncated PE header") from err
    return int(value)

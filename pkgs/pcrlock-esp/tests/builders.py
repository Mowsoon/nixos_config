import hashlib
import json
import struct
from collections.abc import Mapping

PE_OFFSET = 0x80
FILE_ALIGNMENT = 0x200
KERNEL = b"kernel image"
INITRD = b"initrd archive"
OSREL = b"ID=lanza\nVERSION_ID=Generation 1, 2026-11-05\n"
CMDLINE = b"init=/nix/store/system/init quiet"


def pe_image(sections: Mapping[str, bytes], padding: int = 0) -> bytes:
    table = PE_OFFSET + 4 + 20
    data_offset = FILE_ALIGNMENT
    headers = bytearray()
    payload = bytearray()
    for name, content in sections.items():
        raw_size = len(content) + padding
        headers += name.encode("ascii").ljust(8, b"\0")
        headers += struct.pack("<IIII", len(content), 0, raw_size, data_offset + len(payload))
        headers += bytes(16)
        payload += content + bytes(padding)
    image = bytearray(data_offset)
    image[0:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, PE_OFFSET)
    image[PE_OFFSET : PE_OFFSET + 4] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", image, PE_OFFSET + 4, 0x8664, len(sections), 0, 0, 0, 0, 0)
    image[table : table + len(headers)] = headers
    return bytes(image + payload)


def stub_sections() -> dict[str, bytes]:
    return {
        ".osrel": OSREL,
        ".cmdline": CMDLINE,
        ".initrd": b"/EFI/nixos/initrd.efi",
        ".linux": b"/EFI/nixos/kernel.efi",
        ".initrdh": hashlib.sha256(INITRD).digest(),
        ".linuxh": hashlib.sha256(KERNEL).digest(),
    }


def gpt_component(digest: str, pcr: int = 5) -> str:
    digests = [
        {"hashAlg": "sha1", "digest": "00" * 20},
        {"hashAlg": "sha256", "digest": digest},
    ]
    return json.dumps({"records": [{"pcr": pcr, "digests": digests}]})

import struct
from collections import Counter
from collections.abc import Callable, Iterator

from theme_recolor.convert import Pixel
from theme_recolor.errors import FormatError

MAGIC = b"Xcur"
IMAGE_TYPE = 0xFFFD0002
IMAGE_HEADER = 36
OPAQUE_ENOUGH = 128


def is_xcursor(data: bytes) -> bool:
    return data.startswith(MAGIC)


def _images(data: bytes) -> Iterator[tuple[int, int]]:
    try:
        _magic, header, _version, entries = struct.unpack_from("<4sIII", data, 0)
        for index in range(entries):
            kind, _subtype, position = struct.unpack_from("<III", data, header + index * 12)
            if kind != IMAGE_TYPE:
                continue
            width, height = struct.unpack_from("<II", data, position + 16)
            yield position + IMAGE_HEADER, width * height
    except struct.error as err:
        raise FormatError("truncated Xcursor file") from err


def _unpremultiply(argb: int) -> tuple[int, Pixel]:
    alpha = argb >> 24
    channels = ((argb >> 16) & 255, (argb >> 8) & 255, argb & 255)
    r, g, b = (min(255, c * 255 // alpha) for c in channels)
    return alpha, (r, g, b)


def _premultiply(alpha: int, rgb: Pixel) -> int:
    r, g, b = (c * alpha // 255 for c in rgb)
    return (alpha << 24) | (r << 16) | (g << 8) | b


def recolor(data: bytes, convert: Callable[[Pixel], Pixel]) -> bytes:
    out = bytearray(data)
    for offset, count in _images(data):
        pixels = list(struct.unpack_from(f"<{count}I", data, offset))
        for index, argb in enumerate(pixels):
            if argb >> 24 == 0:
                continue
            alpha, rgb = _unpremultiply(argb)
            pixels[index] = _premultiply(alpha, convert(rgb))
        struct.pack_into(f"<{count}I", out, offset, *pixels)
    return bytes(out)


def colors(data: bytes) -> Counter[str]:
    found: Counter[str] = Counter()
    for offset, count in _images(data):
        for argb in struct.unpack_from(f"<{count}I", data, offset):
            if argb >> 24 < OPAQUE_ENOUGH:
                continue
            _alpha, (r, g, b) = _unpremultiply(argb)
            found[f"#{r & 0xF0:02x}{g & 0xF0:02x}{b & 0xF0:02x}"] += 1
    return found

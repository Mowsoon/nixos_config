import io
import struct

import pytest
from PIL import Image

from theme_recolor import raster, text, xcursor
from theme_recolor.convert import Pixel
from theme_recolor.errors import FormatError


def _invert(rgb: Pixel) -> Pixel:
    r, g, b = rgb
    return 255 - r, 255 - g, 255 - b


def _cursor(pixels: list[int]) -> bytes:
    header = struct.pack("<4sIII", b"Xcur", 16, 0x10000, 1)
    toc = struct.pack("<III", xcursor.IMAGE_TYPE, 1, 28)
    image = struct.pack("<9I", 36, xcursor.IMAGE_TYPE, 1, 1, len(pixels), 1, 0, 0, 0)
    return header + toc + image + struct.pack(f"<{len(pixels)}I", *pixels)


def test_xcursor_recolours_opaque_pixels_and_keeps_transparent_ones() -> None:
    data = _cursor([0xFF000000, 0x00000000])
    result = xcursor.recolor(data, _invert)
    assert struct.unpack_from("<2I", result, len(data) - 8) == (0xFFFFFFFF, 0x00000000)


def test_xcursor_keeps_alpha_and_premultiplies() -> None:
    data = _cursor([0x80000000])
    result = xcursor.recolor(data, _invert)
    assert struct.unpack_from("<I", result, len(data) - 4)[0] == 0x80808080


def test_xcursor_rejects_truncated_files() -> None:
    with pytest.raises(FormatError):
        list(xcursor.colors(_cursor([0xFF000000])[:40]))


def test_raster_keeps_alpha() -> None:
    buffer = io.BytesIO()
    Image.new("RGBA", (1, 1), (0, 0, 0, 77)).save(buffer, "PNG")
    result = Image.open(io.BytesIO(raster.recolor(buffer.getvalue(), _invert)))
    assert result.getpixel((0, 0)) == (255, 255, 255, 77)


def test_raster_rejects_unreadable_data() -> None:
    with pytest.raises(FormatError):
        raster.recolor(b"not an image", _invert)


def test_rc_colour_triples_are_rewritten() -> None:
    data = b"[General]\nActiveTextColor=252, 252, 252\nTitleHeight=21\n"
    result = text.recolor_rc(data, lambda value: "#010203")
    assert result == b"[General]\nActiveTextColor=1, 2, 3\nTitleHeight=21\n"


def test_rc_rejects_out_of_range_channels() -> None:
    with pytest.raises(FormatError):
        text.recolor_rc(b"ActiveTextColor=300, 0, 0\n", lambda value: value)


def test_qml_quoted_colours_are_rewritten() -> None:
    data = b'color: "#d3d3ff"\nsource: "images/start.svg"\n'
    assert text.recolor_qml(data, lambda value: "#010203") == (
        b'color: "#010203"\nsource: "images/start.svg"\n'
    )

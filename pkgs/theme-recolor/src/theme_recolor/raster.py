import io
from collections import Counter
from collections.abc import Callable

from PIL import Image, UnidentifiedImageError

from theme_recolor.convert import Pixel
from theme_recolor.errors import FormatError

JPEG_QUALITY = 95
SAMPLE_SIZE = (320, 180)


def _open(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as err:
        raise FormatError("unreadable raster image") from err
    return image


RgbaPixel = tuple[int, int, int, int]


def _rgba(image: Image.Image) -> Image.Image:
    return image if image.mode == "RGBA" else image.convert("RGBA")


def _pixels(image: Image.Image) -> list[RgbaPixel]:
    pixels: list[RgbaPixel] = []
    for value in image.get_flattened_data():
        if not isinstance(value, tuple) or len(value) != 4:
            raise FormatError("unexpected pixel layout")
        r, g, b, a = (int(channel) for channel in value)
        pixels.append((r, g, b, a))
    return pixels


def recolor(data: bytes, convert: Callable[[Pixel], Pixel]) -> bytes:
    source = _open(data)
    image_format = source.format or "PNG"
    image = _rgba(source)
    pixels = [convert((r, g, b)) + (a,) for r, g, b, a in _pixels(image)]
    result = Image.new("RGBA", image.size)
    result.putdata(pixels)
    buffer = io.BytesIO()
    if image_format == "JPEG":
        result.convert("RGB").save(buffer, "JPEG", quality=JPEG_QUALITY)
    else:
        result.save(buffer, image_format)
    return buffer.getvalue()


def colors(data: bytes) -> Counter[str]:
    image = _rgba(_open(data)).resize(SAMPLE_SIZE)
    found: Counter[str] = Counter()
    for r, g, b, a in _pixels(image):
        if a:
            found[f"#{r & 0xF0:02x}{g & 0xF0:02x}{b & 0xF0:02x}"] += 1
    return found

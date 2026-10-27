from collections.abc import Callable

from theme_recolor.oklab import Rgb, parse_hex, to_bytes

Pixel = tuple[int, int, int]


class Converter:
    def __init__(self, apply: Callable[[Rgb], Rgb]) -> None:
        self._apply = apply
        self._pixels: dict[Pixel, Pixel] = {}

    def pixel(self, rgb: Pixel) -> Pixel:
        cached = self._pixels.get(rgb)
        if cached is None:
            r, g, b = rgb
            cached = to_bytes(self._apply((r / 255, g / 255, b / 255)))
            self._pixels[rgb] = cached
        return cached

    def hex(self, text: str) -> str:
        r, g, b = self.pixel(to_bytes(parse_hex(text)))
        return f"#{r:02x}{g:02x}{b:02x}"

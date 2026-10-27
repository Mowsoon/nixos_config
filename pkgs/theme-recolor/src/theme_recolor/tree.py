from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from theme_recolor import raster, svg, text, xcursor
from theme_recolor.convert import Converter, Pixel

HexRewrite = Callable[[bytes, Callable[[str], str]], bytes]
PixelRewrite = Callable[[bytes, Callable[[Pixel], Pixel]], bytes]
Collect = Callable[[bytes], Counter[str]]


@dataclass(frozen=True, slots=True)
class HexFormat:
    rewrite: HexRewrite
    collect: Collect

    def recolor(self, data: bytes, converter: Converter) -> bytes:
        return self.rewrite(data, converter.hex)


@dataclass(frozen=True, slots=True)
class PixelFormat:
    rewrite: PixelRewrite
    collect: Collect

    def recolor(self, data: bytes, converter: Converter) -> bytes:
        return self.rewrite(data, converter.pixel)


Format = HexFormat | PixelFormat

SVG = HexFormat(svg.recolor, svg.colors)
QML = HexFormat(text.recolor_qml, text.qml_colors)
RC = HexFormat(text.recolor_rc, text.rc_colors)
RASTER = PixelFormat(raster.recolor, raster.colors)
XCURSOR = PixelFormat(xcursor.recolor, xcursor.colors)
SUFFIXES: dict[str, Format] = {
    ".svg": SVG,
    ".svgz": SVG,
    ".qml": QML,
    ".png": RASTER,
    ".jpg": RASTER,
    ".jpeg": RASTER,
}


def format_of(path: Path, head: bytes) -> Format | None:
    known = SUFFIXES.get(path.suffix.lower())
    if known is not None:
        return known
    if xcursor.is_xcursor(head):
        return XCURSOR
    if path.suffix == "" and path.name.endswith("rc"):
        return RC
    return None


def files(root: Path) -> Iterator[tuple[Path, Format]]:
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as handle:
            head = handle.read(4)
        found = format_of(path, head)
        if found is not None:
            yield path, found


def collect(root: Path) -> Counter[str]:
    total: Counter[str] = Counter()
    for path, found in files(root):
        total.update(found.collect(path.read_bytes()))
    return total


def recolor(root: Path, converter: Converter) -> int:
    changed = 0
    for path, found in files(root):
        data = path.read_bytes()
        result = found.recolor(data, converter)
        if result != data:
            path.write_bytes(result)
            changed += 1
    return changed

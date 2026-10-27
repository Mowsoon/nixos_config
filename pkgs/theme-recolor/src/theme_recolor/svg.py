import gzip
import re
from collections import Counter
from collections.abc import Callable

from theme_recolor.errors import FormatError

GZIP_MAGIC = b"\x1f\x8b"
STYLE_BLOCK = re.compile(r"(<style\b[^>]*>.*?</style>)", re.DOTALL | re.IGNORECASE)
TAG = re.compile(r"<[A-Za-z][^>]*>")
CLASS = re.compile(r"""\bclass\s*=\s*(["'])([^"']*)\1""")
IDENT = re.compile(r"""\bid\s*=\s*(["'])([^"']*)\1""")
COLOR_ATTRIBUTE = re.compile(
    r"""(?<![\w-])(fill|stroke|stop-color|flood-color|lighting-color|color|style)"""
    r"""(\s*=\s*)(["'])(.*?)\3""",
    re.DOTALL,
)
STYLE_PROPERTY = re.compile(
    r"(?<![\w-])((?:fill|stroke|stop-color|flood-color|lighting-color|color)\s*:\s*)"
    r"(#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b)"
)
HEX_VALUE = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")


def _skipped(tag: str) -> bool:
    classes = CLASS.search(tag)
    if classes and "ColorScheme-" in classes.group(2):
        return True
    ident = IDENT.search(tag)
    return bool(ident and "hint" in ident.group(2))


def _rewrite_value(name: str, value: str, convert: Callable[[str], str]) -> str:
    if name == "style":
        return STYLE_PROPERTY.sub(lambda m: m.group(1) + convert(m.group(2)), value)
    return HEX_VALUE.sub(lambda m: convert(m.group(0)), value)


def _rewrite_tag(tag: str, convert: Callable[[str], str]) -> str:
    if _skipped(tag):
        return tag

    def attribute(match: re.Match[str]) -> str:
        name, equals, quote, value = match.groups()
        return f"{name}{equals}{quote}{_rewrite_value(name, value, convert)}{quote}"

    return COLOR_ATTRIBUTE.sub(attribute, tag)


def rewrite_text(text: str, convert: Callable[[str], str]) -> str:
    parts = STYLE_BLOCK.split(text)
    for index in range(0, len(parts), 2):
        parts[index] = TAG.sub(lambda m: _rewrite_tag(m.group(0), convert), parts[index])
    return "".join(parts)


def _decode(data: bytes) -> tuple[str, bool]:
    compressed = data.startswith(GZIP_MAGIC)
    raw = gzip.decompress(data) if compressed else data
    try:
        return raw.decode("utf-8"), compressed
    except UnicodeDecodeError as err:
        raise FormatError("SVG is not UTF-8") from err


def recolor(data: bytes, convert: Callable[[str], str]) -> bytes:
    text, compressed = _decode(data)
    raw = rewrite_text(text, convert).encode("utf-8")
    return gzip.compress(raw, mtime=0) if compressed else raw


def colors(data: bytes) -> Counter[str]:
    found: Counter[str] = Counter()

    def record(value: str) -> str:
        found[value.lower()] += 1
        return value

    rewrite_text(_decode(data)[0], record)
    return found

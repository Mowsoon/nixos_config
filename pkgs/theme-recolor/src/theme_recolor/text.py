import re
from collections import Counter
from collections.abc import Callable

from theme_recolor.errors import FormatError

QUOTED_HEX = re.compile(r"""(["'])(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\1""")
RC_TRIPLE = re.compile(
    r"^(\w*Colou?r\w*\s*=\s*)(\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})\s*$", re.MULTILINE
)


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as err:
        raise FormatError("text file is not UTF-8") from err


def _triple(match: re.Match[str], convert: Callable[[str], str]) -> str:
    channels = [int(value) for value in match.group(2, 3, 4)]
    if any(value > 255 for value in channels):
        raise FormatError(f"colour out of range in {match.group(0)!r}")
    new = convert("#" + "".join(f"{value:02x}" for value in channels))
    r, g, b = (int(new[i : i + 2], 16) for i in (1, 3, 5))
    return f"{match.group(1)}{r}, {g}, {b}"


def recolor_qml(data: bytes, convert: Callable[[str], str]) -> bytes:
    text = QUOTED_HEX.sub(lambda m: m.group(1) + convert(m.group(2)) + m.group(1), _decode(data))
    return text.encode("utf-8")


def recolor_rc(data: bytes, convert: Callable[[str], str]) -> bytes:
    return RC_TRIPLE.sub(lambda m: _triple(m, convert), _decode(data)).encode("utf-8")


def _collect(rewrite: Callable[[bytes, Callable[[str], str]], bytes], data: bytes) -> Counter[str]:
    found: Counter[str] = Counter()

    def record(value: str) -> str:
        found[value.lower()] += 1
        return value

    rewrite(data, record)
    return found


def qml_colors(data: bytes) -> Counter[str]:
    return _collect(recolor_qml, data)


def rc_colors(data: bytes) -> Counter[str]:
    return _collect(recolor_rc, data)

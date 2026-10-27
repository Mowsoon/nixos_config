import pytest

from theme_recolor.mapping import Palette

BORDEAUX = {
    "base00": "1a0e11",
    "base01": "26151a",
    "base02": "3a1f27",
    "base03": "6b4a52",
    "base04": "a48a90",
    "base05": "e3d3d6",
    "base06": "f0e4e6",
    "base07": "faf3f4",
    "base08": "e06c75",
    "base09": "d9895b",
    "base0A": "d8b46a",
    "base0B": "9cba7f",
    "base0C": "7fb3ad",
    "base0D": "c04a63",
    "base0E": "b07fc0",
    "base0F": "8c4a3a",
}


@pytest.fixture
def palette() -> Palette:
    return Palette.from_hex(BORDEAUX)

import json
from pathlib import Path

import pytest

from theme_recolor.__main__ import run
from theme_recolor.errors import PaletteError, RecolorError

from .conftest import BORDEAUX


@pytest.fixture
def palette_file(tmp_path: Path) -> Path:
    path = tmp_path / "palette.json"
    path.write_text(json.dumps(BORDEAUX), encoding="utf-8")
    return path


def test_run_recolours_files_and_skips_symlinks(tmp_path: Path, palette_file: Path) -> None:
    theme = tmp_path / "theme"
    theme.mkdir()
    (theme / "icon.svg").write_text('<svg><rect fill="#ffffff"/></svg>', encoding="utf-8")
    (theme / "link.svg").symlink_to("icon.svg")
    (theme / "notes.txt").write_text("#ffffff", encoding="utf-8")
    assert run(["--palette", str(palette_file), str(theme)]) == 0
    assert (theme / "icon.svg").read_text(encoding="utf-8") == '<svg><rect fill="#faf3f4"/></svg>'
    assert (theme / "link.svg").is_symlink()
    assert (theme / "notes.txt").read_text(encoding="utf-8") == "#ffffff"


def test_run_applies_role_overrides(tmp_path: Path, palette_file: Path) -> None:
    theme = tmp_path / "theme"
    theme.mkdir()
    (theme / "a.svg").write_text('<svg><rect fill="#c04a63"/></svg>', encoding="utf-8")
    assert run(["--palette", str(palette_file), "--role", "red=base0D", str(theme)]) == 0
    assert (theme / "a.svg").read_text(encoding="utf-8") == '<svg><rect fill="#c04a63"/></svg>'


def test_run_rejects_malformed_role(tmp_path: Path, palette_file: Path) -> None:
    with pytest.raises(PaletteError):
        run(["--palette", str(palette_file), "--role", "red", str(tmp_path)])


def test_run_rejects_missing_directory(tmp_path: Path, palette_file: Path) -> None:
    with pytest.raises(RecolorError):
        run(["--palette", str(palette_file), str(tmp_path / "absent")])


def test_run_rejects_unreadable_palette(tmp_path: Path) -> None:
    with pytest.raises(PaletteError):
        run(["--palette", str(tmp_path / "absent.json"), str(tmp_path)])

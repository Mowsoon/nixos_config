import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from theme_recolor import tree
from theme_recolor.convert import Converter
from theme_recolor.errors import PaletteError, RecolorError
from theme_recolor.mapping import Palette
from theme_recolor.recolor import build

logger = logging.getLogger("theme-recolor")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="theme-recolor")
    parser.add_argument("--palette", type=Path, required=True)
    parser.add_argument("--role", action="append", default=[], metavar="FAMILY=SLOT")
    parser.add_argument("directory", type=Path)
    return parser


def _roles(pairs: Sequence[str]) -> dict[str, str]:
    roles: dict[str, str] = {}
    for pair in pairs:
        name, separator, slot = pair.partition("=")
        if not separator or not name or not slot:
            raise PaletteError(f"role {pair!r} is not FAMILY=SLOT")
        roles[name] = slot
    return roles


def _palette(path: Path) -> Palette:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise PaletteError(f"read palette {path}") from err
    if not isinstance(raw, dict) or not all(isinstance(v, str) for v in raw.values()):
        raise PaletteError(f"palette {path} is not an object of strings")
    return Palette.from_hex({str(k): str(v) for k, v in raw.items()})


def run(argv: Sequence[str]) -> int:
    args = _parser().parse_args(argv)
    if not args.directory.is_dir():
        raise RecolorError(f"{args.directory} is not a directory")
    mapping = build(_palette(args.palette), tree.collect(args.directory), _roles(args.role))
    changed = tree.recolor(args.directory, Converter(mapping.apply))
    logger.info("recoloured %d files in %s", changed, args.directory)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    try:
        return run(sys.argv[1:])
    except RecolorError:
        logger.exception("recolouring failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

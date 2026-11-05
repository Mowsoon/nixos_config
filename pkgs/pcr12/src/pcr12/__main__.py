import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import fields
from pathlib import Path

from pcr12 import reseal
from pcr12.errors import Pcr12Error
from pcr12.reseal import Paths, Resealer
from pcr12.system import SubprocessRunner

DEFAULTS = Paths(
    event_log=Path("/sys/kernel/security/tpm0/binary_bios_measurements"),
    esp=Path("/boot"),
    policy=Path("/var/lib/systemd/pcrlock.json"),
    state=Path("/var/lib/pcr12/enrollment.json"),
    marker=Path("/run/pcr12/verified"),
    pcrs=Path("/sys/class/tpm/tpm0/pcr-sha256"),
    mapping=Path("/dev/mapper/cryptroot"),
    sysfs=Path("/sys"),
)

logger = logging.getLogger("pcr12")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pcr12")
    for field in fields(Paths):
        option = "--" + field.name.replace("_", "-")
        parser.add_argument(option, type=Path, default=getattr(DEFAULTS, field.name))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    seal = commands.add_parser("reseal")
    seal.add_argument("--ask-key", action="store_true")
    return parser


def run(argv: Sequence[str]) -> int:
    args = _parser().parse_args(argv)
    paths = Paths(*(getattr(args, field.name) for field in fields(Paths)))
    if args.command == "check":
        reseal.check(paths)
        return 0
    Resealer(paths, SubprocessRunner()).run(ask_key=args.ask_key)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    try:
        return run(sys.argv[1:])
    except Pcr12Error:
        logger.exception("refused")
        return 1


if __name__ == "__main__":
    sys.exit(main())

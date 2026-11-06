import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pcrlock_esp.components import ComponentWriter
from pcrlock_esp.errors import PcrlockEspError
from pcrlock_esp.esp import Esp, whole_disk
from pcrlock_esp.gpt import GptMeasurement, Runner
from pcrlock_esp.records import boot_loader_config_variants
from pcrlock_esp.selection import booted_entry
from pcrlock_esp.system import SubprocessRunner

GENERATIONS_COMPONENT = "650-lanzaboote-generations"
BOOT_LOADER_CONFIG_COMPONENT = "600-boot-loader-config"

logger = logging.getLogger("pcrlock-esp")


@dataclass(frozen=True, slots=True)
class Options:
    esp: Path
    esp_device: Path
    directory: Path
    pcrlock: Path
    sysfs: Path
    efivars: Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pcrlock-esp")
    parser.add_argument("--esp", type=Path, default=Path("/boot"))
    parser.add_argument("--esp-device", type=Path, required=True)
    parser.add_argument("--directory", type=Path, default=Path("/var/lib/pcrlock.d"))
    parser.add_argument("--pcrlock", type=Path, required=True)
    parser.add_argument("--sysfs", type=Path, default=Path("/sys"))
    parser.add_argument("--efivars", type=Path, default=Path("/sys/firmware/efi/efivars"))
    return parser


def write_components(options: Options, runner: Runner) -> None:
    esp = Esp(options.esp)
    writer = ComponentWriter(options.directory)
    generations = esp.generations(booted_entry(options.efivars))
    writer.write_variants(GENERATIONS_COMPONENT, generations)
    gpt = GptMeasurement(options.pcrlock, runner).digest(
        whole_disk(options.esp_device, options.sysfs)
    )
    writer.write_variants(
        BOOT_LOADER_CONFIG_COMPONENT, boot_loader_config_variants(gpt, esp.loader_conf())
    )
    logger.info(
        "wrote PCR 5 and the PCR 11 records of %d of %d generations",
        len(generations),
        len(esp.stubs()),
    )


def run(argv: Sequence[str], runner: Runner) -> int:
    args = _parser().parse_args(argv)
    write_components(
        Options(args.esp, args.esp_device, args.directory, args.pcrlock, args.sysfs, args.efivars),
        runner,
    )
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    try:
        return run(sys.argv[1:], SubprocessRunner())
    except PcrlockEspError:
        logger.exception("refused")
        return 1


if __name__ == "__main__":
    sys.exit(main())

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from pcr0_predict import eventlog, firmware, pcrlock, prediction
from pcr0_predict.errors import CalibrationError, InputError, PredictError
from pcr0_predict.prediction import Calibration

EVENT_LOG = Path("/sys/kernel/security/tpm0/binary_bios_measurements")
FIRMWARE_CODE = Path("/var/lib/pcrlock.d/250-firmware-code-early.pcrlock.d")
GENERATED = FIRMWARE_CODE / "generated.pcrlock"
PREDICTED = FIRMWARE_CODE / "predicted.pcrlock"

logger = logging.getLogger("pcr0-predict")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pcr0-predict")
    parser.add_argument("--event-log", type=Path, default=EVENT_LOG)
    parser.add_argument("--generated", type=Path, default=GENERATED)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("current", type=Path)
    predict = commands.add_parser("predict")
    predict.add_argument("--output", type=Path, default=PREDICTED)
    predict.add_argument("current", type=Path)
    predict.add_argument("new", type=Path)
    return parser


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as err:
        raise InputError(f"read {path}") from err


def _calibrate(args: argparse.Namespace) -> tuple[Calibration, list[pcrlock.Record]]:
    records = eventlog.firmware_code(eventlog.parse(_read(args.event_log)))
    measured = [record.sha256 for record in records]
    generated = pcrlock.read(args.generated)
    if pcrlock.pcr0_digests(generated) != measured:
        raise CalibrationError(f"{args.generated} does not hold the PCR 0 records of the event log")
    image = firmware.strip_capsule(_read(args.current))
    calibration = prediction.calibrate(records, image)
    if prediction.predict(calibration, image) != measured:
        raise CalibrationError(f"{args.current} does not reproduce PCR 0 of the running firmware")
    modules = ", ".join(sorted(str(guid) for guid in calibration.crtm_modules))
    logger.info("S-CRTM data %s stored by %s", calibration.crtm_data.hex(), modules)
    logger.info("measured volume %s", calibration.volume_name)
    logger.info("%s reproduces PCR 0 of the running firmware", args.current)
    return calibration, generated


def _predict(args: argparse.Namespace) -> int:
    calibration, generated = _calibrate(args)
    digests = prediction.predict(calibration, firmware.strip_capsule(_read(args.new)))
    for digest in digests:
        logger.info("predicted PCR 0 record %s", digest.hex())
    if digests == pcrlock.pcr0_digests(generated):
        logger.info("%s measures the same PCR 0, no variant is needed", args.new)
        return 0
    pcrlock.write(args.output, pcrlock.render(pcrlock.variant(generated, digests)))
    logger.info("wrote %s", args.output)
    return 0


def run(argv: Sequence[str]) -> int:
    args = _parser().parse_args(argv)
    if args.command == "check":
        _calibrate(args)
        return 0
    return _predict(args)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    try:
        return run(sys.argv[1:])
    except PredictError:
        logger.exception("prediction refused")
        return 1


if __name__ == "__main__":
    sys.exit(main())

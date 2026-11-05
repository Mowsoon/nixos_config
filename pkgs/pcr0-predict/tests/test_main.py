import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from pcr0_predict import __main__ as cli
from pcr0_predict import pcrlock
from pcr0_predict.errors import CalibrationError
from tests import builders
from tests.conftest import NEW_PAYLOAD, PAYLOAD


@dataclass(frozen=True, slots=True)
class Machine:
    log: Path
    generated: Path
    current: Path
    new: Path
    output: Path

    def args(self, *command: str) -> list[str]:
        return ["--event-log", str(self.log), "--generated", str(self.generated), *command]


@pytest.fixture
def machine(tmp_path: Path, current_log: bytes, current_image: bytes, new_image: bytes) -> Machine:
    paths = Machine(
        *(tmp_path / name for name in ("log", "generated.pcrlock", "current", "new", "out"))
    )
    paths.log.write_bytes(current_log)
    measured = [hashlib.sha256(builders.CRTM).digest(), _main_digest(PAYLOAD)]
    paths.generated.write_text(
        pcrlock.render([pcrlock.Record(0, digest) for digest in measured]), encoding="utf-8"
    )
    paths.current.write_bytes(builders.capsule(current_image))
    paths.new.write_bytes(builders.capsule(new_image))
    return paths


def _main_digest(payload: bytes) -> bytes:
    return hashlib.sha256(builders.main_volume(payload)).digest()


def test_check_accepts_the_running_firmware(machine: Machine) -> None:
    assert cli.run(machine.args("check", str(machine.current))) == 0


def test_predict_writes_a_variant_with_the_new_volume(machine: Machine) -> None:
    cli.run(
        machine.args(
            "predict", "--output", str(machine.output), str(machine.current), str(machine.new)
        )
    )
    assert pcrlock.pcr0_digests(pcrlock.read(machine.output))[1] == _main_digest(NEW_PAYLOAD)


def test_predict_writes_nothing_for_the_same_firmware(machine: Machine) -> None:
    command = (
        "predict",
        "--output",
        str(machine.output),
        str(machine.current),
        str(machine.current),
    )
    cli.run(machine.args(*command))
    assert not machine.output.exists()


def test_check_raises_when_generated_file_is_stale(machine: Machine) -> None:
    machine.generated.write_text(
        pcrlock.render([pcrlock.Record(0, b"\x00" * 32)]), encoding="utf-8"
    )
    with pytest.raises(CalibrationError, match="does not hold the PCR 0 records"):
        cli.run(machine.args("check", str(machine.current)))


def test_main_returns_one_when_prediction_is_refused(
    machine: Machine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.argv", ["pcr0-predict", *machine.args("check", str(machine.new))])
    assert cli.main() == 1

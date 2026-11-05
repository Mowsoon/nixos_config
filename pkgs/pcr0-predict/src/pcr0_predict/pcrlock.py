import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pcr0_predict.errors import PcrlockError

SHA256 = "sha256"
VARIANT_MODE = 0o644


@dataclass(frozen=True, slots=True)
class Record:
    pcr: int
    sha256: bytes


def _record(raw: object) -> Record:
    if not isinstance(raw, dict):
        raise PcrlockError("pcrlock record is not an object")
    pcr = raw.get("pcr")
    digests = raw.get("digests")
    if not isinstance(pcr, int) or not isinstance(digests, list):
        raise PcrlockError("pcrlock record has no PCR or no digest list")
    for digest in digests:
        if isinstance(digest, dict) and digest.get("hashAlg") == SHA256:
            value = digest.get("digest")
            if isinstance(value, str):
                return Record(pcr, bytes.fromhex(value))
    raise PcrlockError(f"pcrlock record of PCR {pcr} has no SHA-256 digest")


def parse(text: str) -> list[Record]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as err:
        raise PcrlockError("pcrlock file is not JSON") from err
    if not isinstance(raw, dict) or not isinstance(raw.get("records"), list):
        raise PcrlockError("pcrlock file has no record list")
    try:
        return [_record(record) for record in raw["records"]]
    except ValueError as err:
        raise PcrlockError("pcrlock digest is not hexadecimal") from err


def read(path: Path) -> list[Record]:
    try:
        return parse(path.read_text(encoding="utf-8"))
    except OSError as err:
        raise PcrlockError(f"read {path}") from err


def pcr0_digests(records: Sequence[Record]) -> list[bytes]:
    return [record.sha256 for record in records if record.pcr == 0]


def variant(records: Sequence[Record], digests: Sequence[bytes]) -> list[Record]:
    if len(pcr0_digests(records)) != len(digests):
        raise PcrlockError(
            "the recorded firmware code does not have the predicted number of records"
        )
    remaining = iter(digests)
    return [Record(0, next(remaining)) if record.pcr == 0 else record for record in records]


def render(records: Sequence[Record]) -> str:
    entries = [
        {"pcr": record.pcr, "digests": [{"hashAlg": SHA256, "digest": record.sha256.hex()}]}
        for record in records
    ]
    return json.dumps({"records": entries}, indent=2) + "\n"


def write(path: Path, text: str) -> None:
    try:
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    except OSError as err:
        raise PcrlockError(f"create a file next to {path}") from err
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temporary, VARIANT_MODE)
        os.replace(temporary, path)
    except OSError as err:
        Path(temporary).unlink(missing_ok=True)
        raise PcrlockError(f"write {path}") from err

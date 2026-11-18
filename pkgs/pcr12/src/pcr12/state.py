import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from pcr12.errors import InputError

STATE_MODE = 0o600
FIELDS = ("pcr7", "pcr12", "policy_hash")


@dataclass(frozen=True, slots=True)
class Enrollment:
    pcr7: str
    pcr12: str
    policy_hash: str


def _enrollment(raw: object, path: Path) -> Enrollment:
    if not isinstance(raw, dict):
        raise InputError(f"{path} holds a slot that is not an object")
    values = [raw.get(field) for field in FIELDS]
    if not all(isinstance(value, str) for value in values):
        raise InputError(f"{path} misses a field")
    return Enrollment(*(str(value) for value in values))


def load(path: Path) -> list[Enrollment]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as err:
        raise InputError(f"read {path}") from err
    if not isinstance(raw, dict):
        raise InputError(f"{path} is not an object")
    if "slots" not in raw:
        return [_enrollment(raw, path)]
    slots = raw["slots"]
    if not isinstance(slots, list):
        raise InputError(f"{path} has an invalid slot list")
    return [_enrollment(slot, path) for slot in slots]


def _document(enrollments: Sequence[Enrollment]) -> dict[str, object]:
    single = asdict(enrollments[-1]) if enrollments else {}
    return {**single, "slots": [asdict(enrollment) for enrollment in enrollments]}


def save(path: Path, enrollments: Sequence[Enrollment]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(_document(enrollments), handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(handle.name, STATE_MODE)
    os.replace(handle.name, path)

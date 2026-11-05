import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from pcr12.errors import InputError

STATE_MODE = 0o600


@dataclass(frozen=True, slots=True)
class Enrollment:
    pcr7: str
    pcr12: str
    policy_hash: str


def load(path: Path) -> Enrollment | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as err:
        raise InputError(f"read {path}") from err
    if not isinstance(raw, dict):
        raise InputError(f"{path} is not an object")
    values = [raw.get(field) for field in ("pcr7", "pcr12", "policy_hash")]
    if not all(isinstance(value, str) for value in values):
        raise InputError(f"{path} misses a field")
    return Enrollment(*(str(value) for value in values))


def save(path: Path, enrollment: Enrollment) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(asdict(enrollment), handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(handle.name, STATE_MODE)
    os.replace(handle.name, path)

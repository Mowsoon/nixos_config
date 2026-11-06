import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from pcrlock_esp.errors import WriteError
from pcrlock_esp.records import Record

SUFFIX = ".pcrlock"
VARIANTS_SUFFIX = ".pcrlock.d"
MODE = 0o644


def render(records: Sequence[Record]) -> str:
    entries = [
        {"pcr": record.pcr, "digests": [{"hashAlg": "sha256", "digest": record.digest.hex()}]}
        for record in records
    ]
    return json.dumps({"records": entries}, sort_keys=True) + "\n"


class ComponentWriter:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def write(self, name: str, records: Sequence[Record]) -> None:
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            _replace(self._directory / f"{name}{SUFFIX}", render(records))
        except OSError as err:
            raise WriteError(f"write component {name} in {self._directory}") from err

    def write_variants(self, name: str, variants: Mapping[str, Sequence[Record]]) -> None:
        directory = self._directory / f"{name}{VARIANTS_SUFFIX}"
        wanted = {f"{variant}{SUFFIX}" for variant in variants}
        try:
            directory.mkdir(parents=True, exist_ok=True)
            for variant, records in variants.items():
                _replace(directory / f"{variant}{SUFFIX}", render(records))
            for stale in directory.glob(f"*{SUFFIX}"):
                if stale.name not in wanted:
                    stale.unlink()
        except OSError as err:
            raise WriteError(f"write the variants of component {name} in {directory}") from err


def _replace(target: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=target.parent, prefix=".", suffix=".tmp", delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    try:
        temporary.chmod(MODE)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)

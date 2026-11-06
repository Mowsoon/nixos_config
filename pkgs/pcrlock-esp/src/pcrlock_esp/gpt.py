import json
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from pcrlock_esp.errors import InputError
from pcrlock_esp.records import BOOT_LOADER_CONFIG_PCR, DIGEST_SIZE


class Runner(Protocol):
    def run(self, args: Sequence[str]) -> None: ...


class GptMeasurement:
    def __init__(self, pcrlock: Path, runner: Runner) -> None:
        self._pcrlock = pcrlock
        self._runner = runner

    def digest(self, disk: Path) -> bytes:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "gpt.pcrlock"
            self._runner.run([str(self._pcrlock), "lock-gpt", str(disk), f"--pcrlock={output}"])
            try:
                content = output.read_text(encoding="utf-8")
            except OSError as err:
                raise InputError(f"lock-gpt wrote no component for {disk}") from err
        return parse_gpt_component(content)


def parse_gpt_component(content: str) -> bytes:
    try:
        document = json.loads(content)
    except json.JSONDecodeError as err:
        raise InputError("the GPT component is not JSON") from err
    records = document.get("records") if isinstance(document, dict) else None
    if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
        raise InputError("the GPT component does not hold exactly one record")
    record = records[0]
    if record.get("pcr") != BOOT_LOADER_CONFIG_PCR:
        raise InputError("the GPT component does not measure PCR 5")
    return _sha256_digest(record.get("digests"))


def _sha256_digest(digests: object) -> bytes:
    if not isinstance(digests, list):
        raise InputError("the GPT record has no digest list")
    for entry in digests:
        if isinstance(entry, dict) and entry.get("hashAlg") == "sha256":
            return _hex_digest(entry.get("digest"))
    raise InputError("the GPT record has no SHA-256 digest")


def _hex_digest(value: object) -> bytes:
    if not isinstance(value, str):
        raise InputError("the GPT digest is not a string")
    try:
        digest = bytes.fromhex(value)
    except ValueError as err:
        raise InputError("the GPT digest is not hexadecimal") from err
    if len(digest) != DIGEST_SIZE:
        raise InputError("the GPT digest is not a SHA-256 digest")
    return digest

import re
from collections.abc import Sequence
from pathlib import Path

from pcrlock_esp.errors import InputError

MAX_GENERATIONS = 8
GENERATION_NUMBER = re.compile(r"nixos-generation-(\d+)")
LOADER_ENTRY_SELECTED = "LoaderEntrySelected-4a67b082-0a4c-41cf-b6c7-440b29bb8c4f"
EFI_VARIABLE_HEADER_SIZE = 4


def newest(stubs: Sequence[Path], booted: str | None, limit: int = MAX_GENERATIONS) -> list[Path]:
    ordered = sorted(stubs, key=_order, reverse=True)
    chosen = ordered[:limit]
    booted_stub = next((stub for stub in stubs if stub.name == booted), None)
    if booted_stub is None or booted_stub in chosen:
        return chosen
    return [*ordered[: limit - 1], booted_stub]


def booted_entry(efivars: Path) -> str | None:
    variable = efivars / LOADER_ENTRY_SELECTED
    try:
        raw = variable.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as err:
        raise InputError(f"read {variable}") from err
    try:
        return raw[EFI_VARIABLE_HEADER_SIZE:].decode("utf-16-le").rstrip("\0")
    except UnicodeDecodeError as err:
        raise InputError(f"{variable} is not UTF-16") from err


def _order(stub: Path) -> tuple[int, str]:
    match = GENERATION_NUMBER.search(stub.name)
    return (int(match.group(1)) if match else -1, stub.name)

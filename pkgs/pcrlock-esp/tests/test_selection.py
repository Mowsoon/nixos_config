from pathlib import Path

import pytest

from pcrlock_esp.errors import InputError
from pcrlock_esp.selection import LOADER_ENTRY_SELECTED, booted_entry, newest

STUBS = [Path(f"nixos-generation-{number}-x.efi") for number in range(75, 85)]


def _numbers(stubs: list[Path]) -> list[int]:
    return sorted(int(stub.name.split("-")[2]) for stub in stubs)


def test_newest_keeps_the_eight_most_recent_generations() -> None:
    assert _numbers(newest(STUBS, None)) == list(range(77, 85))


def test_newest_keeps_the_booted_generation_when_it_is_recent() -> None:
    assert _numbers(newest(STUBS, "nixos-generation-80-x.efi")) == list(range(77, 85))


def test_newest_replaces_the_oldest_kept_generation_with_an_older_booted_one() -> None:
    kept = newest(STUBS, "nixos-generation-75-x.efi")
    assert _numbers(kept) == [75, *range(78, 85)]


def test_newest_ignores_a_booted_entry_that_is_not_a_stub_of_the_esp() -> None:
    assert _numbers(newest(STUBS, "auto-windows")) == list(range(77, 85))


def test_newest_orders_generations_by_number_not_by_name() -> None:
    stubs = [Path("nixos-generation-9-x.efi"), Path("nixos-generation-10-x.efi")]
    assert newest(stubs, None, limit=1) == [Path("nixos-generation-10-x.efi")]


def test_booted_entry_decodes_the_utf16_variable_after_its_attributes(tmp_path: Path) -> None:
    name = "nixos-generation-84-x.efi"
    data = b"\x06\x00\x00\x00" + (name + "\0").encode("utf-16-le")
    (tmp_path / LOADER_ENTRY_SELECTED).write_bytes(data)
    assert booted_entry(tmp_path) == name


def test_booted_entry_is_none_when_the_loader_set_no_variable(tmp_path: Path) -> None:
    assert booted_entry(tmp_path) is None


def test_booted_entry_raises_when_the_variable_is_not_utf16(tmp_path: Path) -> None:
    (tmp_path / LOADER_ENTRY_SELECTED).write_bytes(b"\x06\x00\x00\x00\xff")
    with pytest.raises(InputError):
        booted_entry(tmp_path)

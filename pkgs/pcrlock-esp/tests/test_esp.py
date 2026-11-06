from pathlib import Path

import pytest

from pcrlock_esp.errors import InputError
from pcrlock_esp.esp import Esp, whole_disk
from pcrlock_esp.records import generation_records
from tests import builders


def _esp(tmp_path: Path, stubs: list[str]) -> Esp:
    directory = tmp_path / "EFI" / "Linux"
    directory.mkdir(parents=True)
    for stub in stubs:
        (directory / stub).write_bytes(builders.pe_image(builders.stub_sections()))
    (tmp_path / "loader").mkdir()
    (tmp_path / "loader" / "loader.conf").write_bytes(b"default nixos-*\n")
    return Esp(tmp_path)


def test_generations_maps_each_stub_to_its_records(tmp_path: Path) -> None:
    esp = _esp(tmp_path, ["nixos-generation-81-a.efi", "nixos-generation-82-b.efi"])
    expected = generation_records(builders.stub_sections())
    assert esp.generations() == {
        "nixos-generation-81-a": expected,
        "nixos-generation-82-b": expected,
    }


def test_generations_ignores_hidden_temporary_stubs(tmp_path: Path) -> None:
    esp = _esp(tmp_path, ["nixos-generation-82-b.efi", ".nixos-generation-83-c.efi"])
    assert list(esp.generations()) == ["nixos-generation-82-b"]


def test_generations_raises_when_the_esp_holds_no_stub(tmp_path: Path) -> None:
    with pytest.raises(InputError):
        _esp(tmp_path, []).generations()


def test_loader_conf_reads_the_systemd_boot_configuration(tmp_path: Path) -> None:
    assert _esp(tmp_path, []).loader_conf() == b"default nixos-*\n"


def _sysfs(tmp_path: Path, partition: str, disk: str, *, is_partition: bool = True) -> Path:
    device = tmp_path / "devices" / disk / partition
    device.mkdir(parents=True)
    if is_partition:
        (device / "partition").write_text("1\n", encoding="utf-8")
    block = tmp_path / "class" / "block"
    block.mkdir(parents=True)
    (block / partition).symlink_to(device)
    return tmp_path


def test_whole_disk_returns_the_parent_disk_of_the_partition(tmp_path: Path) -> None:
    sysfs = _sysfs(tmp_path / "sys", "nvme1n1p1", "nvme1n1")
    partition = tmp_path / "nvme1n1p1"
    partition.touch()
    assert whole_disk(partition, sysfs) == Path("/dev/nvme1n1")


def test_whole_disk_raises_when_the_device_is_not_a_partition(tmp_path: Path) -> None:
    sysfs = _sysfs(tmp_path / "sys", "nvme1n1p1", "nvme1n1", is_partition=False)
    partition = tmp_path / "nvme1n1p1"
    partition.touch()
    with pytest.raises(InputError):
        whole_disk(partition, sysfs)

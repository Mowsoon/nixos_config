import json
from pathlib import Path

from pcrlock_esp.__main__ import run
from tests import builders
from tests.test_gpt import WritingRunner

DIGEST = "cd" * 32


def _prepare(tmp_path: Path) -> list[str]:
    esp = tmp_path / "esp"
    (esp / "EFI" / "Linux").mkdir(parents=True)
    (esp / "EFI" / "Linux" / "nixos-generation-82-b.efi").write_bytes(
        builders.pe_image(builders.stub_sections())
    )
    (esp / "loader").mkdir()
    (esp / "loader" / "loader.conf").write_bytes(b"default nixos-*\n")
    device = tmp_path / "sys" / "devices" / "nvme1n1" / "nvme1n1p1"
    device.mkdir(parents=True)
    (device / "partition").write_text("1\n", encoding="utf-8")
    (tmp_path / "sys" / "class" / "block").mkdir(parents=True)
    (tmp_path / "sys" / "class" / "block" / "nvme1n1p1").symlink_to(device)
    (tmp_path / "nvme1n1p1").touch()
    return [
        f"--esp={esp}",
        f"--esp-device={tmp_path / 'nvme1n1p1'}",
        f"--directory={tmp_path / 'pcrlock.d'}",
        "--pcrlock=/pcrlock",
        f"--sysfs={tmp_path / 'sys'}",
        f"--efivars={tmp_path / 'efivars'}",
    ]


def test_run_writes_the_pcr_5_and_pcr_11_components(tmp_path: Path) -> None:
    runner = WritingRunner(builders.gpt_component(DIGEST))
    assert run(_prepare(tmp_path), runner) == 0
    directory = tmp_path / "pcrlock.d"
    boot_variants = directory / "600-boot-loader-config.pcrlock.d"
    boot = json.loads(
        (boot_variants / "300-gpt-before-each-image.pcrlock").read_text(encoding="utf-8")
    )
    generation = (
        directory / "650-lanzaboote-generations.pcrlock.d" / "nixos-generation-82-b.pcrlock"
    )
    assert [record["pcr"] for record in boot["records"]] == [5, 5, 5]
    assert len(json.loads(generation.read_text(encoding="utf-8"))["records"]) == 8
    assert runner.commands[0][2] == "/dev/nvme1n1"

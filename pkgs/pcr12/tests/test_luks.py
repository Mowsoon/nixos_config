from pathlib import Path

import pytest

from pcr12 import luks
from pcr12.errors import InputError
from tests import builders

POLICY = Path("/var/lib/systemd/pcrlock.json")
DEVICE = Path("/dev/nvme0n1p2")


def test_tpm2_tokens_keep_only_tpm2_tokens() -> None:
    metadata = builders.luks_metadata(
        [{"type": "systemd-recovery"}, builders.tpm2_token([12, 7], "ab")]
    )
    assert luks.tpm2_tokens(metadata) == [luks.Token((7, 12), True, "ab")]


@pytest.mark.parametrize(
    ("pcrs", "pcrlock", "sealed"),
    [([7, 12], True, True), ([7], True, False), ([7, 12], False, False)],
)
def test_token_is_sealed_with_pcrlock_and_pcrs_7_and_12(
    pcrs: list[int], pcrlock: bool, sealed: bool
) -> None:
    metadata = builders.luks_metadata([builders.tpm2_token(pcrs, "ab", pcrlock=pcrlock)])
    assert luks.tpm2_tokens(metadata)[0].sealed is sealed


def test_tpm2_tokens_refuse_metadata_that_is_not_json() -> None:
    with pytest.raises(InputError):
        luks.tpm2_tokens(b"not json")


def test_enroll_command_unlocks_with_the_tpm2_by_default() -> None:
    command = luks.enroll_command(DEVICE, POLICY, bytes(32), ask_key=False)
    assert command == [
        "systemd-cryptenroll",
        str(DEVICE),
        "--tpm2-device=auto",
        f"--tpm2-pcrlock={POLICY}",
        f"--tpm2-pcrs=7+12:sha256={'00' * 32}",
        "--wipe-slot=tpm2",
        "--unlock-tpm2-device=auto",
    ]


def test_enroll_command_asks_for_a_key_when_requested() -> None:
    command = luks.enroll_command(DEVICE, POLICY, bytes(32), ask_key=True)
    assert "--unlock-tpm2-device=auto" not in command


def test_backing_device_follows_the_mapping(tmp_path: Path) -> None:
    (tmp_path / "dm-3").touch()
    (tmp_path / "cryptroot").symlink_to(tmp_path / "dm-3")
    (tmp_path / "block" / "dm-3" / "slaves" / "sda2").mkdir(parents=True)
    assert luks.backing_device(tmp_path / "cryptroot", tmp_path) == Path("/dev/sda2")


def test_backing_device_refuses_a_mapping_on_two_devices(tmp_path: Path) -> None:
    (tmp_path / "dm-3").touch()
    for name in ("sda2", "sdb2"):
        (tmp_path / "block" / "dm-3" / "slaves" / name).mkdir(parents=True)
    with pytest.raises(InputError):
        luks.backing_device(tmp_path / "dm-3", tmp_path)

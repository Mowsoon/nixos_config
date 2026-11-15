import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pcr12.errors import InputError

TPM2_SLOT_TYPE = "systemd-tpm2"
SEALED_PCRS = (7, 12)


@dataclass(frozen=True, slots=True)
class Token:
    pcrs: tuple[int, ...]
    pcrlock: bool
    policy_hash: str
    keyslots: tuple[int, ...]

    @property
    def sealed(self) -> bool:
        return self.pcrlock and self.pcrs == SEALED_PCRS


def _keyslots(raw: dict[str, object]) -> tuple[int, ...]:
    keyslots = raw.get("keyslots", [])
    if not isinstance(keyslots, list) or not all(
        isinstance(keyslot, str) and keyslot.isdigit() for keyslot in keyslots
    ):
        raise InputError("TPM2 token has an invalid keyslot list")
    return tuple(sorted(int(keyslot) for keyslot in keyslots))


def _token(raw: dict[str, object]) -> Token:
    pcrs = raw.get("tpm2-pcrs", [])
    policy_hash = raw.get("tpm2-policy-hash", "")
    if not isinstance(pcrs, list) or not all(isinstance(pcr, int) for pcr in pcrs):
        raise InputError("TPM2 token has an invalid PCR list")
    if not isinstance(policy_hash, str):
        raise InputError("TPM2 token has an invalid policy hash")
    pcrlock = raw.get("tpm2_pcrlock") is True
    return Token(tuple(sorted(pcrs)), pcrlock, policy_hash, _keyslots(raw))


def tpm2_tokens(metadata: bytes) -> list[Token]:
    try:
        raw = json.loads(metadata)
    except json.JSONDecodeError as err:
        raise InputError("LUKS2 metadata is not JSON") from err
    tokens = raw.get("tokens") if isinstance(raw, dict) else None
    if not isinstance(tokens, dict):
        raise InputError("LUKS2 metadata has no token table")
    return [
        _token(token)
        for token in tokens.values()
        if isinstance(token, dict) and token.get("type") == TPM2_SLOT_TYPE
    ]


def dump_command(device: Path) -> list[str]:
    return ["cryptsetup", "luksDump", "--dump-json-metadata", str(device)]


def _wipe_option(keyslots: Sequence[int]) -> list[str]:
    if not keyslots:
        return []
    return ["--wipe-slot=" + ",".join(str(keyslot) for keyslot in sorted(keyslots))]


def enroll_command(
    device: Path, policy: Path, pcr12: bytes, *, wipe: Sequence[int], ask_key: bool
) -> list[str]:
    command = [
        "systemd-cryptenroll",
        str(device),
        "--tpm2-device=auto",
        f"--tpm2-pcrlock={policy}",
        f"--tpm2-pcrs=7+12:sha256={pcr12.hex()}",
        *_wipe_option(wipe),
    ]
    if not ask_key:
        command.append("--unlock-tpm2-device=auto")
    return command


def wipe_command(device: Path, keyslots: Sequence[int]) -> list[str]:
    return ["systemd-cryptenroll", str(device), *_wipe_option(keyslots)]


def backing_device(mapping: Path, sysfs: Path) -> Path:
    mapper = mapping.resolve().name
    slaves_directory = sysfs / "block" / mapper / "slaves"
    try:
        slaves = sorted(slaves_directory.iterdir())
    except OSError as err:
        raise InputError(f"list the devices under {mapping}") from err
    if len(slaves) != 1:
        raise InputError(f"{mapping} does not sit on exactly one device")
    return Path("/dev") / slaves[0].name

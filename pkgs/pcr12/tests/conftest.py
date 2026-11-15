import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from pcr12 import measure
from pcr12.errors import EnrollError
from pcr12.measure import Credential
from pcr12.reseal import Paths
from tests import builders

POLICY = b'{"pcrValues": []}\n'
POLICY_CREDENTIAL = "pcrlock.0123456789abcdef.cred"
PCR7 = bytes(range(32))
PCRS_OPTION = "--tpm2-pcrs=7+12:sha256="
WIPE_OPTION = "--wipe-slot="
FIRST_TPM2_KEYSLOT = 2


@dataclass(frozen=True, slots=True)
class FakeSlot:
    pcrs: tuple[int, ...]
    pcr7: str
    pcr12: str | None

    @property
    def policy_hash(self) -> str:
        return hashlib.sha256(f"{self.pcr7}:{self.pcr12}".encode("ascii")).hexdigest()


class FakeRunner:
    def __init__(self, pcrs: Path) -> None:
        self.pcrs = pcrs
        self.slots: dict[int, FakeSlot] = {FIRST_TPM2_KEYSLOT: FakeSlot((7,), PCR7.hex(), None)}
        self.commands: list[tuple[list[str], bool]] = []
        self.enroll_fails = False
        self.enroll_adds_no_slot = False

    def run(self, args: Sequence[str], stdin: bytes = b"", *, interactive: bool = False) -> bytes:
        self.commands.append((list(args), interactive))
        if args[0] == "systemd-creds":
            return stdin
        if args[0] == "cryptsetup":
            return self.metadata()
        options = {arg.split("=", 1)[0]: arg for arg in args[2:]}
        new = self._enroll(options, interactive=interactive) if "--tpm2-pcrs" in options else None
        if "--wipe-slot" in options:
            for keyslot in options["--wipe-slot"].removeprefix(WIPE_OPTION).split(","):
                if int(keyslot) != new:
                    del self.slots[int(keyslot)]
        return b""

    def _enroll(self, options: dict[str, str], *, interactive: bool) -> int | None:
        if self.enroll_fails or not (interactive or self.unlocks()):
            raise EnrollError("systemd-cryptenroll failed")
        if self.enroll_adds_no_slot:
            return None
        keyslot = max([FIRST_TPM2_KEYSLOT - 1, *self.slots]) + 1
        pcr12 = options["--tpm2-pcrs"].removeprefix(PCRS_OPTION)
        self.slots[keyslot] = FakeSlot((7, 12), self._pcr(7), pcr12)
        return keyslot

    def _pcr(self, index: int) -> str:
        return (self.pcrs / str(index)).read_text(encoding="ascii").strip().lower()

    def unlocks(self) -> bool:
        return any(
            slot.pcr7 == self._pcr(7) and slot.pcr12 in (None, self._pcr(12))
            for slot in self.slots.values()
        )

    def metadata(self) -> bytes:
        tokens: list[dict[str, object]] = [{"type": "systemd-recovery", "keyslots": ["1"]}]
        tokens += [
            builders.tpm2_token(slot.pcrs, slot.policy_hash, keyslot=keyslot)
            for keyslot, slot in sorted(self.slots.items())
        ]
        return builders.luks_metadata(tokens)

    def sealed_pcr12(self) -> list[str | None]:
        return [slot.pcr12 for _, slot in sorted(self.slots.items())]

    def enrollments(self) -> list[tuple[list[str], bool]]:
        return [
            entry
            for entry in self.commands
            if entry[0][0] == "systemd-cryptenroll"
            and any(arg.startswith(PCRS_OPTION) for arg in entry[0])
        ]


class Machine:
    def __init__(self, root: Path) -> None:
        self.paths = Paths(
            event_log=root / "measurements",
            esp=root / "boot",
            policy=root / "pcrlock.json",
            state=root / "state" / "enrollment.json",
            marker=root / "run" / "verified",
            pcrs=root / "pcr-sha256",
            mapping=root / "mapper" / "cryptroot",
            sysfs=root / "sys",
        )
        self.credentials = self.paths.esp / "loader" / "credentials"
        self.credentials.mkdir(parents=True)
        self.paths.pcrs.mkdir()
        (self.paths.pcrs / "7").write_text(PCR7.hex().upper() + "\n", encoding="ascii")
        (root / "dev").mkdir()
        (root / "dev" / "dm-0").touch()
        self.paths.mapping.parent.mkdir()
        self.paths.mapping.symlink_to(root / "dev" / "dm-0")
        (self.paths.sysfs / "block" / "dm-0" / "slaves" / "nvme0n1p2").mkdir(parents=True)
        self.write_policy(POLICY)

    def write_policy(self, policy: bytes) -> None:
        self.paths.policy.write_bytes(policy)
        (self.credentials / POLICY_CREDENTIAL).write_bytes(policy)

    def boot(self) -> bytes:
        found = sorted(self.credentials.iterdir())
        records = measure.records([Credential(path.name, path.read_bytes()) for path in found])
        events = [builders.LogEvent(12, builders.EV_IPL, digest) for digest in records]
        self.paths.event_log.write_bytes(builders.event_log(events))
        pcr12 = measure.replay(records)
        (self.paths.pcrs / "12").write_text(pcr12.hex().upper() + "\n", encoding="ascii")
        return pcr12


@pytest.fixture
def machine(tmp_path: Path) -> Machine:
    return Machine(tmp_path)


@pytest.fixture
def runner(machine: Machine) -> FakeRunner:
    return FakeRunner(machine.paths.pcrs)

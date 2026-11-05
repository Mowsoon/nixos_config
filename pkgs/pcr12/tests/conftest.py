from collections.abc import Sequence
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
OLD_HASH = "aa" * 32
NEW_HASH = "bb" * 32


class FakeRunner:
    def __init__(self) -> None:
        self.tokens: list[dict[str, object]] = [builders.tpm2_token([7], OLD_HASH)]
        self.commands: list[tuple[list[str], bool]] = []
        self.enroll_fails = False
        self.tokens_after_enroll = [builders.tpm2_token([7, 12], NEW_HASH)]

    def run(self, args: Sequence[str], stdin: bytes = b"", *, interactive: bool = False) -> bytes:
        self.commands.append((list(args), interactive))
        if args[0] == "systemd-creds":
            return stdin
        if args[0] == "cryptsetup":
            return builders.luks_metadata(self.tokens)
        if self.enroll_fails:
            raise EnrollError("systemd-cryptenroll failed")
        self.tokens = self.tokens_after_enroll
        return b""

    def enrollments(self) -> list[tuple[list[str], bool]]:
        return [entry for entry in self.commands if entry[0][0] == "systemd-cryptenroll"]


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
def runner() -> FakeRunner:
    return FakeRunner()

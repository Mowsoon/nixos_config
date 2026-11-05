import pytest

from pcr12 import reseal, state
from pcr12.errors import CredentialError, EnrollError, ModelError
from pcr12.reseal import Resealer
from pcr12.state import Enrollment
from tests import builders
from tests.conftest import NEW_HASH, PCR7, FakeRunner, Machine


def _resealed(machine: Machine, runner: FakeRunner, *, ask_key: bool = False) -> bool:
    return Resealer(machine.paths, runner).run(ask_key=ask_key)


def test_check_records_the_reproduced_pcr(machine: Machine) -> None:
    pcr12 = machine.boot()
    reseal.check(machine.paths)
    assert machine.paths.marker.read_text(encoding="ascii").strip() == pcr12.hex()


def test_check_refuses_a_credential_added_after_the_boot(machine: Machine) -> None:
    machine.boot()
    (machine.credentials / "tmpfiles.extra.cred").write_bytes(b"x")
    with pytest.raises(ModelError):
        reseal.check(machine.paths)


def test_check_refuses_a_log_that_does_not_replay(machine: Machine) -> None:
    machine.boot()
    (machine.paths.pcrs / "12").write_text("00" * 32, encoding="ascii")
    with pytest.raises(ModelError):
        reseal.check(machine.paths)


def test_check_refuses_credentials_of_a_boot_entry(machine: Machine) -> None:
    machine.boot()
    drop_in = machine.paths.esp / "EFI" / "Linux" / "nixos.efi.extra.d"
    drop_in.mkdir(parents=True)
    (drop_in / "sysctl.extra.cred").write_bytes(b"x")
    with pytest.raises(ModelError):
        reseal.check(machine.paths)


def test_reseal_seals_the_predicted_pcr_and_records_it(
    machine: Machine, runner: FakeRunner
) -> None:
    pcr12 = machine.boot()
    reseal.check(machine.paths)
    assert _resealed(machine, runner)
    expected = Enrollment(PCR7.hex(), pcr12.hex(), NEW_HASH)
    assert state.load(machine.paths.state) == expected


def test_reseal_unlocks_with_the_current_tpm2_slot(machine: Machine, runner: FakeRunner) -> None:
    machine.boot()
    reseal.check(machine.paths)
    _resealed(machine, runner)
    command, interactive = runner.enrollments()[0]
    assert "--unlock-tpm2-device=auto" in command
    assert not interactive


def test_reseal_does_nothing_when_the_slot_is_current(machine: Machine, runner: FakeRunner) -> None:
    machine.boot()
    reseal.check(machine.paths)
    _resealed(machine, runner)
    assert not _resealed(machine, runner)
    assert len(runner.enrollments()) == 1


def test_reseal_follows_a_new_policy_before_the_reboot(
    machine: Machine, runner: FakeRunner
) -> None:
    machine.boot()
    reseal.check(machine.paths)
    _resealed(machine, runner)
    machine.write_policy(b'{"pcrValues": ["new"]}\n')
    assert _resealed(machine, runner)
    command, _ = runner.enrollments()[1]
    predicted = machine.boot().hex()
    assert f"--tpm2-pcrs=7+12:sha256={predicted}" in command


def test_reseal_follows_a_new_secure_boot_state(machine: Machine, runner: FakeRunner) -> None:
    machine.boot()
    reseal.check(machine.paths)
    _resealed(machine, runner)
    (machine.paths.pcrs / "7").write_text("ff" * 32, encoding="ascii")
    assert _resealed(machine, runner)


def test_reseal_refuses_an_unknown_credential(machine: Machine, runner: FakeRunner) -> None:
    machine.boot()
    reseal.check(machine.paths)
    (machine.credentials / "tmpfiles.extra.cred").write_bytes(b"x")
    with pytest.raises(CredentialError):
        _resealed(machine, runner)
    assert runner.enrollments() == []


def test_reseal_refuses_before_the_check_of_this_boot(machine: Machine, runner: FakeRunner) -> None:
    machine.boot()
    with pytest.raises(ModelError):
        _resealed(machine, runner)


def test_reseal_refuses_a_check_of_another_boot(machine: Machine, runner: FakeRunner) -> None:
    machine.boot()
    reseal.check(machine.paths)
    machine.write_policy(b'{"pcrValues": ["new"]}\n')
    machine.boot()
    with pytest.raises(ModelError):
        _resealed(machine, runner)


def test_reseal_with_a_key_lets_the_enrollment_prompt(machine: Machine, runner: FakeRunner) -> None:
    machine.boot()
    reseal.check(machine.paths)
    _resealed(machine, runner, ask_key=True)
    command, interactive = runner.enrollments()[0]
    assert "--unlock-tpm2-device=auto" not in command
    assert interactive


def test_reseal_points_to_the_recovery_key_when_the_tpm2_refuses(
    machine: Machine, runner: FakeRunner
) -> None:
    machine.boot()
    reseal.check(machine.paths)
    runner.enroll_fails = True
    with pytest.raises(EnrollError, match="--ask-key"):
        _resealed(machine, runner)
    assert state.load(machine.paths.state) is None


def test_reseal_leaves_a_header_without_tpm2_slot_alone(
    machine: Machine, runner: FakeRunner
) -> None:
    machine.boot()
    reseal.check(machine.paths)
    runner.tokens = []
    assert not _resealed(machine, runner)
    assert runner.enrollments() == []


def test_reseal_with_a_key_enrolls_the_first_tpm2_slot(
    machine: Machine, runner: FakeRunner
) -> None:
    machine.boot()
    reseal.check(machine.paths)
    runner.tokens = []
    assert _resealed(machine, runner, ask_key=True)


def test_reseal_refuses_a_header_left_without_a_sealed_slot(
    machine: Machine, runner: FakeRunner
) -> None:
    machine.boot()
    reseal.check(machine.paths)
    runner.tokens_after_enroll = [builders.tpm2_token([7], "cc"), builders.tpm2_token([7], "dd")]
    with pytest.raises(EnrollError):
        _resealed(machine, runner)

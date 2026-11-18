import json
from dataclasses import asdict

import pytest

from pcr12 import measure, reseal, state
from pcr12.errors import CredentialError, EnrollError, ModelError
from pcr12.measure import Credential
from pcr12.reseal import Resealer
from tests.conftest import PCR7, FakeRunner, Machine


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


def _booted(machine: Machine) -> bytes:
    pcr12 = machine.boot()
    reseal.check(machine.paths)
    return pcr12


def _predicted(machine: Machine) -> bytes:
    found = sorted(machine.credentials.iterdir())
    credentials = [Credential(path.name, path.read_bytes()) for path in found]
    return measure.replay(measure.records(credentials))


def _write_new_policy(machine: Machine, version: int) -> None:
    machine.write_policy(f'{{"pcrValues": ["{version}"]}}\n'.encode("ascii"))


def test_reseal_seals_the_predicted_pcr_and_records_it(
    machine: Machine, runner: FakeRunner
) -> None:
    pcr12 = _booted(machine)
    assert _resealed(machine, runner)
    [enrollment] = state.load(machine.paths.state)
    assert (enrollment.pcr7, enrollment.pcr12) == (PCR7.hex(), pcr12.hex())
    assert runner.sealed_pcr12() == [pcr12.hex()]


def test_reseal_unlocks_with_the_current_tpm2_slot(machine: Machine, runner: FakeRunner) -> None:
    _booted(machine)
    _resealed(machine, runner)
    command, interactive = runner.enrollments()[0]
    assert "--unlock-tpm2-device=auto" in command
    assert not interactive


def test_reseal_does_nothing_when_the_slot_is_current(machine: Machine, runner: FakeRunner) -> None:
    _booted(machine)
    _resealed(machine, runner)
    assert not _resealed(machine, runner)
    assert len(runner.enrollments()) == 1


def test_reseal_keeps_the_slot_of_this_boot_next_to_the_slot_of_the_next_boot(
    machine: Machine, runner: FakeRunner
) -> None:
    booted = _booted(machine)
    _resealed(machine, runner)
    _write_new_policy(machine, 1)
    assert _resealed(machine, runner)
    command, _ = runner.enrollments()[1]
    assert not [arg for arg in command if arg.startswith("--wipe-slot")]
    assert runner.sealed_pcr12() == [booted.hex(), _predicted(machine).hex()]


def test_reseal_follows_every_new_policy_before_the_reboot(
    machine: Machine, runner: FakeRunner
) -> None:
    booted = _booted(machine)
    _resealed(machine, runner)
    for version in range(1, 4):
        _write_new_policy(machine, version)
        assert _resealed(machine, runner)
    assert runner.sealed_pcr12() == [booted.hex(), _predicted(machine).hex()]
    assert [entry.pcr12 for entry in state.load(machine.paths.state)] == runner.sealed_pcr12()


def test_reseal_after_the_reboot_removes_the_slot_of_the_previous_boot(
    machine: Machine, runner: FakeRunner
) -> None:
    _booted(machine)
    _resealed(machine, runner)
    _write_new_policy(machine, 1)
    _resealed(machine, runner)
    rebooted = machine.boot()
    assert runner.unlocks()
    assert not _resealed(machine, runner)
    assert runner.sealed_pcr12() == [rebooted.hex()]
    assert [entry.pcr12 for entry in state.load(machine.paths.state)] == [rebooted.hex()]
    wipe, _ = runner.commands[-1]
    assert "--unlock-tpm2-device=auto" not in wipe


def test_reseal_records_the_next_boot_slot_for_older_generations(
    machine: Machine, runner: FakeRunner
) -> None:
    _booted(machine)
    _resealed(machine, runner)
    _write_new_policy(machine, 1)
    _resealed(machine, runner)
    raw = json.loads(machine.paths.state.read_text(encoding="utf-8"))
    assert raw["pcr12"] == _predicted(machine).hex()
    machine.boot()
    _resealed(machine, runner)
    raw = json.loads(machine.paths.state.read_text(encoding="utf-8"))
    assert raw["pcr12"] == _predicted(machine).hex()


def test_reseal_asks_for_the_key_after_a_new_secure_boot_state(
    machine: Machine, runner: FakeRunner
) -> None:
    _booted(machine)
    _resealed(machine, runner)
    (machine.paths.pcrs / "7").write_text("ff" * 32, encoding="ascii")
    with pytest.raises(EnrollError, match="--ask-key"):
        _resealed(machine, runner)
    assert _resealed(machine, runner, ask_key=True)
    assert runner.unlocks()
    assert len(runner.sealed_pcr12()) == 1


def test_reseal_with_a_key_replaces_the_slot_of_this_boot_too(
    machine: Machine, runner: FakeRunner
) -> None:
    _booted(machine)
    _resealed(machine, runner)
    _write_new_policy(machine, 1)
    assert _resealed(machine, runner, ask_key=True)
    assert runner.sealed_pcr12() == [_predicted(machine).hex()]
    [enrollment] = state.load(machine.paths.state)
    assert enrollment.pcr12 == _predicted(machine).hex()


def test_reseal_refuses_an_unknown_credential(machine: Machine, runner: FakeRunner) -> None:
    _booted(machine)
    (machine.credentials / "tmpfiles.extra.cred").write_bytes(b"x")
    with pytest.raises(CredentialError):
        _resealed(machine, runner)
    assert runner.enrollments() == []


def test_reseal_refuses_before_the_check_of_this_boot(machine: Machine, runner: FakeRunner) -> None:
    machine.boot()
    with pytest.raises(ModelError):
        _resealed(machine, runner)


def test_reseal_refuses_a_check_of_another_boot(machine: Machine, runner: FakeRunner) -> None:
    _booted(machine)
    _write_new_policy(machine, 1)
    machine.boot()
    with pytest.raises(ModelError):
        _resealed(machine, runner)


def test_reseal_with_a_key_lets_the_enrollment_prompt(machine: Machine, runner: FakeRunner) -> None:
    _booted(machine)
    _resealed(machine, runner, ask_key=True)
    command, interactive = runner.enrollments()[0]
    assert "--unlock-tpm2-device=auto" not in command
    assert interactive


def test_reseal_points_to_the_recovery_key_when_the_tpm2_refuses(
    machine: Machine, runner: FakeRunner
) -> None:
    _booted(machine)
    runner.enroll_fails = True
    with pytest.raises(EnrollError, match="--ask-key"):
        _resealed(machine, runner)
    assert state.load(machine.paths.state) == []


def test_reseal_leaves_a_header_without_tpm2_slot_alone(
    machine: Machine, runner: FakeRunner
) -> None:
    _booted(machine)
    runner.slots = {}
    assert not _resealed(machine, runner)
    assert runner.enrollments() == []


def test_reseal_with_a_key_enrolls_the_first_tpm2_slot(
    machine: Machine, runner: FakeRunner
) -> None:
    _booted(machine)
    runner.slots = {}
    assert _resealed(machine, runner, ask_key=True)
    assert len(runner.sealed_pcr12()) == 1


def test_reseal_reads_the_state_of_a_single_slot(machine: Machine, runner: FakeRunner) -> None:
    booted = _booted(machine)
    _resealed(machine, runner)
    [enrollment] = state.load(machine.paths.state)
    machine.paths.state.write_text(json.dumps(asdict(enrollment)), encoding="utf-8")
    _write_new_policy(machine, 1)
    assert _resealed(machine, runner)
    assert runner.sealed_pcr12()[0] == booted.hex()


def test_reseal_refuses_a_header_left_without_a_new_sealed_slot(
    machine: Machine, runner: FakeRunner
) -> None:
    _booted(machine)
    runner.enroll_adds_no_slot = True
    with pytest.raises(EnrollError):
        _resealed(machine, runner)

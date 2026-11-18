import logging
from dataclasses import dataclass
from pathlib import Path

from pcr12 import allowlist, eventlog, luks, measure, state
from pcr12.errors import EnrollError, InputError, ModelError
from pcr12.esp import Esp
from pcr12.luks import Token
from pcr12.state import Enrollment
from pcr12.system import CredsDecryptor, Runner

CREDENTIALS_PCR = 12
SECURE_BOOT_PCR = 7

logger = logging.getLogger("pcr12")


@dataclass(frozen=True, slots=True)
class Paths:
    event_log: Path
    esp: Path
    policy: Path
    state: Path
    marker: Path
    pcrs: Path
    mapping: Path
    sysfs: Path


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as err:
        raise InputError(f"read {path}") from err


def _pcr(paths: Paths, index: int) -> bytes:
    return bytes.fromhex(_read(paths.pcrs / str(index)).decode("ascii").strip())


def check(paths: Paths) -> bytes:
    esp = Esp(paths.esp)
    entry_credentials = esp.entry_credentials()
    if entry_credentials:
        raise ModelError(f"boot entry drop-ins hold credentials: {entry_credentials}")
    logged = eventlog.pcr_digests(eventlog.parse(_read(paths.event_log)), CREDENTIALS_PCR)
    if logged != measure.records(esp.global_credentials()):
        raise ModelError("the PCR 12 records of the event log differ from the ESP credentials")
    current = _pcr(paths, CREDENTIALS_PCR)
    if measure.replay(logged) != current:
        raise ModelError("the event log does not replay to the current PCR 12")
    paths.marker.parent.mkdir(parents=True, exist_ok=True)
    paths.marker.write_text(current.hex() + "\n", encoding="ascii")
    logger.info("PCR 12 %s is reproduced from the ESP credentials", current.hex())
    return current


@dataclass(frozen=True, slots=True)
class Slot:
    token: Token
    enrollment: Enrollment | None

    def seals(self, pcr7: bytes, pcr12: bytes) -> bool:
        return self.token.sealed and self.enrollment == Enrollment(
            pcr7.hex(), pcr12.hex(), self.token.policy_hash
        )


def _keyslots(slots: list[Slot]) -> list[int]:
    return sorted(keyslot for slot in slots for keyslot in slot.token.keyslots)


def _enrollments(slots: list[Slot]) -> list[Enrollment]:
    return [slot.enrollment for slot in slots if slot.enrollment is not None]


class Resealer:
    def __init__(self, paths: Paths, runner: Runner) -> None:
        self._paths = paths
        self._runner = runner

    def run(self, *, ask_key: bool) -> bool:
        paths = self._paths
        esp = Esp(paths.esp)
        credentials = esp.global_credentials()
        allowlist.verify(
            credentials, esp.entry_credentials(), _read(paths.policy), CredsDecryptor(self._runner)
        )
        predicted = measure.replay(measure.records(credentials))
        pcr7 = _pcr(paths, SECURE_BOOT_PCR)
        device = luks.backing_device(paths.mapping, paths.sysfs)
        slots = self._slots(device)
        if not slots and not ask_key:
            logger.info("no TPM2 slot is enrolled, nothing to reseal")
            return False
        current = [slot for slot in slots if slot.seals(pcr7, _pcr(paths, CREDENTIALS_PCR))]
        target = [slot for slot in slots if slot.seals(pcr7, predicted)]
        if target:
            self._prune(device, slots, current + target)
            logger.info("the TPM2 slot is already sealed to PCR 12 %s", predicted.hex())
            return False
        self._require_verified_model()
        kept = [] if ask_key else current
        stale = [slot for slot in slots if slot not in kept]
        self._enroll(device, predicted, _keyslots(stale), ask_key=ask_key)
        token = self._new_token(device, slots)
        sealed = Enrollment(pcr7.hex(), predicted.hex(), token.policy_hash)
        state.save(paths.state, [*_enrollments(kept), sealed])
        logger.info("sealed a TPM2 slot to PCR 7 and PCR 12 %s", predicted.hex())
        return True

    def _slots(self, device: Path) -> list[Slot]:
        known = {enrollment.policy_hash: enrollment for enrollment in state.load(self._paths.state)}
        tokens = luks.tpm2_tokens(self._runner.run(luks.dump_command(device)))
        return [Slot(token, known.get(token.policy_hash)) for token in tokens]

    def _prune(self, device: Path, slots: list[Slot], kept: list[Slot]) -> None:
        stale = [slot for slot in slots if slot not in kept]
        if not stale:
            return
        self._runner.run(luks.wipe_command(device, _keyslots(stale)))
        state.save(self._paths.state, _enrollments(list(dict.fromkeys(kept))))
        logger.info("removed the TPM2 slots %s left from a previous boot", _keyslots(stale))

    def _require_verified_model(self) -> None:
        try:
            verified = self._paths.marker.read_text(encoding="ascii").strip()
        except OSError as err:
            raise ModelError("the ESP credentials were not checked against this boot") from err
        if verified != _pcr(self._paths, CREDENTIALS_PCR).hex():
            raise ModelError("the check of this boot does not match the current PCR 12")

    def _enroll(self, device: Path, pcr12: bytes, wipe: list[int], *, ask_key: bool) -> None:
        command = luks.enroll_command(device, self._paths.policy, pcr12, wipe=wipe, ask_key=ask_key)
        try:
            self._runner.run(command, interactive=ask_key)
        except EnrollError as err:
            if ask_key:
                raise
            raise EnrollError(
                "no TPM2 slot unlocks the container in this boot: run 'pcr12 reseal --ask-key'"
                " and type the recovery key"
            ) from err

    def _new_token(self, device: Path, before: list[Slot]) -> Token:
        previous = set(_keyslots(before))
        new = [
            slot.token
            for slot in self._slots(device)
            if slot.token.sealed and not previous.intersection(slot.token.keyslots)
        ]
        if len(new) != 1:
            raise EnrollError(
                "the LUKS2 header does not hold one new TPM2 slot sealed to PCR 7 and 12"
            )
        return new[0]

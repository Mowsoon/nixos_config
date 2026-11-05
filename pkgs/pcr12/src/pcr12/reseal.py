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


def _up_to_date(
    enrollment: Enrollment | None, tokens: list[Token], pcr7: bytes, pcr12: bytes
) -> bool:
    if enrollment is None or len(tokens) != 1 or not tokens[0].sealed:
        return False
    return enrollment == Enrollment(pcr7.hex(), pcr12.hex(), tokens[0].policy_hash)


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
        pcr12 = measure.replay(measure.records(credentials))
        pcr7 = _pcr(paths, SECURE_BOOT_PCR)
        device = luks.backing_device(paths.mapping, paths.sysfs)
        tokens = self._tokens(device)
        if not tokens and not ask_key:
            logger.info("no TPM2 slot is enrolled, nothing to reseal")
            return False
        if _up_to_date(state.load(paths.state), tokens, pcr7, pcr12):
            logger.info("the TPM2 slot is already sealed to PCR 12 %s", pcr12.hex())
            return False
        self._require_verified_model()
        self._enroll(device, pcr12, ask_key=ask_key)
        token = self._sealed_token(device)
        state.save(paths.state, Enrollment(pcr7.hex(), pcr12.hex(), token.policy_hash))
        logger.info("sealed the TPM2 slot to PCR 7 and PCR 12 %s", pcr12.hex())
        return True

    def _tokens(self, device: Path) -> list[Token]:
        return luks.tpm2_tokens(self._runner.run(luks.dump_command(device)))

    def _require_verified_model(self) -> None:
        try:
            verified = self._paths.marker.read_text(encoding="ascii").strip()
        except OSError as err:
            raise ModelError("the ESP credentials were not checked against this boot") from err
        if verified != _pcr(self._paths, CREDENTIALS_PCR).hex():
            raise ModelError("the check of this boot does not match the current PCR 12")

    def _enroll(self, device: Path, pcr12: bytes, *, ask_key: bool) -> None:
        command = luks.enroll_command(device, self._paths.policy, pcr12, ask_key=ask_key)
        try:
            self._runner.run(command, interactive=ask_key)
        except EnrollError as err:
            if ask_key:
                raise
            raise EnrollError(
                "the TPM2 slot no longer unlocks the container: run 'pcr12 reseal --ask-key'"
                " and type the recovery key"
            ) from err

    def _sealed_token(self, device: Path) -> Token:
        tokens = self._tokens(device)
        if len(tokens) != 1 or not tokens[0].sealed:
            raise EnrollError("the LUKS2 header does not hold one TPM2 slot sealed to PCR 7 and 12")
        return tokens[0]

import subprocess
from collections.abc import Sequence
from typing import Protocol

from pcr12.errors import EnrollError
from pcr12.measure import Credential

COMMAND_TIMEOUT = 300
CREDENTIAL_SUFFIX = ".cred"


class Runner(Protocol):
    def run(
        self, args: Sequence[str], stdin: bytes = b"", *, interactive: bool = False
    ) -> bytes: ...


class SubprocessRunner:
    def run(self, args: Sequence[str], stdin: bytes = b"", *, interactive: bool = False) -> bytes:
        try:
            if interactive:
                subprocess.run(list(args), check=True, timeout=COMMAND_TIMEOUT)  # noqa: S603
                return b""
            result = subprocess.run(  # noqa: S603
                list(args), input=stdin, capture_output=True, check=True, timeout=COMMAND_TIMEOUT
            )
        except subprocess.CalledProcessError as err:
            message = err.stderr.decode("utf-8", "replace").strip() if err.stderr else ""
            raise EnrollError(f"{args[0]} failed: {message}") from err
        except (OSError, subprocess.TimeoutExpired) as err:
            raise EnrollError(f"{args[0]} did not complete") from err
        return result.stdout


class CredsDecryptor:
    def __init__(self, runner: Runner) -> None:
        self._runner = runner

    def decrypt(self, credential: Credential) -> bytes:
        name = credential.name.removesuffix(CREDENTIAL_SUFFIX)
        command = ["systemd-creds", "decrypt", "--allow-null", f"--name={name}", "-", "-"]
        return self._runner.run(command, credential.data)

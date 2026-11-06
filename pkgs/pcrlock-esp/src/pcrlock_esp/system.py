import subprocess
from collections.abc import Sequence

from pcrlock_esp.errors import CommandError

COMMAND_TIMEOUT = 60


class SubprocessRunner:
    def run(self, args: Sequence[str]) -> None:
        try:
            subprocess.run(  # noqa: S603
                list(args), capture_output=True, check=True, timeout=COMMAND_TIMEOUT
            )
        except subprocess.CalledProcessError as err:
            message = err.stderr.decode("utf-8", "replace").strip() if err.stderr else ""
            raise CommandError(f"{args[0]} failed: {message}") from err
        except (OSError, subprocess.TimeoutExpired) as err:
            raise CommandError(f"{args[0]} could not run") from err

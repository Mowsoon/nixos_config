from pathlib import Path

from pcr12.errors import InputError
from pcr12.measure import Credential

GLOBAL_DIRECTORY = Path("loader/credentials")
STUB_DIRECTORY = Path("EFI/Linux")
DROP_IN_PATTERN = "*.extra.d"
SUFFIX = ".cred"


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as err:
        raise InputError(f"read {path}") from err


class Esp:
    def __init__(self, root: Path) -> None:
        self._root = root

    def global_credentials(self) -> list[Credential]:
        directory = self._root / GLOBAL_DIRECTORY
        if not directory.is_dir():
            return []
        return [
            Credential(path.name, _read(path))
            for path in sorted(directory.iterdir())
            if path.is_file() and path.name.endswith(SUFFIX)
        ]

    def entry_credentials(self) -> list[Path]:
        stubs = self._root / STUB_DIRECTORY
        if not stubs.is_dir():
            return []
        return sorted(
            path
            for drop_in in stubs.glob(DROP_IN_PATTERN)
            for path in drop_in.glob(f"*{SUFFIX}")
            if path.is_file()
        )

from dataclasses import dataclass
from pathlib import Path

from pcrlock_esp import pe
from pcrlock_esp.errors import InputError
from pcrlock_esp.records import Record, generation_records
from pcrlock_esp.selection import newest

STUB_DIRECTORY = Path("EFI/Linux")
LOADER_CONF = Path("loader/loader.conf")
STUB_SUFFIX = ".efi"


@dataclass(frozen=True, slots=True)
class Esp:
    root: Path

    def stubs(self) -> list[Path]:
        stubs = sorted(
            path
            for path in (self.root / STUB_DIRECTORY).glob(f"*{STUB_SUFFIX}")
            if not path.name.startswith(".")
        )
        if not stubs:
            raise InputError(f"no generation stub under {self.root / STUB_DIRECTORY}")
        return stubs

    def generations(self, booted: str | None) -> dict[str, list[Record]]:
        return {
            stub.stem: generation_records(pe.sections(_read(stub)))
            for stub in newest(self.stubs(), booted)
        }

    def loader_conf(self) -> bytes:
        return _read(self.root / LOADER_CONF)


def whole_disk(partition: Path, sysfs: Path) -> Path:
    name = partition.resolve().name
    entry = sysfs / "class" / "block" / name
    if not (entry / "partition").is_file():
        raise InputError(f"{partition} is not a partition")
    return Path("/dev") / entry.resolve().parent.name


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as err:
        raise InputError(f"read {path}") from err

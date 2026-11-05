import stat
from pathlib import Path

import pytest

from pcr0_predict import pcrlock
from pcr0_predict.errors import PcrlockError
from pcr0_predict.pcrlock import Record

GENERATED = [Record(0, b"\x01" * 32), Record(0, b"\x02" * 32), Record(2, b"\x03" * 32)]


def test_variant_replaces_pcr0_records_and_keeps_the_others() -> None:
    assert pcrlock.variant(GENERATED, [b"\x0a" * 32, b"\x0b" * 32]) == [
        Record(0, b"\x0a" * 32),
        Record(0, b"\x0b" * 32),
        Record(2, b"\x03" * 32),
    ]


def test_variant_raises_when_record_count_differs() -> None:
    with pytest.raises(PcrlockError, match="number of records"):
        pcrlock.variant(GENERATED, [b"\x0a" * 32])


def test_render_and_parse_round_trip() -> None:
    assert pcrlock.parse(pcrlock.render(GENERATED)) == GENERATED


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("{", "not JSON"),
        ('{"other": []}', "no record list"),
        ('{"records": [1]}', "not an object"),
        ('{"records": [{"pcr": 0}]}', "no PCR or no digest list"),
        ('{"records": [{"pcr": 0, "digests": [{"hashAlg": "sha1", "digest": "00"}]}]}', "SHA-256"),
        ('{"records": [{"pcr": 0, "digests": [{"hashAlg": "sha256", "digest": "zz"}]}]}', "hex"),
    ],
)
def test_parse_raises_on_malformed_file(text: str, message: str) -> None:
    with pytest.raises(PcrlockError, match=message):
        pcrlock.parse(text)


def test_write_creates_a_world_readable_file(tmp_path: Path) -> None:
    target = tmp_path / "predicted.pcrlock"
    pcrlock.write(target, "content\n")
    assert (target.read_text(encoding="utf-8"), stat.S_IMODE(target.stat().st_mode)) == (
        "content\n",
        0o644,
    )


def test_write_raises_when_the_directory_is_missing(tmp_path: Path) -> None:
    with pytest.raises(PcrlockError, match="create a file"):
        pcrlock.write(tmp_path / "missing" / "predicted.pcrlock", "content\n")


def test_read_raises_when_the_file_is_missing(tmp_path: Path) -> None:
    with pytest.raises(PcrlockError, match="read"):
        pcrlock.read(tmp_path / "generated.pcrlock")

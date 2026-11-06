import json
from pathlib import Path

import pytest

from pcrlock_esp.components import ComponentWriter, render
from pcrlock_esp.errors import WriteError
from pcrlock_esp.records import Record

RECORDS = [Record(5, bytes(range(32)))]


def test_render_writes_the_pcrlock_record_format() -> None:
    assert json.loads(render(RECORDS)) == {
        "records": [
            {"pcr": 5, "digests": [{"hashAlg": "sha256", "digest": bytes(range(32)).hex()}]}
        ]
    }


def test_write_creates_the_component_file(tmp_path: Path) -> None:
    ComponentWriter(tmp_path).write("600-boot-loader-config", RECORDS)
    assert (tmp_path / "600-boot-loader-config.pcrlock").read_text(encoding="utf-8") == render(
        RECORDS
    )


def test_write_variants_writes_one_file_per_variant(tmp_path: Path) -> None:
    ComponentWriter(tmp_path).write_variants("650-gen", {"a": RECORDS, "b": RECORDS})
    assert sorted(path.name for path in (tmp_path / "650-gen.pcrlock.d").iterdir()) == [
        "a.pcrlock",
        "b.pcrlock",
    ]


def test_write_variants_removes_the_variants_of_removed_generations(tmp_path: Path) -> None:
    writer = ComponentWriter(tmp_path)
    writer.write_variants("650-gen", {"a": RECORDS, "b": RECORDS})
    writer.write_variants("650-gen", {"b": RECORDS})
    assert [path.name for path in (tmp_path / "650-gen.pcrlock.d").iterdir()] == ["b.pcrlock"]


def test_write_raises_when_the_directory_cannot_be_created(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("", encoding="utf-8")
    with pytest.raises(WriteError):
        ComponentWriter(blocker).write("600-boot-loader-config", RECORDS)

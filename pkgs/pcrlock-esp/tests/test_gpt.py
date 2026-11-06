import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from pcrlock_esp.errors import InputError
from pcrlock_esp.gpt import GptMeasurement, parse_gpt_component
from tests import builders

DIGEST = "ab" * 32


class WritingRunner:
    def __init__(self, content: str | None) -> None:
        self.content = content
        self.commands: list[list[str]] = []

    def run(self, args: Sequence[str]) -> None:
        self.commands.append(list(args))
        output = next(arg for arg in args if arg.startswith("--pcrlock="))
        if self.content is not None:
            Path(output.removeprefix("--pcrlock=")).write_text(self.content, encoding="utf-8")


def test_digest_runs_lock_gpt_on_the_disk_and_reads_its_sha256_record() -> None:
    runner = WritingRunner(builders.gpt_component(DIGEST))
    digest = GptMeasurement(Path("/pcrlock"), runner).digest(Path("/dev/nvme1n1"))
    assert digest == bytes.fromhex(DIGEST)
    assert runner.commands[0][:3] == ["/pcrlock", "lock-gpt", "/dev/nvme1n1"]


def test_digest_raises_when_lock_gpt_writes_nothing() -> None:
    with pytest.raises(InputError):
        GptMeasurement(Path("/pcrlock"), WritingRunner(None)).digest(Path("/dev/nvme1n1"))


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps({"records": []}),
        builders.gpt_component(DIGEST, pcr=4),
        json.dumps({"records": [{"pcr": 5, "digests": [{"hashAlg": "sha1", "digest": "00"}]}]}),
        builders.gpt_component("zz" * 32),
        builders.gpt_component("ab" * 20),
    ],
)
def test_parse_gpt_component_raises_on_an_unexpected_component(content: str) -> None:
    with pytest.raises(InputError):
        parse_gpt_component(content)

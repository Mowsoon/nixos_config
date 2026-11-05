import hashlib

import pytest

from pcr0_predict import eventlog
from pcr0_predict.errors import EventLogError
from tests import builders
from tests.builders import LogEvent


def test_parse_reads_digests_and_data(current_log: bytes) -> None:
    events = eventlog.parse(current_log)
    assert (events[0].pcr, events[0].sha256) == (0, hashlib.sha256(builders.CRTM).digest())


def test_firmware_code_keeps_pcr0_records_before_the_separator(current_log: bytes) -> None:
    records = eventlog.firmware_code(eventlog.parse(current_log))
    assert [record.event_type for record in records] == [0x8, 0x8000000A]


def test_firmware_code_raises_without_separator() -> None:
    log = builders.event_log([LogEvent(0, 0x8, builders.CRTM)])
    with pytest.raises(EventLogError, match="no separator"):
        eventlog.firmware_code(eventlog.parse(log))


def test_parse_raises_without_sha256_bank() -> None:
    log = builders.event_log([], algorithms=(0x0004,))
    with pytest.raises(EventLogError, match="no SHA-256 bank"):
        eventlog.parse(log)


def test_parse_raises_on_truncated_log(current_log: bytes) -> None:
    with pytest.raises(EventLogError, match="truncated"):
        eventlog.parse(current_log[:-3])


def test_parse_raises_when_log_is_not_crypto_agile() -> None:
    with pytest.raises(EventLogError, match="Spec ID"):
        eventlog.parse(b"\x00" * 28 + b"\x04\x00\x00\x00" + b"junk")


def test_blob_reads_description_base_and_length() -> None:
    event = eventlog.Event(0, 0x8000000A, b"", builders.blob2(0x1000, 0x2000))
    assert eventlog.blob(event) == eventlog.Blob(b"FV_MAIN", 0x1000, 0x2000)


@pytest.mark.parametrize(
    ("event_type", "data", "message"),
    [
        (0x8, builders.CRTM, "not a firmware blob"),
        (0x8000000A, b"\x07FV_", "truncated"),
        (0x80000008, b"\x00" * 8, "truncated"),
    ],
)
def test_blob_raises_on_unusable_event(event_type: int, data: bytes, message: str) -> None:
    with pytest.raises(EventLogError, match=message):
        eventlog.blob(eventlog.Event(0, event_type, b"", data))

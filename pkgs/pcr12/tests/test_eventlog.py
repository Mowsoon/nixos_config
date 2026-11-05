import struct

import pytest

from pcr12 import eventlog
from pcr12.errors import EventLogError
from tests import builders

FIRST = bytes([1]) * 32
SECOND = bytes([2]) * 32


def test_pcr_digests_keep_the_order_of_one_pcr() -> None:
    log = builders.event_log(
        [
            builders.LogEvent(12, builders.EV_IPL, FIRST, b"credentials"),
            builders.LogEvent(9, builders.EV_IPL, SECOND),
            builders.LogEvent(12, builders.EV_IPL, SECOND),
        ]
    )
    assert eventlog.pcr_digests(eventlog.parse(log), 12) == [FIRST, SECOND]


def test_pcr_digests_skip_no_action_events() -> None:
    log = builders.event_log([builders.LogEvent(12, builders.EV_NO_ACTION, FIRST)])
    assert eventlog.pcr_digests(eventlog.parse(log), 12) == []


def test_parse_refuses_a_truncated_log() -> None:
    log = builders.event_log([builders.LogEvent(12, builders.EV_IPL, FIRST)])
    with pytest.raises(EventLogError):
        eventlog.parse(log[:-10])


def test_parse_refuses_a_log_without_spec_id_event() -> None:
    log = struct.pack("<II", 0, 3) + b"\x00" * 20 + struct.pack("<I", 4) + b"none"
    with pytest.raises(EventLogError):
        eventlog.parse(log)

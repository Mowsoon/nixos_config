from dataclasses import dataclass

from pcr12.errors import EventLogError

SHA256 = 0x000B
SPEC_ID_SIGNATURE = b"Spec ID Event03\x00"
SPEC_ID_FIELDS = 8
LEGACY_HEADER = 4 + 4 + 20
NO_ACTION = 0x3


@dataclass(frozen=True, slots=True)
class Event:
    pcr: int
    event_type: int
    sha256: bytes


class _Reader:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0

    @property
    def done(self) -> bool:
        return self._offset >= len(self._data)

    def take(self, size: int) -> bytes:
        end = self._offset + size
        if end > len(self._data):
            raise EventLogError(f"event log truncated at offset {self._offset:#x}")
        chunk = self._data[self._offset : end]
        self._offset = end
        return chunk

    def u16(self) -> int:
        return int.from_bytes(self.take(2), "little")

    def u32(self) -> int:
        return int.from_bytes(self.take(4), "little")


def _digest_sizes(spec: bytes) -> dict[int, int]:
    if not spec.startswith(SPEC_ID_SIGNATURE):
        raise EventLogError("event log does not start with a crypto agile Spec ID event")
    reader = _Reader(spec[len(SPEC_ID_SIGNATURE) + SPEC_ID_FIELDS :])
    sizes: dict[int, int] = {}
    for _ in range(reader.u32()):
        algorithm = reader.u16()
        sizes[algorithm] = reader.u16()
    if SHA256 not in sizes:
        raise EventLogError("event log has no SHA-256 bank")
    return sizes


def _event(reader: _Reader, sizes: dict[int, int]) -> Event:
    pcr = reader.u32()
    event_type = reader.u32()
    digests: dict[int, bytes] = {}
    for _ in range(reader.u32()):
        algorithm = reader.u16()
        if algorithm not in sizes:
            raise EventLogError(f"event log uses undeclared digest algorithm {algorithm:#x}")
        digests[algorithm] = reader.take(sizes[algorithm])
    reader.take(reader.u32())
    if SHA256 not in digests:
        raise EventLogError(f"event of type {event_type:#x} on PCR {pcr} has no SHA-256 digest")
    return Event(pcr, event_type, digests[SHA256])


def parse(data: bytes) -> list[Event]:
    reader = _Reader(data)
    reader.take(LEGACY_HEADER)
    sizes = _digest_sizes(reader.take(reader.u32()))
    events: list[Event] = []
    while not reader.done:
        events.append(_event(reader, sizes))
    return events


def pcr_digests(events: list[Event], pcr: int) -> list[bytes]:
    return [event.sha256 for event in events if event.pcr == pcr and event.event_type != NO_ACTION]

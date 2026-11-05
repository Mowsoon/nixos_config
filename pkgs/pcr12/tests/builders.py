import json
import struct
from collections.abc import Sequence
from dataclasses import dataclass

SHA256 = 0x000B
EV_IPL = 0xD
EV_NO_ACTION = 0x3


@dataclass(frozen=True, slots=True)
class LogEvent:
    pcr: int
    event_type: int
    digest: bytes
    data: bytes = b""


def event_log(events: Sequence[LogEvent]) -> bytes:
    spec = b"Spec ID Event03\x00" + b"\x00" * 4 + bytes([0, 2, 0, 2])
    spec += struct.pack("<I", 1) + struct.pack("<HH", SHA256, 32)
    log = struct.pack("<II", 0, EV_NO_ACTION) + b"\x00" * 20 + struct.pack("<I", len(spec)) + spec
    for event in events:
        log += struct.pack("<IIIH", event.pcr, event.event_type, 1, SHA256) + event.digest
        log += struct.pack("<I", len(event.data)) + event.data
    return log


def luks_metadata(tokens: Sequence[dict[str, object]]) -> bytes:
    table = {str(index): token for index, token in enumerate(tokens)}
    return json.dumps({"keyslots": {}, "tokens": table}).encode("utf-8")


def tpm2_token(pcrs: Sequence[int], policy_hash: str, *, pcrlock: bool = True) -> dict[str, object]:
    return {
        "type": "systemd-tpm2",
        "tpm2-pcrs": list(pcrs),
        "tpm2_pcrlock": pcrlock,
        "tpm2-policy-hash": policy_hash,
    }

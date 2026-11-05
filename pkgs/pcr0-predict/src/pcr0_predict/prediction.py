import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from pcr0_predict import eventlog, firmware
from pcr0_predict.errors import CalibrationError
from pcr0_predict.eventlog import Event, EventType

STORE_PREFIX = re.escape(b"\xc7\x44\x24") + b"."
STORE_GAP = b".{0,60}?"


@dataclass(frozen=True, slots=True)
class Calibration:
    crtm_data: bytes
    crtm_modules: frozenset[UUID]
    volume_name: UUID


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def stores_constant(code: bytes, constant: bytes) -> bool:
    if not constant or len(constant) % 4:
        return False
    words = [constant[index : index + 4] for index in range(0, len(constant), 4)]
    pattern = STORE_GAP.join(STORE_PREFIX + re.escape(word) for word in words)
    return re.search(pattern, code, re.DOTALL) is not None


def _modules_storing(image: bytes, constant: bytes) -> set[UUID]:
    found: set[UUID] = set()
    for volume in firmware.volumes(image):
        for module in firmware.modules(volume.data):
            if any(stores_constant(code, constant) for code in module.code):
                found.add(module.guid)
    return found


def _shape(records: Sequence[Event]) -> tuple[Event, Event]:
    types = [record.event_type for record in records]
    blobs = (EventType.PLATFORM_FIRMWARE_BLOB, EventType.PLATFORM_FIRMWARE_BLOB2)
    if len(records) != 2 or types[0] != EventType.S_CRTM_VERSION or types[1] not in blobs:
        raise CalibrationError(
            "PCR 0 does not hold exactly an S-CRTM version and one firmware volume: "
            + ", ".join(f"{event_type:#x}" for event_type in types)
        )
    return records[0], records[1]


def _calibrated_volume(image: bytes, event: Event) -> UUID:
    blob = eventlog.blob(event)
    volume = firmware.volume_at(image, blob.base)
    if volume is None or len(volume.data) != blob.length:
        raise CalibrationError(f"no firmware volume of {blob.length:#x} bytes at {blob.base:#x}")
    if _sha256(volume.data) != event.sha256:
        raise CalibrationError(
            "the measured firmware volume differs: the file is not the running firmware"
        )
    if volume.name is None:
        raise CalibrationError(f"the measured firmware volume at {blob.base:#x} has no name")
    return volume.name


def calibrate(records: Sequence[Event], image: bytes) -> Calibration:
    crtm, measured = _shape(records)
    if _sha256(crtm.data) != crtm.sha256:
        raise CalibrationError("the S-CRTM digest is not the hash of its event data")
    name = _calibrated_volume(image, measured)
    sources = _modules_storing(image, crtm.data)
    if not sources:
        raise CalibrationError("no module of the running firmware stores the S-CRTM data")
    return Calibration(crtm.data, frozenset(sources), name)


def _named_volume(image: bytes, name: UUID) -> bytes:
    matches = [volume for volume in firmware.volumes(image) if volume.name == name]
    if len(matches) != 1:
        raise CalibrationError(f"the new firmware holds {len(matches)} volumes named {name}")
    return matches[0].data


def predict(calibration: Calibration, image: bytes) -> list[bytes]:
    missing = calibration.crtm_modules - _modules_storing(image, calibration.crtm_data)
    if missing:
        names = ", ".join(sorted(str(guid) for guid in missing))
        raise CalibrationError(f"modules no longer store the S-CRTM data: {names}")
    volume = _named_volume(image, calibration.volume_name)
    return [_sha256(calibration.crtm_data), _sha256(volume)]

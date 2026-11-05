import hashlib

import pytest

from pcr0_predict import eventlog, prediction
from pcr0_predict.errors import CalibrationError
from tests import builders
from tests.conftest import NEW_PAYLOAD, PAYLOAD


def _records(log: bytes) -> list[eventlog.Event]:
    return eventlog.firmware_code(eventlog.parse(log))


def test_calibration_reproduces_the_measured_records(
    current_log: bytes, current_image: bytes
) -> None:
    records = _records(current_log)
    calibration = prediction.calibrate(records, current_image)
    assert prediction.predict(calibration, current_image) == [record.sha256 for record in records]


def test_calibration_records_the_volume_and_modules(
    current_log: bytes, current_image: bytes
) -> None:
    calibration = prediction.calibrate(_records(current_log), current_image)
    assert (calibration.volume_name, calibration.crtm_modules) == (
        builders.MAIN_NAME,
        frozenset({builders.TPM_MODULE}),
    )


def test_predict_hashes_the_new_measured_volume(
    current_log: bytes, current_image: bytes, new_image: bytes
) -> None:
    calibration = prediction.calibrate(_records(current_log), current_image)
    expected = hashlib.sha256(builders.main_volume(NEW_PAYLOAD)).digest()
    assert prediction.predict(calibration, new_image)[1] == expected


def test_calibrate_raises_when_the_file_is_another_firmware(
    current_log: bytes, new_image: bytes
) -> None:
    with pytest.raises(CalibrationError, match="not the running firmware"):
        prediction.calibrate(_records(current_log), new_image)


def test_predict_raises_when_the_crtm_module_changed(
    current_log: bytes, current_image: bytes
) -> None:
    calibration = prediction.calibrate(_records(current_log), current_image)
    changed = builders.image(PAYLOAD, builders.stores(bytes(16)))
    with pytest.raises(CalibrationError, match="no longer store"):
        prediction.predict(calibration, changed)


def test_calibrate_raises_on_an_unexpected_record(current_image: bytes) -> None:
    events = builders.firmware_events(current_image, PAYLOAD)
    events.insert(2, builders.LogEvent(0, 0x1, b"POST code"))
    with pytest.raises(CalibrationError, match="exactly an S-CRTM version"):
        prediction.calibrate(_records(builders.event_log(events)), current_image)


@pytest.mark.parametrize(
    ("code", "constant", "expected"),
    [
        (builders.stores(builders.CRTM), builders.CRTM, True),
        (b"\x00" + builders.CRTM, builders.CRTM, False),
        (builders.stores(builders.CRTM), builders.CRTM[:15], False),
        (builders.stores(builders.CRTM), b"", False),
    ],
)
def test_stores_constant(code: bytes, constant: bytes, expected: bool) -> None:
    assert prediction.stores_constant(code, constant) is expected

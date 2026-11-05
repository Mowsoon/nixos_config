import pytest

from tests import builders

PAYLOAD = b"\x4d\x5a" + b"\x00" * 62 + b"current driver"
NEW_PAYLOAD = b"\x4d\x5a" + b"\x00" * 62 + b"updated driver"


@pytest.fixture
def current_image() -> bytes:
    return builders.image(PAYLOAD, builders.stores(builders.CRTM))


@pytest.fixture
def new_image() -> bytes:
    return builders.image(NEW_PAYLOAD, builders.stores(builders.CRTM))


@pytest.fixture
def current_log(current_image: bytes) -> bytes:
    return builders.event_log(builders.firmware_events(current_image, PAYLOAD))

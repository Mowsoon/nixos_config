import asyncio
import json
import struct
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from rgb_effects.config import ServerConfig
from rgb_effects.retry import RetryPolicy
from rgb_effects.sdk.settings import (
    HEADER,
    IDLE_SETTINGS_KEY,
    SettingsError,
    SleepController,
    SleepState,
    apply_sleep_state,
    idle_settings,
    packet,
)

UINT = struct.Struct("<I")


class FakeServer:
    def __init__(self, grant_local: bool = True, settings_status: int = 0) -> None:
        self.grant_local = grant_local
        self.settings_status = settings_status
        self.received: list[tuple[int, bytes]] = []

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                _, _, packet_id, size = HEADER.unpack(await reader.readexactly(HEADER.size))
                body = await reader.readexactly(size)
                self.received.append((packet_id, body))
                writer.write(self._replies(packet_id))
                await writer.drain()
        except asyncio.IncompleteReadError:
            writer.close()

    def _replies(self, packet_id: int) -> bytes:
        status = 0
        extra = b""
        if packet_id == 40:
            extra = packet(40, UINT.pack(6)) + packet(51, b"OpenRGB\0") + packet(100, b"")
        if packet_id == 52:
            extra = packet(53, UINT.pack((1 << 16) if self.grant_local else 0))
        if packet_id == 253:
            status = self.settings_status
        return extra + packet(10, struct.pack("<II", packet_id, status))

    def settings(self) -> dict[str, dict[str, dict[str, object]]]:
        bodies = [body for packet_id, body in self.received if packet_id == 253]
        parsed = json.loads(bodies[-1].rstrip(b"\0"))
        assert isinstance(parsed, dict)
        return parsed


@asynccontextmanager
async def serving(fake: FakeServer) -> AsyncIterator[ServerConfig]:
    server = await asyncio.start_server(fake.handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield ServerConfig("127.0.0.1", port)
    finally:
        server.close()
        await server.wait_closed()


def test_idle_settings_set_both_power_profiles() -> None:
    settings = idle_settings(SleepState(False, 300))[IDLE_SETTINGS_KEY]
    assert isinstance(settings, dict)
    assert settings["plugged_in"] == settings["on_battery"]
    assert settings["plugged_in"]["allow_sleep"] is False


async def test_apply_sends_settings_after_the_handshake() -> None:
    fake = FakeServer()
    async with serving(fake) as server:
        await apply_sleep_state(server, "rgb-effects", SleepState(False, 300))
    assert [packet_id for packet_id, _ in fake.received] == [40, 50, 52, 253]
    assert fake.settings()[IDLE_SETTINGS_KEY]["plugged_in"]["allow_sleep"] is False


async def test_apply_requests_protocol_six_and_local_client() -> None:
    fake = FakeServer()
    async with serving(fake) as server:
        await apply_sleep_state(server, "rgb-effects", SleepState(True, 300))
    bodies = dict(fake.received)
    assert UINT.unpack(bodies[40])[0] == 6 and UINT.unpack(bodies[52])[0] & (1 << 16)


async def test_apply_fails_without_local_client_access() -> None:
    fake = FakeServer(grant_local=False)
    async with serving(fake) as server:
        with pytest.raises(SettingsError):
            await apply_sleep_state(server, "rgb-effects", SleepState(True, 300))
    assert 253 not in dict(fake.received)


async def test_apply_fails_when_settings_are_refused() -> None:
    fake = FakeServer(settings_status=3)
    async with serving(fake) as server:
        with pytest.raises(SettingsError):
            await apply_sleep_state(server, "rgb-effects", SleepState(True, 300))


class StopRun(Exception):
    pass


async def test_controller_applies_each_change_once() -> None:
    fake = FakeServer()
    async with serving(fake) as server:
        controller = SleepController(server, "rgb-effects", 300, RetryPolicy(1.0, 2.0), _never)
        task = asyncio.create_task(controller.run())
        await asyncio.sleep(0.2)
        controller.want(False)
        await asyncio.sleep(0.2)
        controller.want(False)
        await asyncio.sleep(0.2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    sent = [json.loads(body.rstrip(b"\0")) for packet_id, body in fake.received if packet_id == 253]
    allowed = [entry[IDLE_SETTINGS_KEY]["plugged_in"]["allow_sleep"] for entry in sent]
    assert allowed == [True, False]


async def _never(seconds: float) -> None:
    raise StopRun

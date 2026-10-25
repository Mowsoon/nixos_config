import asyncio
import json
import logging
import struct
from dataclasses import dataclass

from rgb_effects.config import ServerConfig
from rgb_effects.errors import RgbEffectsError
from rgb_effects.retry import RetryPolicy, Sleep

logger = logging.getLogger(__name__)

MAGIC = b"ORGB"
HEADER = struct.Struct("<4sIII")
UINT = struct.Struct("<I")
ACK = struct.Struct("<II")
PROTOCOL_VERSION = 6
REQUEST_PROTOCOL_VERSION = 40
SET_CLIENT_NAME = 50
SET_CLIENT_FLAGS = 52
SET_SERVER_FLAGS = 53
PACKET_ACK = 10
SET_SETTINGS = 253
SUPPORTS_SETTINGS = 1 << 4
REQUEST_LOCAL_CLIENT = 1 << 16
LOCAL_CLIENT = 1 << 16
STATUS_OK = 0
IDLE_SETTINGS_KEY = "LogitechHIDPP20IdleSettings"
CALL_TIMEOUT_SECONDS = 5.0
MAX_PACKET_BYTES = 1 << 20


class SettingsError(RgbEffectsError):
    pass


@dataclass(frozen=True, slots=True)
class SleepState:
    allow_sleep: bool
    sleep_seconds: int


def idle_settings(state: SleepState) -> dict[str, object]:
    profile = {
        "dim_when_idle": False,
        "dim_brightness": 50,
        "idle_timeout_s": 60,
        "allow_sleep": state.allow_sleep,
        "sleep_timeout_s": state.sleep_seconds,
    }
    return {
        IDLE_SETTINGS_KEY: {
            "plugged_in": profile,
            "on_battery": profile,
            "force_host_mode": False,
            "show_unmapped_leds": False,
        }
    }


def packet(packet_id: int, payload: bytes) -> bytes:
    return HEADER.pack(MAGIC, 0, packet_id, len(payload)) + payload


class SettingsConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    async def request(self, packet_id: int, payload: bytes) -> dict[int, bytes]:
        self._writer.write(packet(packet_id, payload))
        await self._writer.drain()
        replies: dict[int, bytes] = {}
        while True:
            reply_id, body = await self._receive()
            if reply_id == PACKET_ACK and len(body) >= ACK.size:
                acked, status = ACK.unpack_from(body)
                if acked == packet_id:
                    if status != STATUS_OK:
                        raise SettingsError(f"packet {packet_id} refused with status {status}")
                    return replies
            replies[reply_id] = body

    async def _receive(self) -> tuple[int, bytes]:
        magic, _, packet_id, size = HEADER.unpack(await self._reader.readexactly(HEADER.size))
        if magic != MAGIC or size > MAX_PACKET_BYTES:
            raise SettingsError("malformed packet from the OpenRGB server")
        return packet_id, await self._reader.readexactly(size)


async def apply_sleep_state(server: ServerConfig, client_name: str, state: SleepState) -> None:
    async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
        reader, writer = await asyncio.open_connection(server.host, server.port)
        try:
            await _apply(SettingsConnection(reader, writer), client_name, state)
        finally:
            writer.close()
            await writer.wait_closed()


async def _apply(connection: SettingsConnection, client_name: str, state: SleepState) -> None:
    await connection.request(REQUEST_PROTOCOL_VERSION, UINT.pack(PROTOCOL_VERSION))
    await connection.request(SET_CLIENT_NAME, client_name.encode("utf-8") + b"\0")
    replies = await connection.request(
        SET_CLIENT_FLAGS, UINT.pack(SUPPORTS_SETTINGS | REQUEST_LOCAL_CLIENT)
    )
    flags = replies.get(SET_SERVER_FLAGS, b"")
    if len(flags) < UINT.size or not UINT.unpack_from(flags)[0] & LOCAL_CLIENT:
        raise SettingsError("the OpenRGB server did not grant local client access")
    body = json.dumps(idle_settings(state)).encode("utf-8") + b"\0"
    await connection.request(SET_SETTINGS, body)


class SleepController:
    def __init__(
        self,
        server: ServerConfig,
        client_name: str,
        sleep_seconds: int,
        retry: RetryPolicy,
        sleep: Sleep,
    ) -> None:
        self._server = server
        self._client_name = client_name
        self._sleep_seconds = sleep_seconds
        self._retry = retry
        self._sleep = sleep
        self._wanted = SleepState(True, sleep_seconds)
        self._applied: SleepState | None = None
        self._changed = asyncio.Event()

    def want(self, allow_sleep: bool) -> None:
        state = SleepState(allow_sleep, self._sleep_seconds)
        if state != self._wanted or self._applied is None:
            self._wanted = state
            self._changed.set()

    async def run(self) -> None:
        self._changed.set()
        delay = self._retry.initial_seconds
        while True:
            await self._changed.wait()
            self._changed.clear()
            delay = await self._apply_wanted(delay)

    async def _apply_wanted(self, delay: float) -> float:
        state = self._wanted
        if state == self._applied:
            return delay
        try:
            await apply_sleep_state(self._server, self._client_name, state)
        except (OSError, asyncio.IncompleteReadError, SettingsError) as err:
            logger.warning("keyboard sleep policy: %s, retrying in %.0f s", err, delay)
            await self._sleep(self._retry.jittered(delay))
            self._changed.set()
            return self._retry.next_delay(delay)
        self._applied = state
        logger.info("keyboard sleep %s", "allowed" if state.allow_sleep else "suspended")
        return self._retry.initial_seconds

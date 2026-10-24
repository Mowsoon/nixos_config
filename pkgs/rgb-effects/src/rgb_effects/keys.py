import asyncio
import logging
import socket
from pathlib import Path
from typing import Protocol

from rgb_effects.daemon import RetryPolicy, Sleep

logger = logging.getLogger(__name__)

PULSE_CODE = 0xFFFF
PACKET_SIZE = 2


class KeyListener(Protocol):
    def key_pressed(self, code: int | None) -> None: ...


def decode(packet: bytes) -> int | None:
    if len(packet) != PACKET_SIZE:
        raise ValueError(f"key packet of {len(packet)} bytes")
    code = int.from_bytes(packet, "big")
    return None if code == PULSE_CODE else code


class KeySource:
    def __init__(self, path: Path, listener: KeyListener, retry: RetryPolicy, sleep: Sleep) -> None:
        self._path = path
        self._listener = listener
        self._retry = retry
        self._sleep = sleep

    async def run(self) -> None:
        delay = self._retry.initial_seconds
        while True:
            try:
                await self._receive()
                delay = self._retry.initial_seconds
            except OSError as err:
                logger.warning("key reader %s: %s, retrying in %.0f s", self._path, err, delay)
            await self._sleep(self._retry.jittered(delay))
            delay = self._retry.next_delay(delay)

    async def _receive(self) -> None:
        loop = asyncio.get_running_loop()
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as connection:
            connection.setblocking(False)
            await loop.sock_connect(connection, str(self._path))
            logger.info("connected to the key reader")
            while packet := await loop.sock_recv(connection, 16):
                self._dispatch(packet)
        logger.info("key reader closed the connection")

    def _dispatch(self, packet: bytes) -> None:
        try:
            code = decode(packet)
        except ValueError:
            logger.warning("ignored a malformed key packet")
            return
        self._listener.key_pressed(code)

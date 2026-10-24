import argparse
import asyncio
import enum
import logging
import os
import socket
from collections.abc import AsyncIterator
from pathlib import Path

import evdev
from evdev import ecodes

logger = logging.getLogger("rgb_keyreader")

SD_LISTEN_FDS_START = 3
KEY_UP = 0
KEY_DOWN = 1
MAX_CODE = 0xFFFE
PULSE_PACKET = b"\xff\xff\x01"
MODIFIERS = frozenset(
    {
        ecodes.KEY_LEFTCTRL,
        ecodes.KEY_RIGHTCTRL,
        ecodes.KEY_LEFTALT,
        ecodes.KEY_RIGHTALT,
        ecodes.KEY_LEFTMETA,
        ecodes.KEY_RIGHTMETA,
    }
)
DEVICE_RETRY_SECONDS = 2.0


class Mode(enum.Enum):
    POSITION = "position"
    PULSE = "pulse"


class ActivationError(Exception):
    pass


def _forwarded(code: int, value: int, mode: Mode) -> bool:
    if value == KEY_DOWN:
        return True
    return value == KEY_UP and mode is Mode.POSITION and code in MODIFIERS


def encode(event_type: int, code: int, value: int, mode: Mode) -> bytes | None:
    if event_type != ecodes.EV_KEY or not _forwarded(code, value, mode):
        return None
    if mode is Mode.PULSE:
        return PULSE_PACKET
    if not 0 <= code <= MAX_CODE:
        return None
    return code.to_bytes(2, "big") + bytes([value])


def inherited_listener(environ: dict[str, str], pid: int) -> socket.socket:
    if environ.get("LISTEN_PID") != str(pid) or environ.get("LISTEN_FDS") != "1":
        raise ActivationError("expected exactly one socket passed by systemd")
    listener = socket.socket(fileno=SD_LISTEN_FDS_START)
    listener.setblocking(False)
    return listener


async def _open_device(path: Path) -> evdev.InputDevice:
    while True:
        try:
            return evdev.InputDevice(str(path))
        except OSError as err:
            logger.warning("open %s: %s, retrying", path, err.strerror)
            await asyncio.sleep(DEVICE_RETRY_SECONDS)


async def _events(path: Path) -> AsyncIterator[evdev.InputEvent]:
    while True:
        device = await _open_device(path)
        try:
            async for event in device.async_read_loop():
                yield event
        except OSError as err:
            logger.warning("read %s: %s", path, err.strerror)
        finally:
            device.close()


async def _forward(client: socket.socket, path: Path, mode: Mode) -> None:
    loop = asyncio.get_running_loop()
    async for event in _events(path):
        packet = encode(event.type, event.code, event.value, mode)
        if packet is not None:
            await loop.sock_sendall(client, packet)


async def _until_closed(client: socket.socket) -> None:
    loop = asyncio.get_running_loop()
    while await loop.sock_recv(client, 1):
        continue


async def serve(listener: socket.socket, path: Path, mode: Mode) -> None:
    loop = asyncio.get_running_loop()
    client, _ = await loop.sock_accept(listener)
    with client:
        client.setblocking(False)
        logger.info("client connected")
        tasks = {
            asyncio.create_task(_forward(client, path, mode)),
            asyncio.create_task(_until_closed(client)),
        }
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        for task in done:
            task.result()
    logger.info("client disconnected")


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="rgb-keyreader")
    parser.add_argument("--device", type=Path, required=True)
    parser.add_argument("--mode", type=Mode, choices=list(Mode), default=Mode.POSITION)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    arguments = _arguments(argv)
    try:
        listener = inherited_listener(dict(os.environ), os.getpid())
    except ActivationError:
        logger.exception("not started by socket activation")
        return 2
    with listener:
        try:
            asyncio.run(serve(listener, arguments.device, arguments.mode))
        except (BrokenPipeError, ConnectionResetError):
            logger.info("client went away")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import asyncio
import logging
import re

from dbus_fast import BusType, Message, MessageType
from dbus_fast.aio import MessageBus
from dbus_fast.errors import DBusError

from rgb_effects.session import BUS_NAME, INTERFACE, MAX_FOCUS_SECONDS, OBJECT_PATH

logger = logging.getLogger("rgb_focus")

DURATION = re.compile(r"([0-9]{1,5})([smh]?)")
UNIT_SECONDS = {"": 60, "s": 1, "m": 60, "h": 3600}
CALL_TIMEOUT_SECONDS = 5.0
STOP = "stop"


class FocusError(Exception):
    pass


def parse_duration(text: str) -> int:
    match = DURATION.fullmatch(text.strip().lower())
    if match is None:
        raise FocusError(f"duration {text!r} is not like 25m, 90s or 1h")
    seconds = int(match.group(1)) * UNIT_SECONDS[match.group(2)]
    if not 1 <= seconds <= MAX_FOCUS_SECONDS:
        raise FocusError(f"duration {text!r} is outside 1 s to 24 h")
    return seconds


def request(argument: str) -> Message:
    if argument == STOP:
        member, signature, body = "StopFocus", "", []
    else:
        member, signature, body = "StartFocus", "u", [parse_duration(argument)]
    return Message(
        destination=BUS_NAME,
        path=OBJECT_PATH,
        interface=INTERFACE,
        member=member,
        signature=signature,
        body=body,
    )


async def _send(message: Message) -> None:
    async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
        bus = await MessageBus(bus_type=BusType.SESSION).connect()
        try:
            reply = await bus.call(message)
        finally:
            bus.disconnect()
    if reply is None or reply.message_type == MessageType.ERROR:
        error = reply.error_name if reply is not None else "no reply"
        raise FocusError(f"the effects daemon refused the request: {error}")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(prog="rgb-focus")
    parser.add_argument("duration", help="25m, 90s, 1h, or stop")
    arguments = parser.parse_args(argv)
    try:
        asyncio.run(_send(request(arguments.duration)))
    except (FocusError, OSError, DBusError) as err:
        logger.error("rgb-focus: %s", err)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

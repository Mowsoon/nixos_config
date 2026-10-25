import argparse
import asyncio
import logging

from dbus_fast import BusType, Message, MessageType
from dbus_fast.aio import MessageBus
from dbus_fast.errors import DBusError

from rgb_effects.session import BUS_NAME, INTERFACE, OBJECT_PATH

logger = logging.getLogger("rgb_screen")

ACTIONS = {"grant": "GrantScreen", "revoke": "RevokeScreen"}
CALL_TIMEOUT_SECONDS = 5.0


class ScreenCommandError(Exception):
    pass


def request(action: str) -> Message:
    member = ACTIONS.get(action)
    if member is None:
        raise ScreenCommandError(f"unknown action {action!r}, use grant or revoke")
    return Message(destination=BUS_NAME, path=OBJECT_PATH, interface=INTERFACE, member=member)


async def _send(message: Message) -> None:
    async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
        bus = await MessageBus(bus_type=BusType.SESSION).connect()
        try:
            reply = await bus.call(message)
        finally:
            bus.disconnect()
    if reply is None or reply.message_type == MessageType.ERROR:
        error = reply.error_name if reply is not None else "no reply"
        raise ScreenCommandError(f"the effects daemon refused the request: {error}")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(prog="rgb-screen")
    parser.add_argument("action", choices=sorted(ACTIONS))
    arguments = parser.parse_args(argv)
    try:
        asyncio.run(_send(request(arguments.action)))
    except (ScreenCommandError, OSError, DBusError) as err:
        logger.error("rgb-screen: %s", err)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

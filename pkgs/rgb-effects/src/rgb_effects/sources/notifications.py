import asyncio
import logging
import signal

from dbus_fast import BusType, Message, MessageType
from dbus_fast.aio import MessageBus
from dbus_fast.errors import DBusError

from rgb_effects.dbus.service import BUS_NAME, INTERFACE, OBJECT_PATH

logger = logging.getLogger("rgb_notifywatch")

NOTIFY_RULE = (
    "type='method_call',interface='org.freedesktop.Notifications',"
    "member='Notify',path='/org/freedesktop/Notifications'"
)
MAX_APP_NAME = 64
CALL_TIMEOUT_SECONDS = 5.0
BUS_ERRORS = (OSError, DBusError, EOFError)


def app_name(message: Message) -> str | None:
    if message.message_type != MessageType.METHOD_CALL or message.member != "Notify":
        return None
    if message.interface != "org.freedesktop.Notifications" or not message.body:
        return None
    name = message.body[0]
    if not isinstance(name, str) or not name or len(name) > MAX_APP_NAME:
        return None
    return name if name.isprintable() else None


def monitor_request() -> Message:
    return Message(
        destination="org.freedesktop.DBus",
        path="/org/freedesktop/DBus",
        interface="org.freedesktop.DBus.Monitoring",
        member="BecomeMonitor",
        signature="asu",
        body=[[NOTIFY_RULE], 0],
    )


def forward_request(name: str) -> Message:
    return Message(
        destination=BUS_NAME,
        path=OBJECT_PATH,
        interface=INTERFACE,
        member="NotificationShown",
        signature="s",
        body=[name],
    )


class Forwarder:
    def __init__(self, bus: MessageBus) -> None:
        self._bus = bus
        self._tasks: set[asyncio.Task[None]] = set()

    def handle(self, message: Message) -> bool:
        name = app_name(message)
        if name is not None:
            task = asyncio.get_running_loop().create_task(self._forward(name))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        return message.message_type == MessageType.METHOD_CALL

    async def _forward(self, name: str) -> None:
        try:
            async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
                reply = await self._bus.call(forward_request(name))
        except (*BUS_ERRORS, TimeoutError) as err:
            logger.warning("forward a notification event: %s", type(err).__name__)
            return
        if reply is None or reply.message_type == MessageType.ERROR:
            logger.warning("the effects daemon did not take the notification event")


async def watch() -> None:
    sender = await MessageBus(bus_type=BusType.SESSION).connect()
    monitor = await MessageBus(bus_type=BusType.SESSION).connect()
    try:
        forwarder = Forwarder(sender)
        monitor.add_message_handler(forwarder.handle)
        reply = await monitor.call(monitor_request())
        if reply is None or reply.message_type == MessageType.ERROR:
            raise DBusError("org.freedesktop.DBus.Error.AccessDenied", "BecomeMonitor refused")
        logger.info("watching notifications")
        await monitor.wait_for_disconnect()
    finally:
        monitor.disconnect()
        sender.disconnect()


async def _run_until_stopped() -> None:
    task = asyncio.create_task(watch())
    loop = asyncio.get_running_loop()
    for stop_signal in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(stop_signal, task.cancel)
    try:
        await task
    except asyncio.CancelledError:
        logger.info("stopped")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    try:
        asyncio.run(_run_until_stopped())
    except BUS_ERRORS:
        logger.exception("session bus monitoring failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import asyncio
import logging
from pathlib import Path
from typing import Protocol

from dbus_fast import BusType, Message, MessageType, Variant
from dbus_fast.aio import MessageBus
from dbus_fast.errors import DBusError

from rgb_effects.daemon import PowerState, RetryPolicy, Sleep

logger = logging.getLogger(__name__)

UPOWER = "org.freedesktop.UPower"
UPOWER_PATH = "/org/freedesktop/UPower"
PROPERTIES = "org.freedesktop.DBus.Properties"
CALL_TIMEOUT_SECONDS = 5.0
BUS_ERRORS = (OSError, DBusError, EOFError, TimeoutError)


class PowerListener(Protocol):
    def power_changed(self, state: PowerState) -> None: ...


def keyboard_capacity(root: Path, model: str) -> int | None:
    for supply in sorted(root.glob("*")):
        try:
            if (supply / "model_name").read_text(encoding="utf-8").strip() != model:
                continue
            return int((supply / "capacity").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
    return None


def is_low(capacity: int | None, threshold: int) -> bool:
    return capacity is not None and capacity <= threshold


class PowerMonitor:
    def __init__(
        self,
        listener: PowerListener,
        battery: tuple[Path, str, int],
        poll_seconds: float,
        retry: RetryPolicy,
        sleep: Sleep,
    ) -> None:
        self._listener = listener
        self._root, self._model, self._threshold = battery
        self._poll_seconds = poll_seconds
        self._retry = retry
        self._sleep = sleep
        self._state = PowerState(on_battery=False, keyboard_low=False)

    async def run(self) -> None:
        delay = self._retry.initial_seconds
        while True:
            try:
                await self._watch()
            except BUS_ERRORS as err:
                logger.warning("power monitor: %s, retrying in %.0f s", err, delay)
            await self._sleep(self._retry.jittered(delay))
            delay = self._retry.next_delay(delay)

    async def _watch(self) -> None:
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        try:
            await self._subscribe(bus)
            while bus.connected:
                self._publish(on_battery=await self._on_battery(bus))
                await self._sleep(self._poll_seconds)
        finally:
            bus.disconnect()

    async def _subscribe(self, bus: MessageBus) -> None:
        bus.add_message_handler(self._on_message)
        rule = f"type='signal',sender='{UPOWER}',path='{UPOWER_PATH}',interface='{PROPERTIES}'"
        await self._call(
            bus,
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "AddMatch",
            "s",
            [rule],
        )

    async def _on_battery(self, bus: MessageBus) -> bool:
        reply = await self._call(
            bus, UPOWER, UPOWER_PATH, PROPERTIES, "Get", "ss", [UPOWER, "OnBattery"]
        )
        value = reply.body[0].value if reply.body and isinstance(reply.body[0], Variant) else None
        return value is True

    def _on_message(self, message: Message) -> None:
        if message.member != "PropertiesChanged" or message.path != UPOWER_PATH:
            return
        changed = message.body[1] if len(message.body) > 1 else {}
        variant = changed.get("OnBattery") if isinstance(changed, dict) else None
        if isinstance(variant, Variant) and isinstance(variant.value, bool):
            self._publish(on_battery=variant.value)

    def _publish(self, on_battery: bool) -> None:
        capacity = keyboard_capacity(self._root, self._model)
        state = PowerState(on_battery, is_low(capacity, self._threshold))
        if state != self._state:
            self._state = state
            logger.info(
                "on battery: %s, keyboard battery low: %s", state.on_battery, state.keyboard_low
            )
            self._listener.power_changed(state)

    async def _call(
        self,
        bus: MessageBus,
        destination: str,
        path: str,
        interface: str,
        member: str,
        signature: str,
        body: list[object],
    ) -> Message:
        request = Message(
            destination=destination,
            path=path,
            interface=interface,
            member=member,
            signature=signature,
            body=body,
        )
        async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
            reply = await bus.call(request)
        if reply is None or reply.message_type == MessageType.ERROR:
            raise DBusError("org.freedesktop.DBus.Error.Failed", f"{member} failed")
        return reply

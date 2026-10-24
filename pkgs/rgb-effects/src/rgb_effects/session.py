import asyncio
import logging
from pathlib import Path
from types import TracebackType
from typing import Protocol

from dbus_fast import BusType, Message, MessageType, RequestNameReply
from dbus_fast.aio import MessageBus
from dbus_fast.annotations import DBusStr, DBusUInt32
from dbus_fast.constants import NameFlag
from dbus_fast.errors import DBusError
from dbus_fast.service import ServiceInterface, method

from rgb_effects.errors import SessionError

BUS_NAME = "org.hephaestus.RgbEffects"
OBJECT_PATH = "/org/hephaestus/RgbEffects"
INTERFACE = "org.hephaestus.RgbEffects"
KWIN = "org.kde.KWin"
SCRIPTING_PATH = "/Scripting"
SCRIPTING_INTERFACE = "org.kde.kwin.Scripting"
SCRIPT_INTERFACE = "org.kde.kwin.Script"
PLUGIN_NAME = "rgb-effects-active-window"
CALL_TIMEOUT_SECONDS = 5.0
BUS_ERRORS = (OSError, DBusError, EOFError)
MAX_FOCUS_SECONDS = 86400

logger = logging.getLogger(__name__)


class WindowListener(Protocol):
    def window_activated(self, resource_class: str) -> None: ...

    def focus_started(self, seconds: float) -> None: ...

    def focus_stopped(self) -> None: ...


class EffectsInterface(ServiceInterface):
    def __init__(self, listener: WindowListener) -> None:
        super().__init__(INTERFACE)
        self._listener = listener

    @method(name="WindowActivated")
    def window_activated(self, resource_class: DBusStr) -> None:
        self._listener.window_activated(resource_class)

    @method(name="StartFocus")
    def start_focus(self, seconds: DBusUInt32) -> None:
        if not 1 <= seconds <= MAX_FOCUS_SECONDS:
            raise DBusError("org.freedesktop.DBus.Error.InvalidArgs", "focus seconds out of range")
        self._listener.focus_started(float(seconds))

    @method(name="StopFocus")
    def stop_focus(self) -> None:
        self._listener.focus_stopped()


class Session:
    def __init__(self, listener: WindowListener, script: Path) -> None:
        self._listener = listener
        self._script = script
        self._bus: MessageBus | None = None

    async def __aenter__(self) -> "Session":
        try:
            async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
                self._bus = await MessageBus(bus_type=BusType.SESSION).connect()
            self._bus.export(OBJECT_PATH, EffectsInterface(self._listener))
            await self._own_name()
            await self._load_script()
        except (*BUS_ERRORS, TimeoutError) as err:
            await self.close()
            raise SessionError("set up the session bus link") from err
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        bus = self._bus
        if bus is None:
            return
        try:
            await self._kwin(
                SCRIPTING_PATH, SCRIPTING_INTERFACE, "unloadScript", "s", [PLUGIN_NAME]
            )
        except (*BUS_ERRORS, TimeoutError, SessionError) as err:
            logger.warning("unload the KWin script: %s", err)
        finally:
            self._bus = None
            bus.disconnect()

    async def _own_name(self) -> None:
        reply = await self._connected().request_name(BUS_NAME, NameFlag.DO_NOT_QUEUE)
        if reply != RequestNameReply.PRIMARY_OWNER:
            raise SessionError(f"bus name {BUS_NAME} is already owned")

    async def _load_script(self) -> None:
        await self._kwin(SCRIPTING_PATH, SCRIPTING_INTERFACE, "unloadScript", "s", [PLUGIN_NAME])
        reply = await self._kwin(
            SCRIPTING_PATH,
            SCRIPTING_INTERFACE,
            "loadScript",
            "ss",
            [str(self._script), PLUGIN_NAME],
        )
        script_id = reply.body[0] if reply.body else None
        if not isinstance(script_id, int) or script_id < 0:
            raise SessionError(f"KWin refused the script {self._script}")
        await self._kwin(f"{SCRIPTING_PATH}/Script{script_id}", SCRIPT_INTERFACE, "run", "", [])

    async def _kwin(
        self, path: str, interface: str, member: str, signature: str, body: list[object]
    ) -> Message:
        request = Message(
            destination=KWIN,
            path=path,
            interface=interface,
            member=member,
            signature=signature,
            body=body,
        )
        async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
            reply = await self._connected().call(request)
        if reply is None or reply.message_type == MessageType.ERROR:
            error = reply.error_name if reply is not None else "no reply"
            raise SessionError(f"KWin {member} failed: {error}")
        return reply

    def _connected(self) -> MessageBus:
        if self._bus is None:
            raise SessionError("session bus is not connected")
        return self._bus

import asyncio
import os
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dbus_fast import BusType, Message, MessageType, Variant
from dbus_fast.aio import MessageBus
from dbus_fast.errors import DBusError

from rgb_effects.errors import RgbEffectsError

PORTAL = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENCAST = "org.freedesktop.portal.ScreenCast"
REQUEST = "org.freedesktop.portal.Request"
SESSION = "org.freedesktop.portal.Session"
MONITOR_SOURCE = 1
HIDDEN_CURSOR = 1
PERSIST_UNTIL_REVOKED = 2
RESPONSE_SUCCESS = 0
RESPONSE_CANCELLED = 1
QUIET_TIMEOUT_SECONDS = 15.0
DIALOG_TIMEOUT_SECONDS = 180.0
TOKEN_LENGTH = 512


class PortalError(RgbEffectsError):
    pass


class PortalCancelled(PortalError):
    pass


@dataclass(frozen=True, slots=True)
class Capture:
    session: str
    node: int
    descriptor: int
    token: str | None


def request_path(unique_name: str, token: str) -> str:
    sender = unique_name.removeprefix(":").replace(".", "_")
    return f"{PORTAL_PATH}/request/{sender}/{token}"


def _token() -> str:
    return "rgb_" + secrets.token_hex(8)


def _value(results: dict[str, Any], key: str) -> Any:
    entry = results.get(key)
    return entry.value if isinstance(entry, Variant) else None


class TokenStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> str | None:
        try:
            text = self._path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        except OSError as err:
            raise PortalError(f"read {self._path}") from err
        return text if text and len(text) <= TOKEN_LENGTH and text.isprintable() else None

    def write(self, token: str) -> None:
        staging = self._path.with_suffix(".tmp")
        descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(token)
        staging.replace(self._path)

    def delete(self) -> None:
        self._path.unlink(missing_ok=True)


class ScreenCastPortal:
    def __init__(self) -> None:
        self._bus: MessageBus | None = None

    async def start(self, token: str | None, interactive: bool) -> Capture:
        bus = await self._connected()
        session = await self._create_session(bus)
        try:
            return await self._select_and_start(bus, session, token, interactive)
        except BaseException:
            await self.close(session)
            raise

    async def close(self, session: str) -> None:
        bus = self._bus
        if bus is None or not bus.connected:
            return
        message = Message(destination=PORTAL, path=session, interface=SESSION, member="Close")
        try:
            await bus.call(message)
        except (OSError, DBusError, EOFError) as err:
            raise PortalError("close the screen cast session") from err

    async def _connected(self) -> MessageBus:
        if self._bus is None or not self._bus.connected:
            bus = MessageBus(bus_type=BusType.SESSION, negotiate_unix_fd=True)
            self._bus = await bus.connect()
        return self._bus

    async def _select_and_start(
        self, bus: MessageBus, session: str, token: str | None, interactive: bool
    ) -> Capture:
        await self._request(bus, "SelectSources", "oa{sv}", [session, _sources(token)], 0)
        timeout = DIALOG_TIMEOUT_SECONDS if interactive else QUIET_TIMEOUT_SECONDS
        results = await self._request(bus, "Start", "osa{sv}", [session, "", {}], timeout)
        streams = _value(results, "streams")
        if not streams:
            raise PortalError("the portal granted no stream")
        descriptor = await self._open_remote(bus, session)
        return Capture(session, int(streams[0][0]), descriptor, _value(results, "restore_token"))

    async def _create_session(self, bus: MessageBus) -> str:
        options = {"session_handle_token": Variant("s", _token())}
        results = await self._request(bus, "CreateSession", "a{sv}", [options], 0)
        handle = _value(results, "session_handle")
        if not isinstance(handle, str):
            raise PortalError("the portal returned no session")
        return handle

    async def _open_remote(self, bus: MessageBus, session: str) -> int:
        message = Message(
            destination=PORTAL,
            path=PORTAL_PATH,
            interface=SCREENCAST,
            member="OpenPipeWireRemote",
            signature="oa{sv}",
            body=[session, {}],
        )
        reply = await self._call(bus, message, QUIET_TIMEOUT_SECONDS)
        if not reply.unix_fds:
            raise PortalError("the portal returned no PipeWire descriptor")
        return int(reply.unix_fds[0])

    async def _request(
        self, bus: MessageBus, member: str, signature: str, body: list[Any], timeout: float
    ) -> dict[str, Any]:
        token = _token()
        body[-1] = {**body[-1], "handle_token": Variant("s", token)}
        path = request_path(bus.unique_name or "", token)
        response: asyncio.Future[tuple[int, dict[str, Any]]] = (
            asyncio.get_running_loop().create_future()
        )
        handler = _response_handler(path, response)
        rule = f"type='signal',interface='{REQUEST}',member='Response',path='{path}'"
        bus.add_message_handler(handler)
        await self._call(bus, _match("AddMatch", rule), QUIET_TIMEOUT_SECONDS)
        try:
            await self._call(bus, _portal_call(member, signature, body), QUIET_TIMEOUT_SECONDS)
            async with asyncio.timeout(timeout or QUIET_TIMEOUT_SECONDS):
                code, results = await response
        finally:
            bus.remove_message_handler(handler)
            await self._call(bus, _match("RemoveMatch", rule), QUIET_TIMEOUT_SECONDS)
        return _checked(member, code, results)

    async def _call(self, bus: MessageBus, message: Message, timeout: float) -> Message:
        try:
            async with asyncio.timeout(timeout):
                reply = await bus.call(message)
        except (OSError, DBusError, EOFError) as err:
            raise PortalError(f"portal call {message.member}") from err
        if reply is None or reply.message_type == MessageType.ERROR:
            error = reply.error_name if reply is not None else "no reply"
            raise PortalError(f"portal call {message.member} failed: {error}")
        return reply


def _sources(token: str | None) -> dict[str, Variant]:
    options = {
        "types": Variant("u", MONITOR_SOURCE),
        "multiple": Variant("b", False),
        "cursor_mode": Variant("u", HIDDEN_CURSOR),
        "persist_mode": Variant("u", PERSIST_UNTIL_REVOKED),
    }
    if token is not None:
        options["restore_token"] = Variant("s", token)
    return options


def _match(member: str, rule: str) -> Message:
    return Message(
        destination="org.freedesktop.DBus",
        path="/org/freedesktop/DBus",
        interface="org.freedesktop.DBus",
        member=member,
        signature="s",
        body=[rule],
    )


def _portal_call(member: str, signature: str, body: list[Any]) -> Message:
    return Message(
        destination=PORTAL,
        path=PORTAL_PATH,
        interface=SCREENCAST,
        member=member,
        signature=signature,
        body=body,
    )


def _response_handler(
    path: str, response: "asyncio.Future[tuple[int, dict[str, Any]]]"
) -> Callable[[Message], bool]:
    def handle(message: Message) -> bool:
        if message.path != path or message.member != "Response" or response.done():
            return False
        code, results = message.body
        response.set_result((int(code), dict(results)))
        return False

    return handle


def _checked(member: str, code: int, results: dict[str, Any]) -> dict[str, Any]:
    if code == RESPONSE_CANCELLED:
        raise PortalCancelled(f"{member} cancelled by the user")
    if code != RESPONSE_SUCCESS:
        raise PortalError(f"{member} ended with response {code}")
    return results

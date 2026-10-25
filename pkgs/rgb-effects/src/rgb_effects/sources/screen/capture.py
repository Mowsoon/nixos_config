import asyncio
import enum
import logging
import os
from typing import Protocol

from rgb_effects.sources.screen.portal import Capture, PortalCancelled, PortalError, TokenStore

START_DELAY_SECONDS = 1.0

logger = logging.getLogger(__name__)


class Command(enum.Enum):
    SYNC = "sync"
    GRANT = "grant"
    REVOKE = "revoke"


class Portal(Protocol):
    async def start(self, token: str | None, interactive: bool) -> Capture: ...

    async def close(self, session: str) -> None: ...


class Feed(Protocol):
    async def run(self, descriptor: int, node: int) -> None: ...


class ScreenCapture:
    def __init__(
        self,
        portal: Portal,
        feed: Feed,
        tokens: TokenStore,
        capture_on_battery: bool,
        start_delay: float = START_DELAY_SECONDS,
    ) -> None:
        self._start_delay = start_delay
        self._portal = portal
        self._feed = feed
        self._feed_task: asyncio.Task[None] | None = None
        self._tokens = tokens
        self._capture_on_battery = capture_on_battery
        self._fullscreen = False
        self._on_battery = False
        self._capture: Capture | None = None
        self._commands: asyncio.Queue[Command] = asyncio.Queue()

    @property
    def active(self) -> bool:
        return self._capture is not None

    def fullscreen_changed(self, fullscreen: bool) -> None:
        if fullscreen != self._fullscreen:
            self._fullscreen = fullscreen
            self._commands.put_nowait(Command.SYNC)

    def power_changed(self, on_battery: bool) -> None:
        if on_battery != self._on_battery:
            self._on_battery = on_battery
            self._commands.put_nowait(Command.SYNC)

    def grant(self) -> None:
        self._commands.put_nowait(Command.GRANT)

    def revoke(self) -> None:
        self._commands.put_nowait(Command.REVOKE)

    async def run(self) -> None:
        try:
            while True:
                command = await self._commands.get()
                await self._handle(command)
        finally:
            await self._stop_quietly()

    async def _stop_quietly(self) -> None:
        try:
            await self._stop()
        except PortalError as err:
            logger.warning("screen capture: %s", err)

    async def _handle(self, command: Command) -> None:
        try:
            if command is Command.GRANT:
                await self._grant()
            elif command is Command.REVOKE:
                await self._revoke()
            await self._sync()
        except PortalError as err:
            logger.warning("screen capture: %s (%s)", err, err.__cause__ or "no cause")

    def _wanted(self) -> bool:
        allowed = self._capture_on_battery or not self._on_battery
        return self._fullscreen and allowed

    async def _sync(self) -> None:
        if not self._wanted():
            await self._stop()
            return
        if self._capture is not None:
            return
        await asyncio.sleep(self._start_delay)
        if not self._wanted():
            return
        token = self._tokens.read()
        if token is None:
            logger.info("full screen without a screen capture grant, using the window colour")
            return
        try:
            capture = await self._portal.start(token, interactive=False)
            self._keep(capture)
            self._feed_task = asyncio.create_task(self._feed.run(capture.descriptor, capture.node))
        except PortalCancelled:
            self._tokens.delete()
            logger.info("screen capture grant refused, forgotten until rgb-screen grant")

    async def _grant(self) -> None:
        await self._stop()
        capture = await self._portal.start(None, interactive=True)
        self._keep(capture)
        os.close(capture.descriptor)
        logger.info("screen capture granted")
        await self._stop()

    async def _revoke(self) -> None:
        await self._stop()
        self._tokens.delete()
        logger.info("screen capture grant revoked")

    def _keep(self, capture: Capture) -> None:
        if capture.token is not None:
            self._tokens.write(capture.token)
        self._capture = capture
        logger.info("screen capture session started")

    async def _stop(self) -> None:
        capture, self._capture = self._capture, None
        feed, self._feed_task = self._feed_task, None
        if feed is not None:
            feed.cancel()
            await asyncio.gather(feed, return_exceptions=True)
        if capture is None:
            return
        await self._portal.close(capture.session)
        logger.info("screen capture session stopped")

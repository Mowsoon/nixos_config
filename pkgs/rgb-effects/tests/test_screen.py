import asyncio
import os
from pathlib import Path

import pytest

from rgb_effects.portal import Capture, PortalCancelled, TokenStore
from rgb_effects.screen import ScreenCapture


class FakeFeed:
    def __init__(self) -> None:
        self.runs: list[int] = []

    async def run(self, descriptor: int, node: int) -> None:
        self.runs.append(node)
        os.close(descriptor)
        await asyncio.Event().wait()


class FakePortal:
    def __init__(self, cancel: bool = False) -> None:
        self.cancel = cancel
        self.starts: list[tuple[str | None, bool]] = []
        self.closed: list[str] = []
        self.descriptors: list[int] = []

    async def start(self, token: str | None, interactive: bool) -> Capture:
        self.starts.append((token, interactive))
        if self.cancel:
            raise PortalCancelled("cancelled")
        read, write = os.pipe()
        os.close(write)
        self.descriptors.append(read)
        return Capture(f"/session/{len(self.starts)}", 42, read, f"token-{len(self.starts)}")

    async def close(self, session: str) -> None:
        self.closed.append(session)


async def _settle(capture: ScreenCapture) -> None:
    task = asyncio.create_task(capture.run())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def _capture(
    tmp_path: Path, portal: FakePortal, token: str | None = "saved", feed: FakeFeed | None = None
) -> ScreenCapture:
    store = TokenStore(tmp_path / "token")
    if token is not None:
        store.write(token)
    return ScreenCapture(portal, feed or FakeFeed(), store, False, start_delay=0.0)


async def test_full_screen_without_grant_starts_nothing(tmp_path: Path) -> None:
    portal = FakePortal()
    capture = _capture(tmp_path, portal, token=None)
    capture.fullscreen_changed(True)
    await _settle(capture)
    assert portal.starts == []


async def test_full_screen_starts_a_quiet_session_and_keeps_the_new_token(tmp_path: Path) -> None:
    portal = FakePortal()
    capture = _capture(tmp_path, portal)
    capture.fullscreen_changed(True)
    await _settle(capture)
    assert portal.starts == [("saved", False)]
    assert TokenStore(tmp_path / "token").read() == "token-1"


async def test_grant_closes_the_session_descriptor(tmp_path: Path) -> None:
    portal = FakePortal()
    capture = _capture(tmp_path, portal, token=None)
    capture.grant()
    await _settle(capture)
    with pytest.raises(OSError):
        os.fstat(portal.descriptors[0])


async def test_leaving_full_screen_closes_the_session(tmp_path: Path) -> None:
    portal = FakePortal()
    capture = _capture(tmp_path, portal)
    task = asyncio.create_task(capture.run())
    capture.fullscreen_changed(True)
    await asyncio.sleep(0.05)
    capture.fullscreen_changed(False)
    await asyncio.sleep(0.05)
    closed, active = list(portal.closed), capture.active
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed == ["/session/1"] and not active


async def test_battery_prevents_capture(tmp_path: Path) -> None:
    portal = FakePortal()
    capture = _capture(tmp_path, portal)
    capture.power_changed(True)
    capture.fullscreen_changed(True)
    await _settle(capture)
    assert portal.starts == []


async def test_refused_quiet_start_forgets_the_token(tmp_path: Path) -> None:
    portal = FakePortal(cancel=True)
    capture = _capture(tmp_path, portal)
    capture.fullscreen_changed(True)
    await _settle(capture)
    assert TokenStore(tmp_path / "token").read() is None


async def test_grant_asks_interactively_and_stores_the_token(tmp_path: Path) -> None:
    portal = FakePortal()
    capture = _capture(tmp_path, portal, token=None)
    capture.grant()
    await _settle(capture)
    assert portal.starts == [(None, True)] and portal.closed == ["/session/1"]
    assert TokenStore(tmp_path / "token").read() == "token-1"


async def test_revoke_forgets_the_token(tmp_path: Path) -> None:
    portal = FakePortal()
    capture = _capture(tmp_path, portal)
    capture.revoke()
    await _settle(capture)
    assert TokenStore(tmp_path / "token").read() is None


async def test_full_screen_starts_the_feed_on_the_granted_node(tmp_path: Path) -> None:
    feed = FakeFeed()
    capture = _capture(tmp_path, FakePortal(), feed=feed)
    capture.fullscreen_changed(True)
    await _settle(capture)
    assert feed.runs == [42]


async def test_brief_full_screen_starts_nothing(tmp_path: Path) -> None:
    portal = FakePortal()
    store = TokenStore(tmp_path / "token")
    store.write("saved")
    capture = ScreenCapture(portal, FakeFeed(), store, False, start_delay=0.2)
    task = asyncio.create_task(capture.run())
    capture.fullscreen_changed(True)
    await asyncio.sleep(0.05)
    capture.fullscreen_changed(False)
    await asyncio.sleep(0.3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert portal.starts == []


async def test_stopping_the_task_closes_an_open_session(tmp_path: Path) -> None:
    portal = FakePortal()
    capture = _capture(tmp_path, portal)
    capture.fullscreen_changed(True)
    await _settle(capture)
    assert portal.closed == ["/session/1"]

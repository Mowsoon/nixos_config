import asyncio
import stat
from pathlib import Path

import pytest
from dbus_fast import Message, MessageType, Variant

from rgb_effects.sources.screen.portal import (
    PERSIST_UNTIL_REVOKED,
    PortalCancelled,
    PortalError,
    TokenStore,
    _checked,
    _response_handler,
    _sources,
    request_path,
)


def test_request_path_escapes_the_unique_name() -> None:
    path = request_path(":1.234", "rgb_token")
    assert path == "/org/freedesktop/portal/desktop/request/1_234/rgb_token"


def test_sources_persist_until_revoked() -> None:
    assert _sources(None)["persist_mode"].value == PERSIST_UNTIL_REVOKED


def test_sources_pass_the_restore_token() -> None:
    assert _sources("abc")["restore_token"].value == "abc"


def test_sources_omit_a_missing_token() -> None:
    assert "restore_token" not in _sources(None)


@pytest.mark.parametrize(("code", "error"), [(1, PortalCancelled), (2, PortalError)])
def test_checked_raises_on_failed_response(code: int, error: type[Exception]) -> None:
    with pytest.raises(error):
        _checked("Start", code, {})


def test_checked_returns_results_on_success() -> None:
    assert _checked("Start", 0, {"a": Variant("s", "b")})["a"].value == "b"


async def test_response_handler_resolves_its_request() -> None:
    future: asyncio.Future[tuple[int, dict[str, Variant]]] = (
        asyncio.get_running_loop().create_future()
    )
    handler = _response_handler("/request/1", future)
    signal = Message.new_signal(
        "/request/1", "org.freedesktop.portal.Request", "Response", "ua{sv}", [0, {}]
    )
    handler(signal)
    assert future.result() == (0, {})


async def test_response_handler_ignores_other_paths() -> None:
    future: asyncio.Future[tuple[int, dict[str, Variant]]] = (
        asyncio.get_running_loop().create_future()
    )
    handler = _response_handler("/request/1", future)
    handler(
        Message.new_signal(
            "/request/2", "org.freedesktop.portal.Request", "Response", "ua{sv}", [0, {}]
        )
    )
    assert not future.done()


def test_token_store_round_trip(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "token")
    store.write("restore-me")
    assert store.read() == "restore-me"


def test_token_store_writes_private_file(tmp_path: Path) -> None:
    TokenStore(tmp_path / "token").write("secret")
    assert stat.S_IMODE((tmp_path / "token").stat().st_mode) == 0o600


def test_token_store_reads_nothing_when_missing(tmp_path: Path) -> None:
    assert TokenStore(tmp_path / "token").read() is None


def test_token_store_delete_is_idempotent(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "token")
    store.write("x")
    store.delete()
    store.delete()
    assert store.read() is None


def test_method_return_is_not_a_response() -> None:
    reply = Message(message_type=MessageType.METHOD_RETURN, reply_serial=1)
    assert reply.member is None

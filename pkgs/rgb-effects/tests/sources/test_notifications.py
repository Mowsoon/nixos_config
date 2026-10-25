import pytest
from dbus_fast import Message, MessageType

from rgb_effects.sources.notifications import app_name, forward_request, monitor_request

NOTIFY_SIGNATURE = "susssasa{sv}i"


def _notify(name: object) -> Message:
    return Message(
        path="/org/freedesktop/Notifications",
        interface="org.freedesktop.Notifications",
        member="Notify",
        signature=NOTIFY_SIGNATURE,
        body=[name, 0, "", "secret summary", "secret body", [], {}, -1],
    )


def test_app_name_keeps_only_the_application() -> None:
    assert app_name(_notify("Firefox")) == "Firefox"


@pytest.mark.parametrize("name", ["", "x" * 65, "bad\nname"])
def test_app_name_rejects_malformed_names(name: str) -> None:
    assert app_name(_notify(name)) is None


def test_app_name_ignores_other_members() -> None:
    message = Message(
        path="/org/freedesktop/Notifications",
        interface="org.freedesktop.Notifications",
        member="CloseNotification",
        signature="u",
        body=[3],
    )
    assert app_name(message) is None


def test_app_name_ignores_replies() -> None:
    reply = Message(message_type=MessageType.METHOD_RETURN, reply_serial=1)
    assert app_name(reply) is None


def test_monitor_request_matches_notify_calls_only() -> None:
    rules = monitor_request().body[0]
    assert rules == [
        "type='method_call',interface='org.freedesktop.Notifications',"
        "member='Notify',path='/org/freedesktop/Notifications'"
    ]


def test_forward_request_carries_only_the_name() -> None:
    assert forward_request("Firefox").body == ["Firefox"]

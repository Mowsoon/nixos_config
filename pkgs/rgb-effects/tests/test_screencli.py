import pytest

from rgb_effects.screencli import ScreenCommandError, request


@pytest.mark.parametrize(
    ("action", "member"), [("grant", "GrantScreen"), ("revoke", "RevokeScreen")]
)
def test_request_names_the_daemon_method(action: str, member: str) -> None:
    assert request(action).member == member


def test_request_rejects_unknown_action() -> None:
    with pytest.raises(ScreenCommandError):
        request("share")

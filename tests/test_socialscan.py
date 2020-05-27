import pytest

from socialscan.util import sync_execute_queries
from socialscan.platforms import Platforms, PlatformResponse

TIMEOUT_DURATION = 25  # in seconds

AVAILABLE_USERNAMES = ["jsndiwimw"]
UNAVAILABLE_USERNAMES = ["social"]
INVALID_USERNAMES = ["*"]

UNUSED_EMAILS = ["unused@notanemail.com"]
USED_EMAILS = ["a@gmail.com"]


def assert_available(response: PlatformResponse):
    assert response.available
    assert response.valid
    assert response.success


def assert_unavailable(response: PlatformResponse):
    assert not response.available
    assert response.valid
    assert response.success


def assert_invalid(response: PlatformResponse):
    assert not response.available
    assert not response.valid
    assert response.success


@pytest.mark.parametrize("platform", [p for p in Platforms if hasattr(p.value, "check_username")])
@pytest.mark.parametrize(
    "usernames, assert_function",
    [
        (AVAILABLE_USERNAMES, assert_available),
        (UNAVAILABLE_USERNAMES, assert_unavailable),
        (INVALID_USERNAMES, assert_invalid),
    ],
)
@pytest.mark.timeout(TIMEOUT_DURATION)
def test_usernames(platform, usernames, assert_function):
    for username in usernames:
        response = sync_execute_queries([username], [platform])[0]
        assert_function(response)


@pytest.mark.parametrize("platform", [p for p in Platforms if hasattr(p.value, "check_email")])
@pytest.mark.parametrize(
    "emails, assert_function",
    [(UNUSED_EMAILS, assert_available), (USED_EMAILS, assert_unavailable)],
)
@pytest.mark.timeout(TIMEOUT_DURATION)
def test_emails(platform, emails, assert_function):
    for email in emails:
        response = sync_execute_queries([email], [platform])[0]
        assert_function(response)

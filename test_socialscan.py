import asyncio
import pytest

from socialscan.util import query_without_checkers
from socialscan.platforms import Platforms, PlatformResponse

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


@pytest.mark.parametrize('platform', [p for p in Platforms if "check_username" in p.value.__dict__])
@pytest.mark.parametrize('usernames, assert_function', [(AVAILABLE_USERNAMES, assert_available),
                                                        (UNAVAILABLE_USERNAMES, assert_unavailable),
                                                        (INVALID_USERNAMES, assert_invalid)])
def test_usernames(platform, usernames, assert_function):
    for username in usernames:
        response = asyncio.run(query_without_checkers(platform, username))
        assert_function(response)


@pytest.mark.parametrize('platform', [p for p in Platforms if "check_email" in p.value.__dict__])
@pytest.mark.parametrize('emails, assert_function', [(UNUSED_EMAILS, assert_available),
                                                     (USED_EMAILS, assert_unavailable)])
def test_emails(platform, emails, assert_function):
    for email in emails:
        response = asyncio.run(query_without_checkers(platform, email))
        assert_function(response)

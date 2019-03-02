import aiohttp
import re

from namescan.platforms import Platforms, PlatformResponse

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,253}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,253}[a-zA-Z0-9])?)+$")


async def init_prerequest(platform, checkers):
    if platform.value.prerequest_req:
        await checkers[platform].get_token()


def init_checkers(session):
    checkers = {}
    for platform in Platforms:
        checkers[platform] = platform.value(session)
    return checkers


async def check_available(platform, query, checkers):
    try:
        is_email = EMAIL_REGEX.match(query)
        if is_email and "check_email" in platform.value.__dict__:
            return await checkers[platform].check_email(query)
        elif not is_email:
            return await checkers[platform].check_username(query)
    except (aiohttp.ClientError, KeyError) as e:
        response = PlatformResponse(platform, query)
        response.available = response.valid = response.success = False
        response.message = f"{type(e).__name__} - {e}"
        return response

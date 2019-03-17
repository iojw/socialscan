import re

import aiohttp

from socialscan.platforms import PlatformResponse, Platforms

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,253}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,253}[a-zA-Z0-9])?)+$")


async def init_prerequest(platform, checkers):
    if platform.value.prerequest_req:
        await checkers[platform].get_token()


def init_checkers(session, proxy_list=[]):
    checkers = {}
    for platform in Platforms:
        checkers[platform] = platform.value(session, proxy_list=proxy_list)
    return checkers


async def query(platform, query, checkers):
    try:
        is_email = EMAIL_REGEX.match(query)
        if is_email and "check_email" in platform.value.__dict__:
            return await checkers[platform].check_email(query)
        elif not is_email and "check_username" in platform.value.__dict__:
            return await checkers[platform].check_username(query)
    except (aiohttp.ClientError, KeyError) as e:
        response = PlatformResponse(platform=platform,
                                    query=query,
                                    available=False,
                                    valid=False,
                                    success=False,
                                    message=f"{type(e).__name__} - {e}")
        return response

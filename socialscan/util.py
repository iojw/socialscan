import re

import aiohttp

from socialscan.platforms import PlatformResponse, Platforms, QueryError

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,253}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,253}[a-zA-Z0-9])?)+$")


async def init_prerequest(platform, checkers):
    if platform.value.prerequest_req:
        await checkers[platform].get_token()


def init_checkers(session, proxy_list=[]):
    checkers = {}
    for platform in Platforms:
        checkers[platform] = platform.value(session, proxy_list=proxy_list)
    return checkers


async def query(platform, query_str, checkers):
    try:
        is_email = EMAIL_REGEX.match(query_str)
        if is_email and "check_email" in platform.value.__dict__:
            response = await checkers[platform].check_email(query_str)
            if response is None:
                raise QueryError("Error retrieving result")
            return response
        elif not is_email and "check_username" in platform.value.__dict__:
            response = await checkers[platform].check_username(query_str)
            if response is None:
                raise QueryError("Error retrieving result")
            return response
    except (aiohttp.ClientError, KeyError, QueryError) as e:
        return PlatformResponse(platform=platform,
                                query=query_str,
                                available=False,
                                valid=False,
                                success=False,
                                message=f"{type(e).__name__} - {e}")


async def query_without_checkers(platform, query_str):
    async with aiohttp.ClientSession() as session:
        checkers = {platform: platform.value(session)}
        return await query(platform, query_str, checkers)

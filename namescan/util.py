import aiohttp

from namescan.platforms import Platforms, PlatformResponse


async def init_prerequest(platform, checkers):
    if platform.value.prerequest_req:
        await checkers[platform].get_token()


def init_checkers(session):
    checkers = {}
    for platform in Platforms:
        checkers[platform] = platform.value(session)
    return checkers


async def is_username_available(platform, username, checkers):
    try:
        return await checkers[platform].check_username(username)
    except (aiohttp.ClientError, KeyError) as e:
        response = PlatformResponse(platform, username)
        response.available = response.valid = response.success = False
        response.message = f"{type(e).__name__} - {e}"
        return response

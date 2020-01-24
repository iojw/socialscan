# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import asyncio
import re

import aiohttp

from socialscan.platforms import PlatformResponse, Platforms, QueryError

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,253}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,253}[a-zA-Z0-9])?)+$")


async def init_prerequest(platform, checkers):
    if hasattr(platform.value, "prerequest"):
        await checkers[platform].get_token()


def init_checkers(session, platforms=list(Platforms), proxy_list=[]):
    checkers = {}
    for platform in platforms:
        checkers[platform] = platform.value(session, proxy_list=proxy_list)
    return checkers


async def query(query_, platform, checkers):
    try:
        is_email = EMAIL_REGEX.match(query_)
        if is_email and hasattr(platform.value, "check_email"):
            response = await checkers[platform].check_email(query_)
            if response is None:
                raise QueryError("Error retrieving result")
            return response
        elif not is_email and hasattr(platform.value, "check_username"):
            response = await checkers[platform].check_username(query_)
            if response is None:
                raise QueryError("Error retrieving result")
            return response
    except (aiohttp.ClientError, KeyError, QueryError) as e:
        return PlatformResponse(platform=platform,
                                query=query_,
                                available=False,
                                valid=False,
                                success=False,
                                message=f"{type(e).__name__} - {e}")


async def execute_queries(queries, platforms=list(Platforms), proxy_list=[]):
    """Execute each of the queries on the specified platforms concurrently and return a list of results.

    Args:
        queries (`list` of `str`): List of queries to search.
        platforms (`list` of `Platform` members, optional): List of platforms to execute queries for. Defaults to all platforms.
        proxy_list (`list` of `str`, optional): List of HTTP proxies to execute queries with.

    Returns:
        `list` of `PlatformResponse` objects in the same order as the list of queries and platforms passed.
    """
    async with aiohttp.ClientSession() as session:
        checkers = init_checkers(session, platforms=platforms, proxy_list=proxy_list)
        query_tasks = [query(q, p, checkers) for q in queries for p in platforms]
        results = await asyncio.gather(*query_tasks)
        return [x for x in results if x is not None]


def sync_execute_queries(queries, platforms=list(Platforms), proxy_list=[]):
    """Execute each of the queries on the specified platforms concurrently and return a list of results. Synchronous wrapper around `execute_queries`

    Args:
        queries (`list` of `str`): List of queries to search.
        platforms (`list` of `Platforms` members, optional): List of platforms to execute queries for. Defaults to all platforms.
        proxy_list (`list` of `str`, optional): List of HTTP proxies to execute queries with.

    Returns:
        `list` of `PlatformResponse` objects in the same order as the list of queries and platforms passed.
    """
    return asyncio.run(execute_queries(queries, platforms, proxy_list))

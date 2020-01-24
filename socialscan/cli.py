# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import asyncio
import sys
import time
from collections import defaultdict
from operator import attrgetter

import aiohttp
import colorama
import tqdm
from colorama import Fore, Style

from socialscan import __version__
from socialscan.platforms import Platforms
from socialscan.util import init_checkers, init_prerequest, query

BAR_WIDTH = 50
BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed_s:.2f}s]"

DIVIDER_LENGTH = 40

COLOUR_AVAILABLE = (Fore.LIGHTGREEN_EX, Fore.LIGHTGREEN_EX)
COLOUR_UNAVAILABLE = (Fore.YELLOW, Fore.WHITE)
COLOUR_INVALID = (Fore.CYAN, Fore.WHITE)
COLOUR_ERROR = (Fore.RED, Fore.RED)


async def main():
    start_time = time.time()
    colorama.init(autoreset=True)
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="Command-line interface for checking email address and username usage on online platforms: " + ", ".join(p.value.__name__ for p in Platforms))
    parser.add_argument("queries", metavar="query", nargs="*",
                        help="one or more usernames/email addresses to query (email addresses are automatically be queried if they match the format)")
    parser.add_argument("--platforms", "-p", metavar="platform", nargs="*", help="list of platforms to query "
                                                                                 "(default: all platforms)")
    parser.add_argument("--view-by", dest="view_key", choices=["platform", "query"], default="query", help="view results sorted by platform or by query (default: query)")
    parser.add_argument("--available-only", "-a", action="store_true", help="only print usernames/email addresses that are available and not in use")
    parser.add_argument("--cache-tokens", "-c", action="store_true", help="cache tokens for platforms requiring more than one HTTP request (Snapchat, GitHub, Instagram. Lastfm, Tumblr & Yahoo), reducing total number of requests sent")
    parser.add_argument("--input", "-i", metavar="input.txt",
                        help="file containg list of queries to execute")
    parser.add_argument("--proxy-list", metavar="proxy_list.txt", help="file containing list of HTTP proxy servers to execute queries with")
    parser.add_argument("--verbose", "-v", action="store_true", help="show query responses as they are received")
    parser.add_argument("--version", version=f"%(prog)s {__version__}", action="version")
    args = parser.parse_args()

    queries = args.queries
    if args.input:
        with open(args.input, "r") as f:
            for line in f:
                queries.append(line.strip("\n"))
    if not args.queries:
        raise ValueError("You must specify either at least one query or an input file")
    queries = list(dict.fromkeys(queries))
    if args.platforms:
        platforms = []
        for p in args.platforms:
            if p.upper() in Platforms.__members__:
                platforms.append(Platforms[p.upper()])
            else:
                raise ValueError(p + " is not a valid platform")
    else:
        platforms = [p for p in Platforms]
    proxy_list = []
    if args.proxy_list:
        with open(args.proxy_list, "r") as f:
            for line in f:
                proxy_list.append(line.strip("\n"))
    if args.view_key == "query":
        view_value = "platform"
        key_iter = queries
    elif args.view_key == "platform":
        view_value = "query"
        key_iter = Platforms

    async with aiohttp.ClientSession() as session:
        checkers = init_checkers(session, proxy_list=proxy_list)
        all_results = defaultdict(list)
        result_count = 0

        if args.cache_tokens:
            print("Caching tokens...", end="")
            await asyncio.gather(*(init_prerequest(platform, checkers) for platform in platforms))
            print(end="\r")
        platform_queries = [query(q, p, checkers) for q in queries for p in platforms]
        for future in tqdm.tqdm(asyncio.as_completed(platform_queries), total=len(platform_queries), disable=args.verbose, leave=False, ncols=BAR_WIDTH, bar_format=BAR_FORMAT):
            platform_response = await future
            if platform_response and args.verbose:
                print(f"Checked {platform_response.query: ^25} on {platform_response.platform.value.__name__:<10}: {platform_response.message}")
            if platform_response and (args.available_only and platform_response.available or not args.available_only):
                all_results[getattr(platform_response, args.view_key)].append(platform_response)
        if args.verbose:
            print()
        for key in key_iter:
            responses = all_results[key]
            result_count += len(responses)
            header = (f"{'-' * DIVIDER_LENGTH}\n"
                      f"{' ' * (DIVIDER_LENGTH // 2 - len(key) // 2) + Style.BRIGHT + str(key) + Style.RESET_ALL}\n"
                      f"{'-' * DIVIDER_LENGTH}")
            if not (args.available_only and responses == [] or args.view_key == "platform" and responses == []):
                print(header)
            responses.sort(key=lambda platform_response: str(getattr(platform_response, view_value)).lower())
            responses.sort(key=attrgetter('available', 'valid', "success"), reverse=True)
            for platform_response in responses:
                value = getattr(platform_response, view_value)
                if not platform_response.success:
                    print(COLOUR_ERROR[0] + f"{value}: {platform_response.message}", file=sys.stderr)
                else:
                    if platform_response.available:
                        col = COLOUR_AVAILABLE
                    elif not platform_response.valid:
                        col = COLOUR_INVALID
                    else:
                        col = COLOUR_UNAVAILABLE
                    result_text = f"{col[0]}{value}"
                    if not platform_response.valid:
                        result_text += f": {col[1]}{platform_response.message}"
                    print(result_text)

    print("\n" + COLOUR_AVAILABLE[0] + "Available, ", end="")
    print(COLOUR_UNAVAILABLE[0] + "Taken/Reserved, ", end="")
    print(COLOUR_INVALID[0] + "Invalid, ", end="")
    print(COLOUR_ERROR[0] + "Error")
    print("Completed {} queries in {:.2f}s".format(result_count, time.time() - start_time))

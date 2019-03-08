#! /usr/bin/env python
import asyncio
import argparse
import sys
import time
from collections import defaultdict
from operator import attrgetter

import aiohttp
from colorama import Fore, Back, Style, init
import tqdm

from socialscan import util
from socialscan.platforms import Platforms

BAR_WIDTH = 50
BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed_s:.2f}s]"
TIMEOUT_PER_QUERY = 1
CLEAR_LINE = "\x1b[2K"
DIVIDER = "-"
DIVIDER_LENGTH = 40


async def main():
    startTime = time.time()
    init(autoreset=True)
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="Command-line interface for checking username and email address usage on online platforms: " + ", ".join(p.value.__name__ for p in Platforms))
    parser.add_argument("queries", metavar="query", nargs="*",
                        help="one or more usernames/email addresses to query (email addresses are automatically be queried if they match the format)")
    parser.add_argument("--platforms", "-p", metavar="platform", nargs="*", help="list of platforms to query "
                                                                                 "(default: all platforms)")
    parser.add_argument("--input", "-i", metavar="input.txt",
                        help="input file from which to read in queries, one per line")
    parser.add_argument("--cache-tokens", "-c", action="store_true", help="cache tokens for platforms requiring more than one HTTP request (Snapchat, GitHub, Instagram & Tumblr) "
                        "marginally increases runtime but halves number of requests")
    parser.add_argument("--available-only", "-a", action="store_true", help="only print usernames/email addresses that are available")
    parser.add_argument("--verbose", "-v", action="store_true", help="show response messages for all queries, even if available or unavailable")
    args = parser.parse_args()

    queries = args.queries
    if args.input:
        with open(args.input, "r") as f:
            for line in f:
                queries.append(line.strip("\n"))
    if not args.queries:
        raise ValueError("you must specify either at least one query or an input file")
    if args.platforms:
        platforms = []
        for p in args.platforms:
            if p.upper() in Platforms.__members__:
                platforms.append(Platforms[p.upper()])
            else:
                raise ValueError(p + " is not a valid platform")
    else:
        platforms = [p for p in Platforms]
    queries = list(dict.fromkeys(queries))

    async with aiohttp.ClientSession() as session:
        checkers = util.init_checkers(session)

        if args.cache_tokens:
            print("Caching tokens...", end="")
            await asyncio.gather(*(util.init_prerequest(platform, checkers) for platform in platforms))
            print(CLEAR_LINE, end="")
        platform_queries = [util.query(p, query, checkers) for query in queries for p in platforms]
        results = defaultdict(list)
        exceptions = []
        for future in tqdm.tqdm(asyncio.as_completed(platform_queries), total=len(platform_queries), leave=False, ncols=BAR_WIDTH, bar_format=BAR_FORMAT):
            response = await future
            if response and (args.available_only and response.available or not args.available_only):
                results[response.query].append(response)
        for query in queries:
            responses = results[query]
            print(DIVIDER * DIVIDER_LENGTH)
            print(" " * (DIVIDER_LENGTH // 2 - len(query) // 2) + Style.BRIGHT + query)
            print(DIVIDER * DIVIDER_LENGTH)
            responses.sort(key=attrgetter('platform.name'))
            responses.sort(key=attrgetter('available', 'valid', "success"), reverse=True)
            for response in responses:
                if not response.success:
                    col = Fore.RED
                    print(col + f"{response.platform.value.__name__}: {response.message}", file=sys.stderr)
                else:
                    if response.available:
                        name_col = message_col = Fore.LIGHTGREEN_EX
                    elif not response.valid:
                        name_col = Fore.CYAN
                        message_col = Fore.WHITE
                    else:
                        name_col = Fore.YELLOW
                        message_col = Fore.WHITE
                    print(name_col + f"{response.platform.value.__name__}", end="")
                    print(name_col + ": " + message_col + f"{response.message}" if not response.valid or args.verbose else "")

    print(*exceptions, sep="\n", file=sys.stderr)
    print(Fore.GREEN + "Available, ", end="")
    print(Fore.YELLOW + "Unavailable, ", end="")
    print(Fore.CYAN + "Invalid, ", end="")
    print(Fore.RED + "Error")
    print("Completed {} queries in {:.2f}s".format(len(platform_queries), time.time() - startTime))

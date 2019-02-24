#! /usr/bin/env python
import asyncio
import argparse
import sys
import time
from collections import defaultdict

import aiohttp
import colorama
import tqdm

from namescanner import util
from namescanner.platforms import Platforms

BAR_WIDTH = 50
BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed_s:.2f}s]"
TIMEOUT_PER_QUERY = 1
CLEAR_LINE = "\x1b[2K"
DIVIDER = "-"


async def main():
    startTime = time.time()
    colorama.init(autoreset=True)
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="Command-line interface for querying username availability on online platforms: " + ", ".join(p.name.capitalize() for p in Platforms))
    parser.add_argument("usernames", metavar="username", nargs="*",
                        help="list of usernames to query")
    parser.add_argument("-r", "--restrict", metavar="platform", nargs="*", help="restrict list of platforms to query "
                                                                                "(default: all platforms)")
    parser.add_argument("-i", "--input-file", metavar="filename.txt",
                        help="file from which to read in usernames, one per line")
    parser.add_argument("-c", "--cache-tokens", action="store_true", help="cache tokens for platforms requiring more than one HTTP request (Snapchat, GitHub, Instagram & Tumblr) "
                        "marginally increases runtime but halves number of requests")
    parser.add_argument("-a", "--available-only", action="store_true", help="only print usernames that are available")
    args = parser.parse_args()

    usernames = args.usernames
    if args.input_file:
        with open(args.input, "r") as f:
            for line in f:
                usernames.append(line.strip("\n"))
    if not args.usernames:
        raise ValueError("you must specify either a username or an input file")
    if args.restrict:
        platforms = []
        for p in args.restrict:
            if p.upper() in Platforms.__members__:
                platforms.append(Platforms[p.upper()])
            else:
                raise ValueError(p + " is not a valid platform")
    else:
        platforms = [p for p in Platforms]
    usernames = list(dict.fromkeys(usernames))

    async with aiohttp.ClientSession() as session:
        if args.cache_tokens:
            print("Caching tokens...", end="")
            await asyncio.gather(*(util.prerequest(platform, session) for platform in platforms))
            print(CLEAR_LINE, end="")
        platform_queries = [util.is_username_available(i, username, session) for username in usernames for i in platforms]
        results = defaultdict(list)
        exceptions = []
        for future in tqdm.tqdm(asyncio.as_completed(platform_queries), total=len(platform_queries), leave=False, ncols=BAR_WIDTH, bar_format=BAR_FORMAT):
            try:
                response = await future
                if args.available_only and response.valid or not args.available_only:
                    results[response.username].append(response)
            # Catch only networking errors and errors in JSON handling
            except (aiohttp.ClientError, KeyError) as e:
                exceptions.append(colorama.Back.RED + f"{type(e).__name__}: {e}")
        for username, responses in results.items():
            print(DIVIDER * (len(username)))
            print(username)
            print(DIVIDER * (len(username)))
            for response in responses:
                if not response.success:
                    fore = colorama.Fore.YELLOW
                elif response.valid:
                    fore = colorama.Fore.GREEN
                else:
                    fore = colorama.Fore.RED
                print(fore + f"{response.platform.name.capitalize()}", end="")
                print(f": {response.message}" if not response.valid else "")
    print(*exceptions, sep="\n", file=sys.stderr)
    print("Completed {} queries in {:.2f}s".format(len(platform_queries), time.time() - startTime))

if __name__ == "__main__":
    asyncio.run(main())

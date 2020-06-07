# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import asyncio
import json
import sys
import time
from collections import namedtuple, defaultdict
from dataclasses import asdict
from operator import attrgetter

import aiohttp
import colorama
import tqdm
from colorama import Fore, Style

from socialscan import __version__
from socialscan.platforms import PlatformResponse, Platforms
from socialscan.util import init_checkers, init_prerequest, query

BAR_WIDTH = 50
BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed_s:.2f}s]"

DIVIDER_LENGTH = 40

Colour = namedtuple("Colour", ["Primary", "Secondary"])
COLOUR_AVAILABLE = Colour(Fore.LIGHTGREEN_EX, Fore.LIGHTGREEN_EX)
COLOUR_UNAVAILABLE = Colour(Fore.YELLOW, Fore.WHITE)
COLOUR_INVALID = Colour(Fore.CYAN, Fore.WHITE)
COLOUR_ERROR = Colour(Fore.RED, Fore.RED)


def init_parser():
    parser = argparse.ArgumentParser(
        description="Command-line interface for checking email address and username usage on online platforms: "
        + ", ".join(p.value.__name__ for p in Platforms)
    )
    parser.add_argument(
        "queries",
        metavar="query",
        nargs="*",
        help="one or more usernames/email addresses to query (email addresses are automatically be queried if they match the format)",
    )
    parser.add_argument(
        "--platforms",
        "-p",
        metavar="platform",
        nargs="*",
        help="list of platforms to query " "(default: all platforms)",
    )
    parser.add_argument(
        "--view-by",
        dest="view_key",
        choices=["platform", "query"],
        default="query",
        help="view results sorted by platform or by query (default: query)",
    )
    parser.add_argument(
        "--available-only",
        "-a",
        action="store_true",
        help="only print usernames/email addresses that are available and not in use",
    )
    parser.add_argument(
        "--cache-tokens",
        "-c",
        action="store_true",
        help="cache tokens for platforms requiring more than one HTTP request (Snapchat, GitHub, Instagram. Lastfm, Tumblr & Yahoo), reducing total number of requests sent",
    )
    parser.add_argument(
        "--input", "-i", metavar="input.txt", help="file containg list of queries to execute"
    )
    parser.add_argument(
        "--proxy-list",
        metavar="proxy_list.txt",
        help="file containing list of HTTP proxy servers to execute queries with",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="show query responses as they are received"
    )
    parser.add_argument(
        "--show-urls",
        action="store_true",
        help="display profile URLs for usernames on supported platforms (profiles may not exist if usernames are reserved or belong to deleted/banned accounts)",
    )
    parser.add_argument(
        "--json", metavar="json.txt", help="output results in JSON format to the specified file",
    )
    parser.add_argument("--version", version=f"%(prog)s {__version__}", action="version")
    return parser


def pretty_print(results, *, view_value, available_only, show_urls):
    for key, responses in results.items():
        if available_only and not [r for r in responses if r.available]:
            continue

        header = (
            f"{'-' * DIVIDER_LENGTH}\n"
            f"{' ' * (DIVIDER_LENGTH // 2 - len(key) // 2) + Style.BRIGHT + str(key) + Style.RESET_ALL}\n"
            f"{'-' * DIVIDER_LENGTH}"
        )
        print(header)

        responses.sort(key=lambda response: str(getattr(response, view_value)).lower())
        responses.sort(key=attrgetter("available", "valid", "success"), reverse=True)
        for response in responses:
            value = str(getattr(response, view_value))
            if available_only and not response.available:
                continue
            if not response.success:
                print(COLOUR_ERROR.Primary + f"{value}: {response.message}", file=sys.stderr)
            elif not response.valid:
                print(
                    COLOUR_INVALID.Primary
                    + f"{value}: {COLOUR_INVALID.Secondary}{response.message}"
                )
            else:
                col = COLOUR_AVAILABLE if response.available else COLOUR_UNAVAILABLE
                result_text = col.Primary + value
                if response.link and show_urls:
                    result_text += col.Secondary + f" - {response.link}"
                print(result_text)

    print("\n" + COLOUR_AVAILABLE.Primary + "Available, ", end="")
    print(COLOUR_UNAVAILABLE.Primary + "Taken/Reserved, ", end="")
    print(COLOUR_INVALID.Primary + "Invalid, ", end="")
    print(COLOUR_ERROR.Primary + "Error")


def print_json(results, *, file, available_only):
    if available_only:
        results = {key: [v for v in values if v.available] for key, values in results.items()}

    def serialize(obj):
        if isinstance(obj, PlatformResponse):
            # Omit None and convert Platform objects to str
            return asdict(
                obj,
                dict_factory=lambda data: dict(
                    [(x[0], str(x[1])) for x in data if x[1] is not None]
                ),
            )

    with open(file, "w") as f:
        f.write(json.dumps(results, default=serialize, indent=4))


async def main():
    start_time = time.time()
    colorama.init(autoreset=True)
    if sys.version_info >= (3, 7):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = init_parser()
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
    elif args.view_key == "platform":
        view_value = "query"

    async with aiohttp.ClientSession() as session:
        checkers = init_checkers(session, proxy_list=proxy_list)
        results = defaultdict(list)
        if args.cache_tokens:
            print("Caching tokens...", end="")
            await asyncio.gather(*(init_prerequest(platform, checkers) for platform in platforms))
            print(end="\r")
        platform_queries = [query(q, p, checkers) for q in queries for p in platforms]
        for future in tqdm.tqdm(
            asyncio.as_completed(platform_queries),
            total=len(platform_queries),
            disable=args.verbose,
            leave=False,
            ncols=BAR_WIDTH,
            bar_format=BAR_FORMAT,
        ):
            platform_response = await future
            if platform_response is None:
                continue
            if args.verbose:
                print(platform_response, getattr(platform_response, args.view_key))
                print(
                    f"Checked {platform_response.query: ^25} on {platform_response.platform.value.__name__:<10}: {platform_response.message}"
                )
            results[str(getattr(platform_response, args.view_key))].append(platform_response)

    if args.json:
        print_json(results, file=args.json, available_only=args.available_only)
    else:
        pretty_print(
            results,
            view_value=view_value,
            available_only=args.available_only,
            show_urls=args.show_urls,
        )
    print(f"Completed {len(platform_queries)} queries in {time.time() - start_time:.2f}s")

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import asyncio
import sys

from socialscan import cli


def main():
    # To avoid 'Event loop is closed' RuntimeError due to compatibility issue with aiohttp
    if sys.platform.startswith("win") and sys.version_info >= (3, 8):
        try:
            from asyncio import WindowsSelectorEventLoopPolicy
        except ImportError:
            pass
        else:
            if not isinstance(asyncio.get_event_loop_policy(), WindowsSelectorEventLoopPolicy):
                asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    asyncio.run(cli.main())


if __name__ == "__main__":
    main()

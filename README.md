# socialscan
[![Build Status](https://travis-ci.com/iojw/socialscan.svg?token=4yLRbSuqAQqrjanbzeXs&branch=master)](https://travis-ci.com/iojw/socialscan)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/downloads/)

socialscan offers **accurate** and **fast** checks for email address and username usage on online platforms.  

Given an email address or username, socialscan returns whether it is available, taken or invalid on online platforms. Its speed also makes it suitable for bulk queries involving hundreds of usernames and email addresses.

The following platforms are currently supported:   

|           | Username | Email |
|:---------:|:--------:|:--------:|
| Instagram |     ✔️    |   ✔️   |
| Twitter   |     ✔️    |   ✔️   |
|  GitHub   |     ✔️    |   ✔️   |
|   Tumblr  |     ✔️    |   ✔️   |
|  Lastfm  |     ✔️    |   ✔️   |
|  Snapchat |     ✔️    |         |
| GitLab    |     ✔️    |         |
| Reddit    |     ✔️    |         |
| Pinterest |            |   ✔️   |
|  Spotify  |            |   ✔️   |

<p>
<img src="https://github.com/iojw/socialscan/raw/master/demo/demo.gif" width="700" height="469"/>
<img src="https://github.com/iojw/socialscan/raw/master/demo/demo100.gif" width="700" height="469"/>
</p>

## Background

Other similar tools check username availability by requesting the profile page of the username in question and based on information like the HTTP status code or error text on the requested page, determine whether a username is already taken. This is a naive approach that fails in the following cases:

- Reserved keywords: Most platforms have a set of keywords that they don't allow to be used in usernames  
(A simple test: try checking reserved words like 'admin' or 'home' or 'root' and see if other services mark them as available)

- Deleted/banned accounts: Deleted/banned account usernames tend to be unavailable even though the profile pages might not exist

Therefore, these tools tend to come up with false positives and negatives. This method of checking also cannot be extended to email addresses or platforms which don't use traditional profile pages.

socialscan aims to plug these gaps.

## Features

1. **100% accuracy**: Rather than scanning profile pages, socialscan queries the registration servers of the platforms directly, retrieving the appropriate CSRF tokens, headers, and cookies. This eliminates all false positives/negatives, ensuring that results are accurate.

2. **Speed**: socialscan uses [asyncio](https://docs.python.org/3/library/asyncio.html) along with [aiohttp](https://aiohttp.readthedocs.io/en/stable/) to conduct all queries concurrently, resulting in very quick searching even with bulk queries.

## Installation

### pip
```
> pip install socialscan
```

### Install from source
```
> git clone https://github.com/iojw/socialscan.git  
> cd socialscan  
> pip install .
```

## Usage
```
usage: socialscan [list of usernames/email addresses to check]

optional arguments:
  -h, --help            show this help message and exit
  --platforms [platform [platform ...]], -p [platform [platform ...]]
                        list of platforms to query (default: all platforms)
  --view-by {platform,query}
                        view results sorted by platform or by query (default:
                        query)
  --available-only, -a  only print usernames/email addresses that are
                        available and not in use
  --cache-tokens, -c    cache tokens for platforms requiring more than one
                        HTTP request (Snapchat, GitHub, Instagram. Lastfm &
                        Tumblr), reducing total number of requests sent
  --input input.txt, -i input.txt
                        file containg list of queries to execute
  --proxy-list proxy_list.txt
                        file containing list of HTTP proxy servers to execute
                        queries with
  --verbose, -v         show query responses as they are received
  --version             show program's version number and exit
```

## As a library

socialscan can also be imported into existing code and used as a library.


Executing single queries:
```python
import asyncio

from socialscan.util import Platforms, query_without_checkers

result = asyncio.run(query_without_checkers(Platforms.GITHUB, "username1"))
print(f"Success: {result.success}, Valid: {result.valid}, Available: {result.available}")
```
Executing multiple queries concurrently requires a bit more setup:
```python
import asyncio
import aiohttp
from socialscan.util import Platforms, init_checkers, query

async def execute_queries():
    async with aiohttp.ClientSession() as session:
        checkers = init_checkers(session)
        platforms = [Platforms.GITHUB, Platforms.LASTFM]
        queries = ["username1", "email2@gmail.com", "email3@me.com"]
        query_tasks = [query(p, q, checkers) for q in queries for p in platforms]
        results = await asyncio.gather(*query_tasks)
        for result in results:
            print(f"{result.query} on {result.platform.name}: Success: {result.success}, Valid: {result.valid}, Available: {result.available}")

asyncio.run(execute_queries())
```
## Contributing

Errors, suggestions or want a site added? [Submit an issue](https://github.com/iojw/socialscan/issues). 

PRs are always welcome 🙂

## License
MIT
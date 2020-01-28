# socialscan
[![Build Status](https://travis-ci.com/iojw/socialscan.svg?token=4yLRbSuqAQqrjanbzeXs&branch=master)](https://travis-ci.com/iojw/socialscan)
[![Downloads](https://pepy.tech/badge/socialscan/month)](https://pepy.tech/project/socialscan/month)
[![MPL 2.0 license](https://img.shields.io/badge/License-MPL%202.0-blue.svg)](https://www.mozilla.org/en-US/MPL/2.0/)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/downloads/)

socialscan offers **accurate** and **fast** checks for email address and username usage on online platforms.  

Given an email address or username, socialscan returns whether it is available, taken or invalid on online platforms. 

Features that differentiate socialscan from similar tools (e.g. knowem.com, Namechk, and Sherlock):

1. **100% accuracy**: socialscan's query method eliminates the false positives and negatives that often occur in similar tools, ensuring that results are always accurate.

2. **Speed**: socialscan uses [asyncio](https://docs.python.org/3/library/asyncio.html) along with [aiohttp](https://aiohttp.readthedocs.io/en/stable/) to conduct all queries concurrently, providing fast searches even with bulk queries involving hundreds of usernames and email addresses. On a test computer with average specs and Internet speed, 100 queries were executed in ~4 seconds.

3. **Library / CLI**: socialscan can be executed through a CLI, or imported as a Python library to be used with existing code.

4. **Email support**: socialscan supports queries for both email addresses and usernames.

The following platforms are currently supported:   

|           | Username | Email |
|:---------:|:--------:|:--------:|
| Instagram |     ✔️    |   ✔️   |
| Twitter   |     ✔️    |   ✔️   |
|  GitHub   |     ✔️    |   ✔️   |
|   Tumblr  |     ✔️    |   ✔️   |
|  Lastfm   |     ✔️    |   ✔️   |
|  Snapchat |     ✔️    |        |
| GitLab    |     ✔️    |        |
| Reddit    |     ✔️    |        |
|  Yahoo    |     ✔️    |        |
| Pinterest |            |   ✔️  |
|  Spotify  |            |   ✔️  |

![](https://github.com/iojw/socialscan/raw/master/demo/demo.gif)
![](https://github.com/iojw/socialscan/raw/master/demo/demo100.gif)

## Background

Other similar tools check username availability by requesting the profile page of the username in question and based on information like the HTTP status code or error text on the requested page, determine whether a username is already taken. This is a naive approach that fails in the following cases:

- Reserved keywords: Most platforms have a set of keywords that they don't allow to be used in usernames  
(A simple test: try checking reserved words like 'admin' or 'home' or 'root' and see if other services mark them as available)

- Deleted/banned accounts: Deleted/banned account usernames tend to be unavailable even though the profile pages might not exist

Therefore, these tools tend to come up with false positives and negatives. This method of checking is also dependent on platforms having web-based profile pages and cannot be extended to email addresses.

socialscan aims to plug these gaps by directly querying the registration servers of the platforms instead, retrieving the appropriate CSRF tokens, headers, and cookies. 

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

v1.0.0 introduces the async method `execute_queries` and the corresponding synchronous wrapper `sync_execute_queries` that takes a list of queries and optional list of platforms and proxies, executing all queries concurrently. The method then returns a list of results in the same order.

```python
from socialscan.util import Platforms, sync_execute_queries

queries = ["username1", "email2@gmail.com", "mail42@me.com"]
platforms = [Platforms.GITHUB, Platforms.LASTFM]
results = sync_execute_queries(queries, platforms)
for result in results:
    print(f"{result.query} on {result.platform}: {result.message} (Success: {result.success}, Valid: {result.valid}, Available: {result.available})")
```
Output:
```
username1 on GitHub: Username is already taken (Success: True, Valid: True, Available: False)
username1 on Lastfm: Sorry, this username isn't available. (Success: True, Valid: True, Available: False)
email2@gmail.com on GitHub: Available (Success: True, Valid: True, Available: True)
email2@gmail.com on Lastfm: Sorry, that email address is already registered to another account. (Success: True, Valid: True, Available: False)
mail42@me.com on GitHub: Available (Success: True, Valid: True, Available: True)
mail42@me.com on Lastfm: Looking good! (Success: True, Valid: True, Available: True)
```

## Text file input
For bulk queries with the `--input` option, place one username/email on each line in the .txt file:
```
username1
email2@mail.com
username3
```

## Contributing
Errors, suggestions or want a site added? [Submit an issue](https://github.com/iojw/socialscan/issues). 

PRs are always welcome 🙂

## License
MPL 2.0

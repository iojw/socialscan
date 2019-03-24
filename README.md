# socialscan
[![Build Status](https://travis-ci.com/iojw/socialscan.svg?token=4yLRbSuqAQqrjanbzeXs&branch=master)](https://travis-ci.com/iojw/socialscan)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/downloads/)

socialscan offers **accurate** and **fast** checks for email address and username usage on online platforms. Given an email address or username, socialscan returns whether it is available, taken or invalid on online platforms. Its speed also makes it suitable for bulk queries involving hundreds of usernames and email addresses (with a proxy).

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

<br/>
<a href="https://asciinema.org/a/N3SDS7krILW0YA6NisLxrxqkV">
<img src="https://github.com/iojw/socialscan/raw/master/demo/demo.gif" width="904" height="492"/>
</a>

## Background

Other similar tools check username availability by requesting the profile page of the username in question and based on information like the HTTP status code or error text on the requested page, determine whether a username is already taken. This is a naive approach that fails in the following cases:

- Reserved keywords: Most platforms have a set of keywords that they don't allow to be used in usernames  
(A simple test: try checking reserved words like 'admin' or 'home' or 'root' and see if other services mark them as available.)

- Deleted/banned accounts: Deleted/banned account usernames tend to be unavailable even though the profile pages might not exist

These tools therefore tend to come up with false positives and negatives. This method of checking also cannot be extended to email addresses.

socialscan's implementation solves these problems, while also adding support for email addresses.

## Features

1. **100% accuracy**: Rather than scanning profile pages, socialscan queries the registration servers of the platforms directly, retrieving the appropriate CSRF tokens, headers, and cookies. This eliminates all false positives/negatives, ensuring that results are accurate.

2. **Speed**: socialscan uses [asyncio](https://docs.python.org/3/library/asyncio.html) along with [aiohttp](https://aiohttp.readthedocs.io/en/stable/) to conduct all queries concurrently, resulting in very quick searching even with bulk queries

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
  --input input.txt, -i input.txt
                        file containg list of queries to execute
  --cache-tokens, -c    cache tokens for platforms requiring more than one
                        HTTP request - this marginally increases runtime 
                        but halves the total number of requests for bulk queries
  --available-only, -a  only print usernames/email addresses that are
                        available and not in use
  --verbose, -v         show response messages for all queries regardless of
                        result
  --proxy-list proxy_list.txt
                        file containing list of proxy servers to execute
                        queries with (useful for bypassing rate limits set by
                        platforms)
  --version             show program's version number and exit
```

## Contributing

Errors, suggestions or want a site added? [Submit an issue](https://github.com/iojw/socialscan/issues). 

PRs are always welcome 🙂

## License
MIT
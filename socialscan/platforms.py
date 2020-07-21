# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
from dataclasses import dataclass
from enum import Enum

import aiohttp

from socialscan import __version__


class QueryError(Exception):
    pass


class PlatformChecker:
    DEFAULT_HEADERS = {
        "User-agent": f"socialscan {__version__}",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    }
    UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE = "Unexpected content type {}. You might be sending too many requests. Use a proxy or wait before trying again."
    TOKEN_ERROR_MESSAGE = "Could not retrieve token. You might be sending too many requests. Use a proxy or wait before trying again."
    TOO_MANY_REQUEST_ERROR_MESSAGE = "Requests denied by platform due to excessive requests. Use a proxy or wait before trying again."
    TIMEOUT_DURATION = 15

    client_timeout = aiohttp.ClientTimeout(connect=TIMEOUT_DURATION)

    # Subclasses can implement 3 methods depending on requirements: prerequest(), check_username() and check_email()
    # 1: Be as explicit as possible in handling all cases
    # 2: Do not include any queries that will lead to side-effects on users (e.g. submitting sign up forms)
    # OK to omit checks for whether a key exists when parsing the JSON response. KeyError is handled by the parent coroutine.

    async def get_token(self):
        """
        Retrieve and return platform token using the `prerequest` method specified in the class

        Normal calls will not be able to take advantage of this as all tokens are retrieved concurrently
        This only applies to when tokens are retrieved before main queries with -c
        Adds 1-2s to overall running time but halves HTTP requests sent for bulk queries
        """
        if self.prerequest_sent:
            if self.token is None:
                raise QueryError(PlatformChecker.TOKEN_ERROR_MESSAGE)
            return self.token
        else:
            self.token = await self.prerequest()
            self.prerequest_sent = True
            if self.token is None:
                raise QueryError(PlatformChecker.TOKEN_ERROR_MESSAGE)
            return self.token

    def response_failure(self, query, *, message="Failure"):
        return PlatformResponse(
            platform=Platforms(self.__class__),
            query=query,
            available=False,
            valid=False,
            success=False,
            message=message,
            link=None,
        )

    def response_available(self, query, *, message="Available"):
        return PlatformResponse(
            platform=Platforms(self.__class__),
            query=query,
            available=True,
            valid=True,
            success=True,
            message=message,
            link=None,
        )

    def response_unavailable(self, query, *, message="Unavailable", link=None):
        return PlatformResponse(
            platform=Platforms(self.__class__),
            query=query,
            available=False,
            valid=True,
            success=True,
            message=message,
            link=link,
        )

    def response_invalid(self, query, *, message="Invalid"):
        return PlatformResponse(
            platform=Platforms(self.__class__),
            query=query,
            available=False,
            valid=False,
            success=True,
            message=message,
            link=None,
        )

    def response_unavailable_or_invalid(self, query, *, message, unavailable_messages, link=None):
        if any(x in message for x in unavailable_messages):
            return self.response_unavailable(query, message=message, link=link)
        else:
            return self.response_invalid(query, message=message)

    def _request(self, method, url, **kwargs):
        proxy = (
            self.proxy_list[self.request_count % len(self.proxy_list)] if self.proxy_list else None
        )
        self.request_count += 1
        if "headers" in kwargs:
            kwargs["headers"].update(PlatformChecker.DEFAULT_HEADERS)
        else:
            kwargs["headers"] = PlatformChecker.DEFAULT_HEADERS
        return self.session.request(method, url, timeout=self.client_timeout, proxy=proxy, **kwargs)

    def post(self, url, **kwargs):
        return self._request("POST", url, **kwargs)

    def get(self, url, **kwargs):
        return self._request("GET", url, **kwargs)

    @staticmethod
    async def get_json(request):
        if not request.headers["Content-Type"].startswith("application/json"):
            raise QueryError(
                PlatformChecker.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE.format(
                    request.headers["Content-Type"]
                )
            )
        else:
            return await request.json()

    def __init__(self, session, proxy_list=[]):
        self.session = session
        self.proxy_list = proxy_list
        self.request_count = 0
        self.prerequest_sent = False
        self.token = None


class Snapchat(PlatformChecker):
    URL = "https://accounts.snapchat.com/accounts/login"
    ENDPOINT = "https://accounts.snapchat.com/accounts/get_username_suggestions"
    USERNAME_TAKEN_MSGS = ["is already taken", "is currently unavailable"]

    async def prerequest(self):
        async with self.get(Snapchat.URL) as r:
            """
            See: https://github.com/aio-libs/aiohttp/issues/3002
            Snapchat sends multiple Set-Cookie headers in its response setting the value of 'xsrf-token',
            causing the original value of 'xsrf-token' to be overwritten in aiohttp
            Need to analyse the header response to extract the required value
            """
            cookies = r.headers.getall("Set-Cookie")
            for cookie in cookies:
                match = re.search(r"xsrf_token=([\w-]*);", cookie)
                if match:
                    token = match.group(1)
                    return token

    async def check_username(self, username):
        token = await self.get_token()
        async with self.post(
            Snapchat.ENDPOINT,
            data={"requested_username": username, "xsrf_token": token},
            cookies={"xsrf_token": token},
        ) as r:
            # Non-JSON received if too many requests
            json_body = await self.get_json(r)
            if "error_message" in json_body["reference"]:
                return self.response_unavailable_or_invalid(
                    username,
                    message=json_body["reference"]["error_message"],
                    unavailable_messages=Snapchat.USERNAME_TAKEN_MSGS,
                )
            elif json_body["reference"]["status_code"] == "OK":
                return self.response_available(username)

    # Email: Snapchat doesn't associate email addresses with accounts


class Instagram(PlatformChecker):
    URL = "https://instagram.com"
    ENDPOINT = "https://www.instagram.com/accounts/web_create_ajax/attempt/"
    USERNAME_TAKEN_MSGS = [
        "This username isn't available.",
        "A user with that username already exists.",
    ]
    USERNAME_LINK_FORMAT = "https://www.instagram.com/{}"

    async def prerequest(self):
        async with self.get(Instagram.URL) as r:
            if "csrftoken" in r.cookies:
                token = r.cookies["csrftoken"].value
                return token

    async def check_username(self, username):
        token = await self.get_token()
        async with self.post(
            Instagram.ENDPOINT, data={"username": username}, headers={"x-csrftoken": token}
        ) as r:
            json_body = await self.get_json(r)
            # Too many requests
            if json_body["status"] == "fail":
                return self.response_failure(username, message=json_body["message"])
            if "username" in json_body["errors"]:
                return self.response_unavailable_or_invalid(
                    username,
                    message=json_body["errors"]["username"][0]["message"],
                    unavailable_messages=Instagram.USERNAME_TAKEN_MSGS,
                    link=Instagram.USERNAME_LINK_FORMAT.format(username),
                )
            else:
                return self.response_available(username)

    async def check_email(self, email):
        token = await self.get_token()
        async with self.post(
            Instagram.ENDPOINT, data={"email": email}, headers={"x-csrftoken": token}
        ) as r:
            json_body = await self.get_json(r)
            # Too many requests
            if json_body["status"] == "fail":
                return self.response_failure(email, message=json_body["message"])
            if "email" not in json_body["errors"]:
                return self.response_available(email)
            else:
                message = json_body["errors"]["email"][0]["message"]
                if json_body["errors"]["email"][0]["code"] == "invalid_email":
                    return self.response_invalid(email, message=message)
                else:
                    return self.response_unavailable(email, message=message)


class GitHub(PlatformChecker):
    URL = "https://github.com/join"
    USERNAME_ENDPOINT = "https://github.com/signup_check/username"
    EMAIL_ENDPOINT = "https://github.com/signup_check/email"
    # [username taken, reserved keyword (Username __ is unavailable)]
    USERNAME_TAKEN_MSGS = ["already taken", "unavailable", "not available"]
    USERNAME_LINK_FORMAT = "https://github.com/{}"

    token_regex = re.compile(
        r'<auto-check src="/signup_check/username[\s\S]*?value="([\S]+)"[\s\S]*<auto-check src="/signup_check/email[\s\S]*?value="([\S]+)"'
    )
    tag_regex = re.compile(r"<[^>]+>")

    async def prerequest(self):
        async with self.get(GitHub.URL) as r:
            text = await r.text()
            match = self.token_regex.search(text)
            if match:
                username_token = match.group(1)
                email_token = match.group(2)
                return (username_token, email_token)

    async def check_username(self, username):
        pr = await self.get_token()
        (username_token, _) = pr
        async with self.post(
            GitHub.USERNAME_ENDPOINT,
            data={"value": username, "authenticity_token": username_token},
        ) as r:
            if r.status == 422:
                text = await r.text()
                text = self.tag_regex.sub("", text).strip()
                return self.response_unavailable_or_invalid(
                    username,
                    message=text,
                    unavailable_messages=GitHub.USERNAME_TAKEN_MSGS,
                    link=GitHub.USERNAME_LINK_FORMAT.format(username),
                )
            elif r.status == 200:
                return self.response_available(username)
            elif r.status == 429:
                return self.response_failure(
                    username, message=PlatformChecker.TOO_MANY_REQUEST_ERROR_MESSAGE
                )

    async def check_email(self, email):
        pr = await self.get_token()
        if pr is None:
            return self.response_failure(email, message=PlatformChecker.TOKEN_ERROR_MESSAGE)
        else:
            (_, email_token) = pr
        async with self.post(
            GitHub.EMAIL_ENDPOINT, data={"value": email, "authenticity_token": email_token},
        ) as r:
            if r.status == 422:
                text = await r.text()
                return self.response_unavailable(email, message=text)
            elif r.status == 200:
                return self.response_available(email)
            elif r.status == 429:
                return self.response_failure(
                    email, message=PlatformChecker.TOO_MANY_REQUEST_ERROR_MESSAGE
                )


class Tumblr(PlatformChecker):
    URL = "https://tumblr.com/register"
    ENDPOINT = "https://www.tumblr.com/svc/account/register"
    USERNAME_TAKEN_MSGS = [
        "That's a good one, but it's taken",
        "Someone beat you to that username",
        "Try something else, that one is spoken for",
    ]
    USERNAME_LINK_FORMAT = "https://{}.tumblr.com"

    SAMPLE_UNUSED_EMAIL = "akc2rW33AuSqQWY8@gmail.com"
    SAMPLE_PASSWORD = "correcthorsebatterystaple"
    SAMPLE_UNUSED_USERNAME = "akc2rW33AuSqQWY8"

    async def prerequest(self):
        async with self.get(Tumblr.URL) as r:
            text = await r.text()
            match = re.search(
                r'<meta name="tumblr-form-key" id="tumblr_form_key" content="([^\s]*)">', text
            )
            if match:
                token = match.group(1)
                return token

    async def _check(self, email=SAMPLE_UNUSED_EMAIL, username=SAMPLE_UNUSED_USERNAME):
        query = email if username == Tumblr.SAMPLE_UNUSED_USERNAME else username
        token = await self.get_token()
        async with self.post(
            Tumblr.ENDPOINT,
            data={
                "action": "signup_account",
                "form_key": token,
                "user[email]": email,
                "user[password]": Tumblr.SAMPLE_PASSWORD,
                "tumblelog[name]": username,
            },
        ) as r:
            json_body = await self.get_json(r)
            if username == query:
                if "usernames" in json_body or len(json_body["errors"]) > 0:
                    return self.response_unavailable_or_invalid(
                        query,
                        message=json_body["errors"][0],
                        unavailable_messages=Tumblr.USERNAME_TAKEN_MSGS,
                        link=Tumblr.USERNAME_LINK_FORMAT.format(query),
                    )
                elif json_body["errors"] == []:
                    return self.response_available(query)
            elif email == query:
                if "This email address is already in use." in json_body["errors"]:
                    return self.response_unavailable(query, message=json_body["errors"][0],)
                elif "This email address isn't correct. Please try again." in json_body["errors"]:
                    return self.response_invalid(query, message=json_body["errors"][0])
                elif json_body["errors"] == []:
                    return self.response_available(query)

    async def check_username(self, username):
        return await self._check(username=username)

    async def check_email(self, email):
        return await self._check(email=email)


class GitLab(PlatformChecker):
    URL = "https://gitlab.com/users/sign_in"
    ENDPOINT = "https://gitlab.com/users/{}/exists"
    USERNAME_LINK_FORMAT = "https://gitlab.com/{}"

    async def check_username(self, username):
        # Custom matching required as validation is implemented locally and not server-side by GitLab
        if not re.fullmatch(
            r"[a-zA-Z0-9_\.][a-zA-Z0-9_\-\.]*[a-zA-Z0-9_\-]|[a-zA-Z0-9_]", username
        ):
            return self.response_invalid(
                username, message="Please create a username with only alphanumeric characters."
            )
        async with self.get(
            GitLab.ENDPOINT.format(username), headers={"X-Requested-With": "XMLHttpRequest"}
        ) as r:
            # Special case for usernames
            if r.status == 401:
                return self.response_unavailable(
                    username, link=GitLab.USERNAME_LINK_FORMAT.format(username)
                )
            json_body = await self.get_json(r)
            if json_body["exists"]:
                return self.response_unavailable(
                    username, link=GitLab.USERNAME_LINK_FORMAT.format(username)
                )
            else:
                return self.response_available(username)

    # Email: GitLab requires a reCAPTCHA token to check email address usage which we cannot bypass


class Reddit(PlatformChecker):
    URL = "https://reddit.com"
    ENDPOINT = "https://www.reddit.com/api/check_username.json"
    USERNAME_TAKEN_MSGS = [
        "that username is already taken",
        "that username is taken by a deleted account",
    ]
    USERNAME_LINK_FORMAT = "https://www.reddit.com/u/{}"

    async def check_username(self, username):
        # Custom user agent required to overcome rate limits for Reddit API
        async with self.post(Reddit.ENDPOINT, data={"user": username}) as r:
            json_body = await self.get_json(r)
            if "error" in json_body and json_body["error"] == 429:
                return self.response_failure(
                    username, message=PlatformChecker.TOO_MANY_REQUEST_ERROR_MESSAGE
                )
            elif "json" in json_body:
                return self.response_unavailable_or_invalid(
                    username,
                    message=json_body["json"]["errors"][0][1],
                    unavailable_messages=Reddit.USERNAME_TAKEN_MSGS,
                    link=Reddit.USERNAME_LINK_FORMAT.format(username),
                )
            elif json_body == {}:
                return self.response_available(username)

    # Email: You can register multiple Reddit accounts under the same email address so not possible to check if an address is in use


class Twitter(PlatformChecker):
    URL = "https://twitter.com/signup"
    USERNAME_ENDPOINT = "https://api.twitter.com/i/users/username_available.json"
    EMAIL_ENDPOINT = "https://api.twitter.com/i/users/email_available.json"
    # [account in use, account suspended]
    USERNAME_TAKEN_MSGS = ["That username has been taken", "unavailable"]
    USERNAME_LINK_FORMAT = "https://twitter.com/{}"

    async def check_username(self, username):
        async with self.get(Twitter.USERNAME_ENDPOINT, params={"username": username}) as r:
            json_body = await self.get_json(r)
            message = json_body["desc"]
            if json_body["valid"]:
                return self.response_available(username, message=message)
            else:
                return self.response_unavailable_or_invalid(
                    username,
                    message=message,
                    unavailable_messages=Twitter.USERNAME_TAKEN_MSGS,
                    link=Twitter.USERNAME_LINK_FORMAT.format(username),
                )

    async def check_email(self, email):
        async with self.get(Twitter.EMAIL_ENDPOINT, params={"email": email}) as r:
            json_body = await self.get_json(r)
            message = json_body["msg"]
            if not json_body["valid"] and not json_body["taken"]:
                return self.response_invalid(email, message=message)

            if json_body["taken"]:
                return self.response_unavailable(email, message=message)
            else:
                return self.response_available(email, message=message)


class Pastebin(PlatformChecker):
    URL = "https://pastebin.com/signup"
    USERNAME_ENDPOINT = "https://pastebin.com/ajax/check_username.php"
    EMAIL_ENDPOINT = "https://pastebin.com/ajax/check_email.php"
    USERNAME_TAKEN_MSGS = ["Username not available!"]
    USERNAME_LINK_FORMAT = "https://pastebin.com/u/{}"

    regex = re.compile(r"^<font color=\"(red|green)\">([^<>]+)<\/font>$")

    async def _check(self, query, endpoint, data, is_email):
        async with self.post(endpoint, data=data) as r:
            text = await r.text()
            match = self.regex.match(text)
            if not match:
                return self.response_failure(
                    query, message=PlatformChecker.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE
                )
            else:
                message = match[2]
                if match[1] == "green":
                    return self.response_available(query, message=message)
                else:
                    if is_email:
                        if message == "Please use a valid email address.":
                            return self.response_invalid(query, message=message)
                        else:
                            return self.response_unavailable(query, message=message)
                    else:
                        return self.response_unavailable_or_invalid(
                            query,
                            message=message,
                            unavailable_messages=Pastebin.USERNAME_TAKEN_MSGS,
                            link=Pastebin.USERNAME_LINK_FORMAT.format(query),
                        )

    async def check_username(self, username):
        return await self._check(
            username,
            Pastebin.USERNAME_ENDPOINT,
            data={"action": "check_username", "username": username},
            is_email=False,
        )

    async def check_email(self, email):
        return await self._check(
            email,
            Pastebin.EMAIL_ENDPOINT,
            data={"action": "check_email", "username": email},
            is_email=True,
        )


class Pinterest(PlatformChecker):
    URL = "https://www.pinterest.com"
    EMAIL_ENDPOINT = "https://www.pinterest.com/_ngjs/resource/EmailExistsResource/get/"

    async def check_email(self, email):
        data = '{"options": {"email": "%s"}, "context": {}}' % email
        async with self.get(
            Pinterest.EMAIL_ENDPOINT, params={"source_url": "/", "data": data}
        ) as r:
            json_body = await self.get_json(r)
            email_exists = json_body["resource_response"]["data"]
            if email_exists:
                return self.response_unavailable(email)
            else:
                return self.response_available(email)


class Lastfm(PlatformChecker):
    URL = "https://www.last.fm/join"
    ENDPOINT = "https://www.last.fm/join/partial/validate"
    USERNAME_TAKEN_MSGS = ["Sorry, this username isn't available."]
    USERNAME_LINK_FORMAT = "https://www.last.fm/user/{}"

    async def prerequest(self):
        async with self.get(Lastfm.URL) as r:
            if "csrftoken" in r.cookies:
                token = r.cookies["csrftoken"].value
                return token

    async def _check(self, username="", email=""):
        token = await self.get_token()
        data = {"csrfmiddlewaretoken": token, "userName": username, "email": email}
        headers = {
            "Accept": "*/*",
            "Referer": "https://www.last.fm/join",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": f"csrftoken={token}",
        }
        async with self.post(Lastfm.ENDPOINT, data=data, headers=headers) as r:
            json_body = await self.get_json(r)
            if email:
                if json_body["email"]["valid"]:
                    return self.response_available(
                        email, message=json_body["email"]["success_message"]
                    )
                else:
                    return self.response_unavailable(
                        email, message=json_body["email"]["error_messages"][0]
                    )
            elif username:
                if json_body["userName"]["valid"]:
                    return self.response_available(
                        username, message=json_body["userName"]["success_message"]
                    )
                else:
                    return self.response_unavailable_or_invalid(
                        username,
                        message=re.sub("<[^<]+?>", "", json_body["userName"]["error_messages"][0]),
                        unavailable_messages=Lastfm.USERNAME_TAKEN_MSGS,
                        link=Lastfm.USERNAME_LINK_FORMAT.format(username),
                    )

    async def check_email(self, email):
        return await self._check(email=email)

    async def check_username(self, username):
        return await self._check(username=username)


class Spotify(PlatformChecker):
    URL = "https://www.spotify.com/signup/"
    EMAIL_ENDPOINT = "https://spclient.wg.spotify.com/signup/public/v1/account"

    async def check_email(self, email):
        async with self.get(Spotify.EMAIL_ENDPOINT, params={"validate": 1, "email": email}) as r:
            json_body = await self.get_json(r)
            if json_body["status"] == 1:
                return self.response_available(email)
            elif json_body["status"] == 20:
                return self.response_unavailable(email, message=json_body["errors"]["email"])
            else:
                return self.response_failure(email, message=json_body["errors"]["email"])


class Yahoo(PlatformChecker):
    URL = "https://login.yahoo.com/account/create"
    USERNAME_ENDPOINT = "https://login.yahoo.com/account/module/create?validateField=yid"

    # Modified from Yahoo source
    error_messages = {
        "IDENTIFIER_EXISTS": "A Yahoo account already exists with this username.",
        "RESERVED_WORD_PRESENT": "A reserved word is present in the username",
        "FIELD_EMPTY": "This is required.",
        "SOME_SPECIAL_CHARACTERS_NOT_ALLOWED": "You can only use letters, numbers, full stops (‘.’) and underscores (‘_’) in your username",
        "CANNOT_END_WITH_SPECIAL_CHARACTER": "Your username has to end with a letter or a number",
        "CANNOT_HAVE_MORE_THAN_ONE_PERIOD": "You can’t have more than one ‘.’ in your username.",
        "NEED_AT_LEAST_ONE_ALPHA": "Please use at least one letter in your username",
        "CANNOT_START_WITH_SPECIAL_CHARACTER_OR_NUMBER": "Your username has to start with a letter",
        "CONSECUTIVE_SPECIAL_CHARACTERS_NOT_ALLOWED": "You can’t have more than one ‘.’ or ‘_’ in a row.",
        "LENGTH_TOO_SHORT": "That username is too short, please use a longer one.",
        "LENGTH_TOO_LONG": "That username is too long, please use a shorter one.",
    }

    regex = re.compile(r"v=1&s=([^\s]*)")

    async def prerequest(self):
        async with self.get(Yahoo.URL) as r:
            if "AS" in r.cookies:
                match = self.regex.search(r.cookies["AS"].value)
                if match:
                    return match.group(1)

    async def check_username(self, username):
        token = await self.get_token()
        async with self.post(
            Yahoo.USERNAME_ENDPOINT,
            data={"specId": "yidReg", "acrumb": token, "yid": username},
            headers={"X-Requested-With": "XMLHttpRequest"},
        ) as r:
            json_body = await self.get_json(r)
            if json_body["errors"][2]["name"] != "yid":
                return self.response_available(username)
            else:
                error = json_body["errors"][2]["error"]
                error_pretty = self.error_messages.get(error, error.replace("_", " ").capitalize())
                if error == "IDENTIFIER_EXISTS" or error == "RESERVED_WORD_PRESENT":
                    return self.response_unavailable(username, message=error_pretty)
                else:
                    return self.response_invalid(username, message=error_pretty)


class Firefox(PlatformChecker):
    URL = "https://accounts.firefox.com/signup"
    EMAIL_ENDPOINT = "https://api.accounts.firefox.com/v1/account/status"

    async def check_email(self, email):
        async with self.post(Firefox.EMAIL_ENDPOINT, data={"email": email}) as r:
            json_body = await self.get_json(r)
            if "error" in json_body:
                return self.response_failure(email, message=json_body["message"])
            elif json_body["exists"]:
                return self.response_unavailable(email)
            else:
                return self.response_available(email)


class Platforms(Enum):
    GITHUB = GitHub
    GITLAB = GitLab
    INSTAGRAM = Instagram
    LASTFM = Lastfm
    PASTEBIN = Pastebin
    PINTEREST = Pinterest
    REDDIT = Reddit
    SNAPCHAT = Snapchat
    SPOTIFY = Spotify
    TWITTER = Twitter
    TUMBLR = Tumblr
    YAHOO = Yahoo
    FIREFOX = Firefox

    def __str__(self):
        return self.value.__name__

    def __len__(self):
        return len(self.value.__name__)


@dataclass(frozen=True)
class PlatformResponse:
    platform: Platforms
    query: str
    available: bool
    valid: bool
    success: bool
    message: str
    link: str

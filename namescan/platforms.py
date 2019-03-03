from enum import Enum
import re

import aiohttp


class PlatformResponse:
    def __init__(self, platform, username):
        __slots__ = ["platform", "username", "available", "valid", "success", "message"]
        self.platform = platform
        self.username = username


class PlatformChecker:
    DEFAULT_HEADERS = {"User-agent": "namescan 1.0", "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"}
    UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE = "Received unexpected content. Wait before trying again."
    TOKEN_ERROR_MESSAGE = "Could not retrieve token. Wait before trying again."
    TOO_MANY_REQUEST_ERROR_MESSAGE = "Requests denied by platform due to excessive requests. Wait before trying again."
    TIMEOUT_DURATION = 5

    client_timeout = aiohttp.ClientTimeout(connect=TIMEOUT_DURATION)
    prerequest_req = False

    async def prerequest(self):
        pass

    async def check_username(self, username):
        pass

    async def check_email(self, email):
        pass

    async def get_token(self):
        """
        Normal calls will not be able to take advantage of this as all tokens are retrieved concurrently
        This only applies to when tokens are retrieved before main queries with -c
        Adds 1-2s to overall running time but halves HTTP requests sent for bulk queries
        """
        if self.prerequest_sent:
            return self.token
        else:
            self.token = await self.prerequest()
            self.prerequest_sent = True
            return self.token

    def is_taken(self, message):
        return any(x in message for x in self.TAKEN_MESSAGES)

    def response_failure(self, username, message="Failure"):
        response = PlatformResponse(Platforms(self.__class__), username)
        response.available = response.valid = response.success = False
        response.message = message
        return response

    def response_available(self, username, message="Username is available"):
        response = PlatformResponse(Platforms(self.__class__), username)
        response.available = response.valid = response.success = True
        response.message = message
        return response

    def response_unavailable(self, username, message="Username is unavailable"):
        response = PlatformResponse(Platforms(self.__class__), username)
        response.valid = response.success = True
        response.available = False
        response.message = message
        return response

    def response_invalid(self, username, message="Username is invalid"):
        response = PlatformResponse(Platforms(self.__class__), username)
        response.success = True
        response.valid = response.available = False
        response.message = message
        return response

    def response_unavailable_or_invalid(self, username, message):
        if self.is_taken(message):
            return self.response_unavailable(username, message)
        else:
            return self.response_invalid(username, message)

    def post(self, url, **kwargs):
        if "headers" in kwargs:
            kwargs["headers"].update(self.DEFAULT_HEADERS)
        else:
            kwargs["headers"] = self.DEFAULT_HEADERS
        return self.session.post(url, timeout=self.client_timeout, **kwargs)

    def get(self, url, **kwargs):
        if "headers" in kwargs:
            kwargs["headers"].update(self.DEFAULT_HEADERS)
        else:
            kwargs["headers"] = self.DEFAULT_HEADERS
        return self.session.get(url, timeout=self.client_timeout, **kwargs)

    @staticmethod
    def content_type(request):
        return request.headers["Content-Type"]

    @staticmethod
    def is_json(request):
        return request.headers["Content-Type"].startswith("application/json")

    def __init__(self, session):
        self.session = session
        self.prerequest_sent = False
        self.taken_messages = []


class Snapchat(PlatformChecker):
    URL = "https://accounts.snapchat.com/accounts/login"
    ENDPOINT = "https://accounts.snapchat.com/accounts/get_username_suggestions"
    TAKEN_MESSAGES = ["is already taken", "is currently unavailable"]

    prerequest_req = True

    async def prerequest(self):
        async with self.get(self.URL) as r:
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
        if token is None:
            return self.response_failure(username, self.TOKEN_ERROR_MESSAGE)
        async with self.post(self.ENDPOINT,
                             data={"requested_username": username, "xsrf_token": token},
                             cookies={'xsrf_token': token}) as r:
            if not self.is_json(r):
                return self.response_failure(username, self.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE)
            json_body = await r.json()
            if "error_message" in json_body["reference"]:
                return self.response_unavailable_or_invalid(username, json_body["reference"]["error_message"])
            else:
                return self.response_available(username)


class Instagram(PlatformChecker):
    URL = "https://instagram.com"
    ENDPOINT = "https://www.instagram.com/accounts/web_create_ajax/attempt/"
    TAKEN_MESSAGES = ["This username isn't available.", "A user with that username already exists."]

    prerequest_req = True

    async def prerequest(self):
        async with self.get(self.URL) as r:
            if "csrftoken" in r.cookies:
                token = r.cookies["csrftoken"].value
                return token

    async def check_username(self, username):
        token = await self.get_token()
        if token is None:
            return self.response_failure(username, self.TOKEN_ERROR_MESSAGE)
        async with self.post(self.ENDPOINT,
                             data={"username": username},
                             headers={'x-csrftoken': token}) as r:
            if not self.is_json(r):
                return self.response_failure(username, self.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE)
            json_body = await r.json()
            # Too many requests
            if json_body["status"] == "fail":
                return self.response_failure(username, json_body["message"])
            if "username" in json_body["errors"]:
                return self.response_unavailable_or_invalid(username, json_body["errors"]["username"][0]["message"])
            else:
                return self.response_available(username)

    async def check_email(self, email):
        token = await self.get_token()
        if token is None:
            return self.response_failure(email, self.TOKEN_ERROR_MESSAGE)
        async with self.post(self.ENDPOINT,
                             data={"email": email},
                             headers={'x-csrftoken': token}) as r:
            if not self.is_json(r):
                return self.response_failure(email, self.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE)
            json_body = await r.json()
            # Too many requests
            if json_body["status"] == "fail":
                return self.response_failure(email, json_body["message"])
            if "email" not in json_body["errors"]:
                return self.response_available(email)
            else:
                message = json_body["errors"]["email"][0]["message"]
                if json_body["errors"]["email"][0]["code"] == "invalid_email":
                    return self.response_invalid(email, message)
                else:
                    return self.response_unavailable(email, message)


class GitHub(PlatformChecker):
    URL = "https://github.com/join"
    ENDPOINT = "https://github.com/signup_check/username"
    # Username 'x' is unavailable means reserved keyword while 'Username is already taken' means already in use
    TAKEN_MESSAGES = ["Username is already taken", "unavailable"]

    prerequest_req = True

    async def prerequest(self):
        async with self.get(self.URL) as r:
            text = await r.text()
            match = re.search(r'auto-check src="/signup_check/username" csrf="([^\s]*)"', text)
            if match:
                token = match.group(1)
                # _gh_sess cookie required for GH username query
                return (token, {"_gh_sess": r.cookies["_gh_sess"]})

    async def check_username(self, username):
        pr = await self.get_token()
        if pr is None:
            return self.response_failure(username, self.TOKEN_ERROR_MESSAGE)
        else:
            (token, cookies) = pr
        async with self.post(self.ENDPOINT,
                             data={"value": username, "authenticity_token": token},
                             cookies=cookies) as r:
            if r.status == 422:
                text = await r.text()
                return self.response_unavailable_or_invalid(username, text)
            elif r.status == 200:
                return self.response_available(username)
            elif r.status == 429:
                return self.response_failure(username, self.TOO_MANY_REQUEST_ERROR_MESSAGE)


class Tumblr(PlatformChecker):
    URL = "https://tumblr.com/register"
    ENDPOINT = "https://www.tumblr.com/svc/account/register"
    TAKEN_MESSAGES = ["That's a good one, but it's taken", "Someone beat you to that username", "Try something else, that one is spoken for"]

    prerequest_req = True

    async def prerequest(self):
        async with self.get(self.URL) as r:
            text = await r.text()
            match = re.search(r'<meta name="tumblr-form-key" id="tumblr_form_key" content="([^\s]*)">', text)
            if match:
                token = match.group(1)
                return token

    async def check_username(self, username):
        token = await self.get_token()
        if token is None:
            return self.response_failure(username, self.TOKEN_ERROR_MESSAGE)
        SAMPLE_UNUSED_EMAIL = "akc2rW33AuSqQWY8@gmail.com"
        SAMPLE_PASSWORD = "correcthorsebatterystaple"
        async with self.post(self.ENDPOINT,
                             data={"action": "signup_account", "form_key": token,
                                   "user[email]": SAMPLE_UNUSED_EMAIL, "user[password]": SAMPLE_PASSWORD, "tumblelog[name]": username}) as r:
            if not self.is_json(r):
                return self.response_failure(username, self.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE)
            json_body = await r.json()
            if "usernames" in json_body or len(json_body["errors"]) > 0:
                return self.response_unavailable_or_invalid(username, json_body["errors"][0])
            else:
                return self.response_available(username)


class GitLab(PlatformChecker):
    URL = "https://gitlab.com/users/sign_in",
    ENDPOINT = "https://gitlab.com/users/{}/exists"

    async def check_username(self, username):
        # Custom matching required as validation is implemented locally and not server-side by GitLab
        if not re.fullmatch(r"[a-zA-Z0-9_\.][a-zA-Z0-9_\-\.]*[a-zA-Z0-9_\-]|[a-zA-Z0-9_]", username):
            return self.response_invalid(username, "Please create a username with only alphanumeric characters.")
        async with self.get(self.ENDPOINT.format(username),
                            headers={"X-Requested-With": "XMLHttpRequest"}) as r:
            if r.status == 401:
                return self.response_unavailable(username)
            if not self.is_json(r):
                return self.response_failure(username, self.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE)
            json_body = await r.json()
            if json_body["exists"]:
                return self.response_unavailable(username)
            else:
                return self.response_available(username)


class Reddit(PlatformChecker):
    URL = "https://reddit.com"
    ENDPOINT = "https://www.reddit.com/api/check_username.json"
    TAKEN_MESSAGES = ["that username is already taken"]

    async def check_username(self, username):
        # Custom user agent required to overcome rate limits for Reddit API
        async with self.post(self.ENDPOINT,
                             data={"user": username}) as r:
            if not self.is_json(r):
                return self.response_failure(username, self.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE)
            json_body = await r.json()
            if "json" in json_body:
                return self.response_unavailable_or_invalid(username, json_body["json"]["errors"][0][1])
            else:
                return self.response_available(username)


class Twitter(PlatformChecker):
    URL = "https://twitter.com/signup",
    USERNAME_ENDPOINT = "https://twitter.com/users/username_available"
    EMAIL_ENDPOINT = "https://api.twitter.com/i/users/email_available.json"
    # [account in use, account suspended]
    TAKEN_MESSAGES = ["That username has been taken", "unavailable"]

    async def check_username(self, username):
        async with self.get(self.USERNAME_ENDPOINT,
                            params={"username": username}) as r:
            if not self.is_json(r):
                return self.response_failure(username, self.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE)
            json_body = await r.json()
            message = json_body["desc"]
            if json_body["valid"]:
                return self.response_available(username, message)
            else:
                return self.response_unavailable_or_invalid(username, message)

    async def check_email(self, email):
        async with self.get(self.EMAIL_ENDPOINT,
                            params={"email": email}) as r:
            if not self.is_json(r):
                return self.response_failure(email, self.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE)
            json_body = await r.json()
            message = json_body["msg"]
            if not json_body["valid"] and not json_body["taken"]:
                return self.response_invalid(email, message)

            if json_body["taken"]:
                return self.response_unavailable(email, message)
            else:
                return self.response_available(email, message)


class Pastebin(PlatformChecker):
    URL = "https://pastebin.com/signup",
    USERNAME_ENDPOINT = "https://pastebin.com/ajax/check_username.php"
    EMAIL_ENDPOINT = "https://pastebin.com/ajax/check_email.php"
    TAKEN_MESSAGES = ["Username not available!"]

    regex = re.compile(r"^<font color=\"(red|green)\">([^<>]+)<\/font>$")

    async def check_username(self, username):
        async with self.post(self.USERNAME_ENDPOINT,
                             data={"action": "check_username", "username": username}) as r:
            text = await r.text()
            match = self.regex.match(text)
            if not match:
                return self.response_failure(username, self.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE)
            else:
                message = match[2]
                if match[1] == "green":
                    return self.response_available(username, message)
                else:
                    return self.response_unavailable_or_invalid(username, message)

    async def check_email(self, email):
        async with self.post(self.EMAIL_ENDPOINT,
                             data={"action": "check_email", "username": email}) as r:
            text = await r.text()
            match = self.regex.match(text)
            if not match:
                return self.response_failure(email, self.UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE)
            else:
                message = match[2]
                if match[1] == "green":
                    return self.response_available(email, message)
                elif message == "Please use a valid email address.":
                    return self.response_invalid(email, message)
                else:
                    return self.response_unavailable(email, message)


class Platforms(Enum):
    GITHUB = GitHub
    GITLAB = GitLab
    INSTAGRAM = Instagram
    PASTEBIN = Pastebin
    REDDIT = Reddit
    SNAPCHAT = Snapchat
    TWITTER = Twitter
    TUMBLR = Tumblr

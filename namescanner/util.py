import re
from platforms import Platforms

CONTENT_TYPE_JSON = "application/json"
UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE_FORMAT = "Received unexpected content type {}. Wait before trying again"
TOKEN_ERROR_MESSAGE = "Could not retrieve token. Wait before trying again"
TOO_MANY_REQUEST_ERROR_MESSAGE = "Requests denied by platform due to excessive requests. Wait before trying again"
DEFAULT_HEADERS = {"User-agent": "namescanner 1.0"}
tokens = {}


class PlatformResponse:
    def __init__(self, platform, username):
        __slots__ = ["platform", "username", "valid", "success", "message"]
        self.platform = platform
        self.username = username

    def failure(self, message="Failure"):
        self.valid = False
        self.success = False
        self.message = message

    def valid(self, message="Available"):
        self.valid = True
        self.success = True
        self.message = message

    def invalid(self, message="Unavailable"):
        self.valid = False
        self.success = True
        self.message = message


async def prerequest(platform, session):
    global tokens
    if platform in tokens:
        """
        Normal calls will not be able to take advantage of this as all tokens are retrieved concurrently
        This only applies to when tokens are retrieved before main queries with -c
        Adds 1-2s to overall running time but halves HTTP requests sent for bulk queries
        """
        return tokens[platform]

    if platform == Platforms.INSTAGRAM:
        async with session.get(Platforms.INSTAGRAM.url) as r:
            if "csrftoken" in r.cookies:
                token = r.cookies["csrftoken"].value
                tokens[Platforms.INSTAGRAM] = token
                return token
            else:
                tokens[Platforms.INSTAGRAM] = None
    elif platform == Platforms.GITHUB:
        async with session.get(Platforms.GITHUB.url) as r:
            text = await r.text()
            match = re.search(r'auto-check src="/signup_check/username" csrf="([^\s]*)"', text)
            if match:
                token = match.group(1)
                # _gh_sess cookie required for GH username query
                token_tuple = (token, {"_gh_sess": r.cookies["_gh_sess"]})
                tokens[Platforms.GITHUB] = token_tuple
                return token_tuple
            else:
                tokens[Platforms.GITHUB] = None
    elif platform == Platforms.SNAPCHAT:
        async with session.get(Platforms.SNAPCHAT.url) as r:
            """
            See: https://github.com/aio-libs/aiohttp/issues/3002
            Snapchat sends multiple Set-Cookie headers in its response setting the value of 'xsrf-token',
            causing the original value of 'xsrf-token' to be overwritten in aiohttp
            Need to analyse the header response to extract the required value
            """
            cookies = r.headers.getall("Set-Cookie")
            token = ""
            for cookie in cookies:
                match = re.search(r"xsrf_token=([\w-]*);", cookie)
                if match and match.group(1) != "":
                    token = match.group(1)
                    tokens[Platforms.SNAPCHAT] = token
                    return token
            if token == "":
                tokens[Platforms.SNAPCHAT] = None
    elif platform == Platforms.TUMBLR:
        async with session.get(Platforms.TUMBLR.url) as r:
            text = await r.text()
            match = re.search(r'<meta name="tumblr-form-key" id="tumblr_form_key" content="([^\s]*)">', text)
            if match:
                token = match.group(1)
                tokens[Platforms.TUMBLR] = token
                return token
            else:
                tokens[Platforms.TUMBLR] = None


async def check_instagram(username, session, response):
    token = await prerequest(Platforms.INSTAGRAM, session)
    if token is None:
        response.failure(TOKEN_ERROR_MESSAGE)
        return response
    async with session.post(Platforms.INSTAGRAM.endpoint,
                            data={"username": username},
                            headers={**DEFAULT_HEADERS, 'x-csrftoken': token}) as r:
        if not content_type(r).startswith(CONTENT_TYPE_JSON):
                response.failure(UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE_FORMAT.format(content_type(r)))
                return response
        json_body = await r.json()
        if json_body["status"] == "fail":
            response.failure(json_body["message"])
            return response
        if "username" in json_body["errors"]:
            response.invalid(json_body["errors"]["username"][0]["message"])
        else:
            response.valid()
        return response


async def check_snapchat(username, session, response):
    token = await prerequest(Platforms.SNAPCHAT, session)
    if token is None:
        response.failure(TOKEN_ERROR_MESSAGE)
        return response
    # aiohttp.CLientSession() does not properly process 'xsrf-token' cookie from prerequest, so manually set cookie
    async with session.post(Platforms.SNAPCHAT.endpoint,
                            data={"requested_username": username,
                                  "xsrf_token": token},
                            headers=DEFAULT_HEADERS,
                            cookies={'xsrf_token': token}) as r:
        if not content_type(r).startswith(CONTENT_TYPE_JSON):
            response.failure(UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE_FORMAT.format(content_type(r)))
            return response
        json_body = await r.json()
        if "error_message" in json_body["reference"]:
            response.invalid(json_body["reference"]["error_message"])
        else:
            response.valid()
        return response


async def check_github(username, session, response):
    pr = await prerequest(Platforms.GITHUB, session)
    if pr is None:
        response.failure(TOKEN_ERROR_MESSAGE)
        return response
    (token, cookies) = pr
    async with session.post(Platforms.GITHUB.endpoint,
                            data={"value": username, "authenticity_token": token},
                            headers=DEFAULT_HEADERS,
                            cookies=cookies) as r:
        if r.status == 422:
            text = await r.text()
            response.invalid(text)
        elif r.status == 200:
            response.valid()
        elif r.status == 429:
            response.failure(TOO_MANY_REQUEST_ERROR_MESSAGE)
        return response


async def check_tumblr(username, session, response):
    token = await prerequest(Platforms.TUMBLR, session)
    if token is None:
        response.failure(TOKEN_ERROR_MESSAGE)
        return response
    SAMPLE_UNUSED_EMAIL = "akc2rW33AuSqQWY8@gmail.com"
    SAMPLE_PASSWORD = "correcthorsebatterystaple"
    async with session.post(Platforms.TUMBLR.endpoint,
                            data={"action": "signup_account", "form_key": token,
                                  "user[email]": SAMPLE_UNUSED_EMAIL, "user[password]": SAMPLE_PASSWORD,
                                  "tumblelog[name]": username},
                            headers=DEFAULT_HEADERS) as r:
        if not content_type(r).startswith(CONTENT_TYPE_JSON):
            response.failure(UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE_FORMAT.format(content_type(r)))
            return response
        json_body = await r.json()
        if "usernames" in json_body or len(json_body["errors"]) > 0:
            response.invalid(json_body["errors"][0])
        else:
            response.valid()
        return response


async def check_twitter(username, session, response):
    async with session.get(Platforms.TWITTER.endpoint,
                           params={"username": username},
                           headers=DEFAULT_HEADERS) as r:
        if not content_type(r).startswith(CONTENT_TYPE_JSON):
            response.failure(UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE_FORMAT.format(content_type(r)))
            return response
        json_body = await r.json()
        message = json_body["desc"]
        if json_body["valid"]:
            response.valid(message)
        else:
            response.invalid(message)
        return response


async def check_reddit(username, session, response):
    # Custom user agent required to overcome rate limits for Reddit API
    async with session.post(Platforms.REDDIT.endpoint,
                            data={"user": username},
                            headers=DEFAULT_HEADERS) as r:
        if not content_type(r).startswith(CONTENT_TYPE_JSON):
            response.failure(UNEXPECTED_CONTENT_TYPE_ERROR_MESSAGE_FORMAT.format(content_type(r)))
            return response
        json_body = await r.json()
        if "json" in json_body:
            response.invalid(json_body["json"]["errors"][0][1])
        else:
            response.valid()
        return response


def content_type(request):
    return request.headers["Content-Type"]


async def is_username_available(platform, username, session):
    dispatch = {Platforms.GITHUB: check_github,
                Platforms.INSTAGRAM: check_instagram,
                Platforms.REDDIT: check_reddit,
                Platforms.SNAPCHAT: check_snapchat,
                Platforms.TWITTER: check_twitter,
                Platforms.TUMBLR: check_tumblr}
    return await dispatch[platform](username, session, PlatformResponse(platform, username))

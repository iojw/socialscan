from enum import Enum


class Platforms(Enum):
    GITHUB = ("https://github.com/join",
              "https://github.com/signup_check/username")
    GITLAB = ("https://gitlab.com/users/sign_in",
              "https://gitlab.com/users/{}/exists")
    INSTAGRAM = ("https://instagram.com",
                 "https://www.instagram.com/accounts/web_create_ajax/attempt/")
    REDDIT = ("https://reddit.com",
              "https://www.reddit.com/api/check_username.json")
    SNAPCHAT = ("https://accounts.snapchat.com/accounts/login",
                "https://accounts.snapchat.com/accounts/get_username_suggestions")
    TWITTER = ("ht1tps://twitter.com/signup",
               "https://twitter.com/users/username_available")
    TUMBLR = ("https://tumblr.com/register",
              "https://www.tumblr.com/svc/account/register")

    def __init__(self, url, endpoint):
        self.url = url
        self.endpoint = endpoint

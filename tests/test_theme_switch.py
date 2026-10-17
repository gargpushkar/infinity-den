"""The header switch's choice (a "theme" cookie) decides when night.css applies."""

import re

import pytest

from app.routes.public.home import templates


class _Request:
    url = "https://infinityden.test/"

    def __init__(self, cookies: dict[str, str]) -> None:
        self.cookies = cookies

    def url_for(self, name: str, **params: str) -> str:
        return f"/static/{params.get('path', '')}"


@pytest.mark.parametrize(
    ("cookies", "media"),
    [
        ({}, "(prefers-color-scheme: dark)"),
        ({"theme": "dark"}, "all"),
        ({"theme": "light"}, "not all"),
        ({"theme": "<script>"}, "(prefers-color-scheme: dark)"),
    ],
)
def test_night_styles_follow_the_choice_or_the_device(cookies, media):
    html = templates.get_template("layouts/base.html").render(request=_Request(cookies), app_name="Infinity Den")
    link = re.search(r'<link[^>]*night\.css[^>]*>', html).group(0)
    assert f'media="{media}"' in link

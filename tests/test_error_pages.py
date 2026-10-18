"""Error pages speak plainly: a friendly line for a bare 404, the route's own message when it has one."""

from app.middleware.exception_handlers import error_copy
from app.routes.public.form_pages import templates
from tests.test_theme_switch import _Request


def test_a_bare_404_gets_friendly_words_and_a_specific_message_is_kept():
    assert error_copy(404, "Not Found") == ("We couldn't find that page.", "The link may be old, or the page may have moved.")
    assert error_copy(404, "Debate was not found.") == ("We couldn't find that page.", "Debate was not found.")
    assert error_copy(418, "I'm a Teapot") == ("I'm a Teapot", "I'm a Teapot")  # unknown codes keep the phrase


def test_the_404_page_offers_places_to_go_and_never_repeats_itself():
    title, message = error_copy(404, "Not Found")
    html = templates.get_template("pages/error.html").render(
        request=_Request({}), app_name="Infinity Den", status_code=404, page_title="Not Found",
        error_title=title, error_message=message,
    )
    body = html.split("<main", 1)[-1]
    assert "Not Found" not in body
    assert 'href="/questions"' in body and 'href="/categories"' in body and 'href="/search"' in body

"""Member accounts: validation, token separation, CSRF, rate limits, privacy.

No database and no real secret: settings are swapped for a test key.
"""

import asyncio
import dataclasses
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.routes.public.members import _safe_next
from app.schemas.user import MemberRead, MemberSignup
from app.services import admin_session, member_session
from app.services.member_page_service import public_profile
from app.utils.rate_limit import RateLimiter
from app.utils.security import create_access_token


TEST_SETTINGS = dataclasses.replace(member_session.settings, auth_secret_key="test-secret")
MEMBER = MemberRead(
    _id="0123456789abcdef01234567",
    username="mira",
    display_name="Mira",
    email="mira@example.org",
    bio="Curious about everything.",
    created_at=datetime(2026, 10, 16, tzinfo=timezone.utc),
)


@pytest.fixture(autouse=True)
def test_secret(monkeypatch):
    monkeypatch.setattr(member_session, "settings", TEST_SETTINGS)
    monkeypatch.setattr(admin_session, "settings", TEST_SETTINGS)


def _request(cookies: dict[str, str]) -> Request:
    cookie_header = "; ".join(f"{name}={value}" for name, value in cookies.items())
    return Request({"type": "http", "headers": [(b"cookie", cookie_header.encode())]})


def _admin_token() -> str:
    return create_access_token(
        subject="0123456789abcdef01234567",
        secret_key="test-secret",
        expires_delta=timedelta(minutes=5),
        claims={"kind": "admin", "role": "admin", "username": "admin"},
    )


# --- sign-up validation ------------------------------------------------------

def _signup(**overrides) -> MemberSignup:
    data = {
        "username": "mira",
        "display_name": "Mira",
        "email": "Mira@Example.org ",
        "password": "a long enough password",
        **overrides,
    }
    return MemberSignup(**data)


def test_signup_normalizes_email_and_username():
    signup = _signup(username="  Mira ")
    assert signup.username == "mira"
    assert signup.email == "mira@example.org"


@pytest.mark.parametrize(
    "overrides",
    [
        {"username": "ab"},
        {"username": "-mira"},
        {"username": "mira!"},
        {"username": "admin"},
        {"email": "not-an-email"},
        {"password": "short"},
        {"display_name": " "},
    ],
)
def test_signup_rejects_invalid_input(overrides):
    with pytest.raises(ValidationError):
        _signup(**overrides)


# --- token kinds never cross over -------------------------------------------

def test_member_token_is_recognised_as_member():
    token = member_session.create_member_token(MEMBER)
    claims = member_session.member_claims(_request({member_session.MEMBER_AUTH_COOKIE: token}))
    assert claims["sub"] == MEMBER.id
    assert claims["kind"] == "member"


def test_member_token_cannot_open_admin_area():
    token = member_session.create_member_token(MEMBER)
    request = _request({admin_session.ADMIN_AUTH_COOKIE: token})
    with pytest.raises(HTTPException) as error:
        # The admin lookup is never reached: the token kind is rejected first.
        asyncio.run(admin_session.get_current_admin(request, admin_service=None))
    assert error.value.status_code == 401


def test_admin_token_is_not_a_member_session():
    request = _request({member_session.MEMBER_AUTH_COOKIE: _admin_token()})
    assert member_session.member_claims(request) is None


def test_tampered_member_token_is_rejected():
    token = member_session.create_member_token(MEMBER)
    request = _request({member_session.MEMBER_AUTH_COOKIE: token[:-2] + "xx"})
    assert member_session.member_claims(request) is None


# --- CSRF for member forms ---------------------------------------------------

def test_form_csrf_requires_matching_signed_token():
    token = member_session.form_csrf_token(_request({}))
    cookie = {member_session.MEMBER_CSRF_COOKIE: token}
    assert member_session.form_csrf_is_valid(_request(cookie), {"csrf_token": token})
    assert not member_session.form_csrf_is_valid(_request(cookie), {"csrf_token": "other"})
    assert not member_session.form_csrf_is_valid(_request({}), {"csrf_token": token})


def test_form_csrf_token_is_reused_across_tabs():
    token = member_session.form_csrf_token(_request({}))
    again = member_session.form_csrf_token(_request({member_session.MEMBER_CSRF_COOKIE: token}))
    assert again == token


# --- rate limiting and redirects ---------------------------------------------

def test_rate_limiter_blocks_then_recovers():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("ip", now=0)
    assert limiter.allow("ip", now=1)
    assert not limiter.allow("ip", now=2)
    assert limiter.allow("other-ip", now=2)
    assert limiter.allow("ip", now=61)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/account", "/account"),
        ("https://evil.example", ""),
        ("//evil.example", ""),
        ("/\\evil.example", ""),
        ("", ""),
    ],
)
def test_next_only_allows_same_site_paths(value, expected):
    assert _safe_next(value) == expected


# --- privacy -----------------------------------------------------------------

def test_public_profile_never_includes_email():
    profile = public_profile(MEMBER)
    assert "email" not in profile
    assert "password_hash" not in profile
    assert MEMBER.email not in str(profile)
    assert profile["url"] == "/members/mira"

"""Member sign-in state: the session cookie and CSRF tokens for member forms.

Tokens carry ``kind: "member"`` and admin tokens carry ``kind: "admin"``; each
side rejects the other's, so a member token can never open the admin area.
"""

from datetime import timedelta
from typing import Any

from fastapi import Request, Response

from app.config.settings import settings
from app.schemas.user import MemberRead
from app.services.user_service import UserService
from app.utils.security import (
    SecurityError,
    TokenValidationError,
    create_access_token,
    create_csrf_token,
    decode_access_token,
    verify_csrf_token,
)


MEMBER_AUTH_COOKIE = "member_access_token"
MEMBER_CSRF_COOKIE = "member_csrf_token"
MEMBER_TOKEN_KIND = "member"


def create_member_token(member: MemberRead) -> str:
    return create_access_token(
        subject=member.id,
        secret_key=settings.auth_secret_key,
        expires_delta=timedelta(days=settings.member_token_expire_days),
        claims={
            "kind": MEMBER_TOKEN_KIND,
            "username": member.username,
            "display_name": member.display_name,
            "sv": member.session_version,
        },
    )


def set_member_cookie(response: Response, member: MemberRead) -> None:
    response.set_cookie(
        MEMBER_AUTH_COOKIE,
        create_member_token(member),
        max_age=settings.member_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )


def clear_member_cookie(response: Response) -> None:
    response.delete_cookie(MEMBER_AUTH_COOKIE)


def member_claims(request: Request) -> dict[str, Any] | None:
    """The member token's verified claims, without touching the database.

    Only a first step: use get_current_member, which also checks the account
    still exists and is active, before showing or changing anything.
    """
    token = request.cookies.get(MEMBER_AUTH_COOKIE, "").strip()
    if not token:
        return None

    try:
        payload = decode_access_token(token, settings.auth_secret_key)
    except (TokenValidationError, SecurityError):
        return None

    if payload.get("kind") != MEMBER_TOKEN_KIND or not isinstance(payload.get("sub"), str):
        return None

    return payload


async def get_current_member(request: Request) -> MemberRead | None:
    claims = member_claims(request)
    if claims is None:
        return None

    member = await UserService().get_member_by_id(claims["sub"])
    # Cookies from before a password reset carry an older session number.
    # Cookies issued before session numbers existed carry none, which counts as 0.
    if member is None or member.session_version != claims.get("sv", 0):
        return None
    return member


def form_csrf_token(request: Request) -> str:
    """Double-submit CSRF: the same signed token goes in the form and a cookie.

    Reuses the visitor's existing token so a second open tab does not
    invalidate the form in the first one.
    """
    existing = request.cookies.get(MEMBER_CSRF_COOKIE, "").strip()
    if existing and verify_csrf_token(existing, settings.auth_secret_key):
        return existing

    return create_csrf_token(settings.auth_secret_key)


def set_form_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        MEMBER_CSRF_COOKIE,
        token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )


def form_csrf_is_valid(request: Request, form: dict[str, str]) -> bool:
    form_token = form.get("csrf_token", "").strip()
    cookie_token = request.cookies.get(MEMBER_CSRF_COOKIE, "").strip()
    if not form_token or form_token != cookie_token:
        return False

    return verify_csrf_token(form_token, settings.auth_secret_key)

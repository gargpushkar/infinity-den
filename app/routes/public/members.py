from typing import Any

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi import status as http_status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from app.config.settings import settings
from app.schemas.user import (
    PASSWORD_MIN_LENGTH,
    MemberLogin,
    MemberProfileUpdate,
    MemberSignup,
)
from app.services.member_page_service import (
    get_member_profile_context,
    member_profile_url,
    public_profile,
)
from app.services.member_session import (
    clear_member_cookie,
    form_csrf_is_valid,
    get_current_member,
    form_csrf_token,
    set_form_csrf_cookie,
    set_member_cookie,
)
from app.services.nav_service import get_nav_context
from app.services.user_service import (
    EmailTakenError,
    InvalidCredentialsError,
    UserService,
    UsernameTakenError,
)
from app.utils.forms import read_form
from app.utils.rate_limit import client_key, member_login_limiter, member_signup_limiter


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

FORM_EXPIRED = "Your form expired. Please try again."
TOO_MANY_ATTEMPTS = "Too many attempts. Please wait a few minutes and try again."
SERVICE_UNAVAILABLE = "Accounts are unavailable right now. Please try again shortly."


# --- sign up -----------------------------------------------------------------

@router.get("/join")
async def join_page(request: Request):
    if await _signed_in(request):
        return RedirectResponse("/account", status_code=303)

    return await _render(request, "pages/member_join.html", "Join", values={})


@router.post("/join")
async def join(request: Request):
    form = await read_form(request)
    values = {key: form.get(key, "") for key in ("username", "display_name", "email")}

    if not form_csrf_is_valid(request, form):
        return await _render(request, "pages/member_join.html", "Join", values=values, error=FORM_EXPIRED, status_code=400)
    if not member_signup_limiter.allow(client_key(request)):
        return await _render(request, "pages/member_join.html", "Join", values=values, error=TOO_MANY_ATTEMPTS, status_code=429)

    try:
        payload = MemberSignup(**values, password=form.get("password", ""))
    except ValidationError as exc:
        return await _render(request, "pages/member_join.html", "Join", values=values, field_errors=_field_errors(exc), status_code=422)

    try:
        member = await UserService().create_member(payload)
    except UsernameTakenError as exc:
        return await _render(request, "pages/member_join.html", "Join", values=values, field_errors={"username": str(exc)}, status_code=409)
    except EmailTakenError as exc:
        return await _render(request, "pages/member_join.html", "Join", values=values, field_errors={"email": str(exc)}, status_code=409)
    except (RuntimeError, PyMongoError):
        return await _render(request, "pages/member_join.html", "Join", values=values, error=SERVICE_UNAVAILABLE, status_code=503)

    response = RedirectResponse("/account?welcome=1", status_code=303)
    set_member_cookie(response, member)
    return response


# --- sign in / sign out ------------------------------------------------------

@router.get("/login")
async def login_page(request: Request, next: str = ""):
    if await _signed_in(request):
        return RedirectResponse(_safe_next(next) or "/account", status_code=303)

    return await _render(request, "pages/member_login.html", "Sign in", values={"next": _safe_next(next)})


@router.post("/login")
async def login(request: Request):
    form = await read_form(request)
    values = {"email": form.get("email", ""), "next": _safe_next(form.get("next", ""))}

    if not form_csrf_is_valid(request, form):
        return await _render(request, "pages/member_login.html", "Sign in", values=values, error=FORM_EXPIRED, status_code=400)
    if not member_login_limiter.allow(client_key(request)):
        return await _render(request, "pages/member_login.html", "Sign in", values=values, error=TOO_MANY_ATTEMPTS, status_code=429)

    try:
        member = await UserService().authenticate(
            MemberLogin(email=values["email"], password=form.get("password", ""))
        )
    except (ValidationError, InvalidCredentialsError):
        return await _render(request, "pages/member_login.html", "Sign in", values=values, error="Email or password is incorrect.", status_code=401)
    except (RuntimeError, PyMongoError):
        return await _render(request, "pages/member_login.html", "Sign in", values=values, error=SERVICE_UNAVAILABLE, status_code=503)

    response = RedirectResponse(values["next"] or member_profile_url(member.username), status_code=303)
    set_member_cookie(response, member)
    return response


@router.get("/logout")
async def logout_page(request: Request):
    return await _render(request, "pages/member_logout.html", "Sign out", values={})


@router.post("/logout")
async def logout(request: Request):
    form = await read_form(request)
    if not form_csrf_is_valid(request, form):
        return await _render(request, "pages/member_logout.html", "Sign out", values={}, error=FORM_EXPIRED, status_code=400)

    response = RedirectResponse("/", status_code=303)
    clear_member_cookie(response)
    return response


# --- your account ------------------------------------------------------------

@router.get("/account")
async def account_page(request: Request, welcome: bool = False, saved: bool = False):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse("/login?next=/account", status_code=303)

    return await _render(
        request,
        "pages/member_account.html",
        "Your account",
        values={"display_name": member.display_name, "bio": member.bio or ""},
        member=public_profile(member),
        email=member.email,
        notice="Welcome to Infinity Den." if welcome else "Profile saved." if saved else None,
    )


@router.post("/account")
async def update_account(request: Request):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse("/login?next=/account", status_code=303)

    form = await read_form(request)
    values = {"display_name": form.get("display_name", ""), "bio": form.get("bio", "")}
    page = {"member": public_profile(member), "email": member.email}

    if not form_csrf_is_valid(request, form):
        return await _render(request, "pages/member_account.html", "Your account", values=values, error=FORM_EXPIRED, status_code=400, **page)

    try:
        payload = MemberProfileUpdate(**values)
    except ValidationError as exc:
        return await _render(request, "pages/member_account.html", "Your account", values=values, field_errors=_field_errors(exc), status_code=422, **page)

    updated = await UserService().update_profile(member.id, payload)
    response = RedirectResponse("/account?saved=1", status_code=303)
    set_member_cookie(response, updated)  # the header shows the display name from the token
    return response


# --- public profile ----------------------------------------------------------

@router.get("/members/{username}")
async def member_profile(request: Request, username: str = Path(min_length=3, max_length=30)):
    context = await get_member_profile_context(username)
    if context is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Member was not found.")

    member = context["member"]
    return templates.TemplateResponse(
        request,
        "pages/member_profile.html",
        {
            **await get_nav_context(request),
            **context,
            "app_name": settings.app_name,
            "page_title": member["display_name"],
            "seo_title": f"{member['display_name']} (@{member['username']})",
            "seo_description": member["bio"] or f"{member['display_name']} on {settings.app_name}.",
        },
    )


# --- helpers -----------------------------------------------------------------

async def _render(
    request: Request,
    template: str,
    title: str,
    *,
    values: dict[str, str],
    status_code: int = 200,
    error: str | None = None,
    field_errors: dict[str, str] | None = None,
    **extra: Any,
):
    """Render a member form page with a fresh CSRF token. Never echoes passwords."""
    csrf_token = form_csrf_token(request)
    context = {
        **await get_nav_context(request),
        "app_name": settings.app_name,
        "page_title": title,
        "seo_title": title,
        "robots": "noindex, nofollow",
        "values": values,
        "error": error,
        "field_errors": field_errors or {},
        "password_min_length": PASSWORD_MIN_LENGTH,
        "csrf_token": csrf_token,
        **extra,
    }
    response = templates.TemplateResponse(request, template, context, status_code=status_code)
    set_form_csrf_cookie(response, csrf_token)
    return response


async def _signed_in(request: Request) -> bool:
    try:
        return await get_current_member(request) is not None
    except (RuntimeError, PyMongoError):
        return False


def _field_errors(exc: ValidationError) -> dict[str, str]:
    errors: dict[str, str] = {}
    for error in exc.errors():
        field = str(error["loc"][0]) if error["loc"] else "form"
        limits = error.get("ctx") or {}
        if error["type"] == "string_too_short":
            message = f"Must be at least {limits.get('min_length')} characters." if limits.get("min_length", 0) > 1 else "This field is required."
        elif error["type"] == "string_too_long":
            message = f"Must be at most {limits.get('max_length')} characters."
        else:
            message = str(error["msg"]).removeprefix("Value error, ")
        errors.setdefault(field, message)
    return errors


def _safe_next(value: str) -> str:
    """Only same-site paths, so ?next= cannot send people to another site."""
    value = (value or "").strip()
    if value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return ""

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi import status as http_status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from pymongo.errors import PyMongoError
from starlette.background import BackgroundTask

from app.config.settings import settings
from app.routes.public.form_pages import (
    FORM_EXPIRED,
    SERVICE_UNAVAILABLE,
    TOO_MANY_ATTEMPTS,
    field_errors,
    render_form_page,
    safe_next,
    templates,
)
from app.schemas.user import MemberLogin, MemberProfileUpdate, MemberSignup
from app.services.member_article_service import MemberArticleService
from app.services.member_page_service import (
    get_member_profile_context,
    member_profile_url,
    public_profile,
)
from app.services.member_session import (
    clear_member_cookie,
    form_csrf_is_valid,
    get_current_member,
    set_member_cookie,
)
from app.routes.public.email_confirmation import send_confirmation_later
from app.services.account_deletion_service import (
    DELETION_DAYS,
    AccountDeletionService,
    WrongPasswordError,
    send_request_received,
)
from app.services.nav_service import get_nav_context
from app.services.user_service import (
    DeletionRequestedError,
    EmailTakenError,
    InvalidCredentialsError,
    UserService,
    UsernameTakenError,
)
from app.utils.forms import read_form
from app.utils.rate_limit import account_delete_limiter, client_key, member_login_limiter, member_signup_limiter


router = APIRouter()


# --- sign up -----------------------------------------------------------------

@router.get("/join")
async def join_page(request: Request):
    # An unconfirmed member may join again, for example to fix a mistyped email.
    if await _signed_in(request, confirmed_only=True):
        return RedirectResponse("/account", status_code=303)

    return await render_form_page(request, "pages/member_join.html", "Join", values={})


@router.post("/join")
async def join(request: Request):
    form = await read_form(request)
    values = {key: form.get(key, "") for key in ("username", "display_name", "email")}

    if not form_csrf_is_valid(request, form):
        return await render_form_page(request, "pages/member_join.html", "Join", values=values, error=FORM_EXPIRED, status_code=400)
    if not member_signup_limiter.allow(client_key(request)):
        return await render_form_page(request, "pages/member_join.html", "Join", values=values, error=TOO_MANY_ATTEMPTS, status_code=429)

    try:
        payload = MemberSignup(**values, password=form.get("password", ""))
    except ValidationError as exc:
        return await render_form_page(request, "pages/member_join.html", "Join", values=values, field_errors=field_errors(exc), status_code=422)

    try:
        member = await UserService().create_member(payload)
    except UsernameTakenError as exc:
        return await render_form_page(request, "pages/member_join.html", "Join", values=values, field_errors={"username": str(exc)}, status_code=409)
    except EmailTakenError as exc:
        return await render_form_page(request, "pages/member_join.html", "Join", values=values, field_errors={"email": str(exc)}, status_code=409)
    except (RuntimeError, PyMongoError):
        return await render_form_page(request, "pages/member_join.html", "Join", values=values, error=SERVICE_UNAVAILABLE, status_code=503)

    response = RedirectResponse("/confirm-email?sent=1", status_code=303)
    set_member_cookie(response, member)
    send_confirmation_later(response, request, member)
    return response


# --- sign in / sign out ------------------------------------------------------

@router.get("/login")
async def login_page(request: Request, next: str = "", confirmed: bool = False):
    if await _signed_in(request):
        return RedirectResponse(safe_next(next) or "/account", status_code=303)

    notice = "Your email is confirmed. Sign in to start taking part." if confirmed else None
    return await render_form_page(request, "pages/member_login.html", "Sign in", values={"next": safe_next(next)}, notice=notice)


@router.post("/login")
async def login(request: Request):
    form = await read_form(request)
    values = {"email": form.get("email", ""), "next": safe_next(form.get("next", ""))}

    if not form_csrf_is_valid(request, form):
        return await render_form_page(request, "pages/member_login.html", "Sign in", values=values, error=FORM_EXPIRED, status_code=400)
    if not member_login_limiter.allow(client_key(request)):
        return await render_form_page(request, "pages/member_login.html", "Sign in", values=values, error=TOO_MANY_ATTEMPTS, status_code=429)

    try:
        member = await UserService().authenticate(
            MemberLogin(email=values["email"], password=form.get("password", ""))
        )
    except (ValidationError, InvalidCredentialsError):
        return await render_form_page(request, "pages/member_login.html", "Sign in", values=values, error="Email or password is incorrect.", status_code=401)
    except DeletionRequestedError:
        return await render_form_page(
            request, "pages/member_login.html", "Sign in", values=values, status_code=403,
            error=f"You asked us to delete this account, so it can't be used any more. "
                  f"If you've changed your mind or need help, contact us at {settings.contact_email}.",
        )
    except (RuntimeError, PyMongoError):
        return await render_form_page(request, "pages/member_login.html", "Sign in", values=values, error=SERVICE_UNAVAILABLE, status_code=503)

    response = RedirectResponse(values["next"] or member_profile_url(member.username), status_code=303)
    set_member_cookie(response, member)
    return response


@router.get("/logout")
async def logout_page(request: Request):
    return await render_form_page(request, "pages/member_logout.html", "Sign out", values={})


@router.post("/logout")
async def logout(request: Request):
    form = await read_form(request)
    if not form_csrf_is_valid(request, form):
        return await render_form_page(request, "pages/member_logout.html", "Sign out", values={}, error=FORM_EXPIRED, status_code=400)

    response = RedirectResponse("/", status_code=303)
    clear_member_cookie(response)
    return response


# --- your account ------------------------------------------------------------

@router.get("/account")
async def account_page(request: Request, welcome: bool = False, saved: bool = False, reset: bool = False, confirmed: bool = False):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse("/login?next=/account", status_code=303)

    return await render_form_page(
        request,
        "pages/member_account.html",
        "Your account",
        values={"display_name": member.display_name, "bio": member.bio or ""},
        member=public_profile(member),
        email=member.email,
        pieces=await MemberArticleService().list_own(member),
        notice="Welcome to Infinity Den." if welcome else "Profile saved." if saved
        else "Your new password is saved, and every other device is signed out." if reset
        else "Your email is confirmed. You can now write, respond, and comment." if confirmed else None,
    )


@router.post("/account")
async def update_account(request: Request):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse("/login?next=/account", status_code=303)

    form = await read_form(request)
    values = {"display_name": form.get("display_name", ""), "bio": form.get("bio", "")}
    page = {
        "member": public_profile(member),
        "email": member.email,
        "pieces": await MemberArticleService().list_own(member),
    }

    if not form_csrf_is_valid(request, form):
        return await render_form_page(request, "pages/member_account.html", "Your account", values=values, error=FORM_EXPIRED, status_code=400, **page)

    try:
        payload = MemberProfileUpdate(**values)
    except ValidationError as exc:
        return await render_form_page(request, "pages/member_account.html", "Your account", values=values, field_errors=field_errors(exc), status_code=422, **page)

    updated = await UserService().update_profile(member.id, payload)
    response = RedirectResponse("/account?saved=1", status_code=303)
    set_member_cookie(response, updated)  # keep the token's claims current
    return response


@router.post("/account/delete")
async def request_account_deletion(request: Request):
    """Members only ask; editors delete (see account_deletion_service)."""
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse("/login?next=/account", status_code=303)

    form = await read_form(request)
    page = {
        "member": public_profile(member),
        "email": member.email,
        "pieces": await MemberArticleService().list_own(member),
    }
    values = {"display_name": member.display_name, "bio": member.bio or ""}

    if not form_csrf_is_valid(request, form):
        return await render_form_page(request, "pages/member_account.html", "Your account", values=values, error=FORM_EXPIRED, status_code=400, **page)
    if not account_delete_limiter.allow(member.id):
        return await render_form_page(request, "pages/member_account.html", "Your account", values=values, error=TOO_MANY_ATTEMPTS, status_code=429, **page)

    try:
        account = await AccountDeletionService().request(member.id, form.get("delete_password", ""))
    except WrongPasswordError:
        return await render_form_page(
            request, "pages/member_account.html", "Your account", values=values,
            field_errors={"delete_password": "That password is incorrect."}, status_code=401, **page,
        )
    except (RuntimeError, PyMongoError):
        return await render_form_page(request, "pages/member_account.html", "Your account", values=values, error=SERVICE_UNAVAILABLE, status_code=503, **page)

    response = await render_form_page(request, "pages/member_account_deleted.html", "Deletion requested", values={}, deletion_days=DELETION_DAYS)
    clear_member_cookie(response)
    response.background = BackgroundTask(send_request_received, account["email"], account["display_name"])
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

async def _signed_in(request: Request, *, confirmed_only: bool = False) -> bool:
    try:
        member = await get_current_member(request)
    except (RuntimeError, PyMongoError):
        return False
    return member is not None and (member.email_confirmed or not confirmed_only)

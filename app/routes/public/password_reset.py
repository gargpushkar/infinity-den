import logging

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from pymongo.errors import PyMongoError
from starlette.background import BackgroundTask

from app.routes.public.form_pages import (
    FORM_EXPIRED,
    SERVICE_UNAVAILABLE,
    TOO_MANY_ATTEMPTS,
    field_errors,
    render_form_page,
    site_url,
)
from app.schemas.user import PasswordResetInput, PasswordResetRequest
from app.services.member_session import form_csrf_is_valid, set_member_cookie
from app.services.password_reset_service import InvalidResetLinkError, PasswordResetService
from app.utils.forms import read_form
from app.utils.rate_limit import client_key, reset_email_limiter, reset_password_limiter, reset_request_limiter


logger = logging.getLogger(__name__)
router = APIRouter()

FORGOT_TEMPLATE = "pages/member_forgot_password.html"
RESET_TEMPLATE = "pages/member_reset_password.html"
LINK_SENT = (
    "If an account uses that address, we've sent it a link to choose a new password. "
    "It works for an hour. Check your spam folder if it doesn't arrive in a few minutes."
)
LINK_INVALID = "This link has expired or has already been used. Ask for a new one below."


@router.get("/forgot-password")
async def forgot_password_page(request: Request, expired: bool = False):
    return await render_form_page(request, FORGOT_TEMPLATE, "Reset your password", values={}, error=LINK_INVALID if expired else None)


@router.post("/forgot-password")
async def forgot_password(request: Request):
    form = await read_form(request)
    values = {"email": form.get("email", "")}

    if not form_csrf_is_valid(request, form):
        return await render_form_page(request, FORGOT_TEMPLATE, "Reset your password", values=values, error=FORM_EXPIRED, status_code=400)
    if not reset_request_limiter.allow(client_key(request)):
        return await render_form_page(request, FORGOT_TEMPLATE, "Reset your password", values=values, error=TOO_MANY_ATTEMPTS, status_code=429)
    try:
        payload = PasswordResetRequest(**values)
    except ValidationError as exc:
        return await render_form_page(request, FORGOT_TEMPLATE, "Reset your password", values=values, field_errors=field_errors(exc), status_code=422)

    response = await render_form_page(request, FORGOT_TEMPLATE, "Check your email", values={}, notice=LINK_SENT, sent=True)
    base = site_url(request)
    if not base:
        logger.error("Password reset email not sent: set SITE_URL in production")
    elif reset_email_limiter.allow(payload.email):
        # Sent after the response, so the reply takes the same time whether or
        # not the address has an account.
        response.background = BackgroundTask(_send_quietly, payload.email, base)
    return response


async def _send_quietly(email: str, base: str) -> None:
    try:
        await PasswordResetService().send_reset_link(email, base)
    except (RuntimeError, PyMongoError):
        logger.exception("Could not look up the account for a password reset")


@router.get("/reset-password")
async def reset_password_page(request: Request, token: str = ""):
    try:
        await PasswordResetService().check_link(token)
    except InvalidResetLinkError:
        return RedirectResponse("/forgot-password?expired=1", status_code=303)
    except (RuntimeError, PyMongoError):
        return await render_form_page(request, RESET_TEMPLATE, "Choose a new password", values={}, error=SERVICE_UNAVAILABLE, status_code=503)
    return await render_form_page(request, RESET_TEMPLATE, "Choose a new password", values={"token": token})


@router.post("/reset-password")
async def reset_password(request: Request):
    form = await read_form(request)
    values = {"token": form.get("token", "")}

    if not form_csrf_is_valid(request, form):
        return await render_form_page(request, RESET_TEMPLATE, "Choose a new password", values=values, error=FORM_EXPIRED, status_code=400)
    if not reset_password_limiter.allow(client_key(request)):
        return await render_form_page(request, RESET_TEMPLATE, "Choose a new password", values=values, error=TOO_MANY_ATTEMPTS, status_code=429)
    try:
        payload = PasswordResetInput(password=form.get("password", ""))
    except ValidationError as exc:
        return await render_form_page(request, RESET_TEMPLATE, "Choose a new password", values=values, field_errors=field_errors(exc), status_code=422)

    try:
        member = await PasswordResetService().reset_password(values["token"], payload.password, site_url(request))
    except InvalidResetLinkError:
        return RedirectResponse("/forgot-password?expired=1", status_code=303)
    except (RuntimeError, PyMongoError):
        return await render_form_page(request, RESET_TEMPLATE, "Choose a new password", values=values, error=SERVICE_UNAVAILABLE, status_code=503)

    response = RedirectResponse("/account?reset=1", status_code=303)
    set_member_cookie(response, member)  # carries the new session number
    return response

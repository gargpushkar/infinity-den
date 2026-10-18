import logging

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pymongo.errors import PyMongoError
from starlette.background import BackgroundTask

from app.routes.public.form_pages import FORM_EXPIRED, SERVICE_UNAVAILABLE, TOO_MANY_ATTEMPTS, render_form_page, site_url
from app.schemas.user import MemberRead
from app.services.email_confirmation_service import EmailConfirmationService, InvalidConfirmLinkError
from app.services.member_session import form_csrf_is_valid, get_current_member
from app.utils.forms import read_form
from app.utils.rate_limit import confirm_resend_limiter


logger = logging.getLogger(__name__)
router = APIRouter()

TEMPLATE = "pages/member_confirm_email.html"
TITLE = "Confirm your email"
LINK_INVALID = "This link has expired or doesn't match your account. Send yourself a new one below."


def send_confirmation_later(response, request: Request, member: MemberRead) -> None:
    """Send the link after the response, so a slow mail server never holds up the page."""
    base = site_url(request)
    if not base:
        logger.error("Email confirmation not sent: set SITE_URL in production")
        return
    response.background = BackgroundTask(EmailConfirmationService().send_link, member, base)


@router.get("/confirm-email")
async def confirm_email(request: Request, token: str = "", sent: bool = False):
    if token:
        try:
            await EmailConfirmationService().confirm(token)
        except InvalidConfirmLinkError:
            member = await get_current_member(request)
            if member is None:
                return RedirectResponse("/login?next=/confirm-email", status_code=303)
            return await render_form_page(request, TEMPLATE, TITLE, values={}, error=LINK_INVALID, member=member, status_code=400)
        except (RuntimeError, PyMongoError):
            return await render_form_page(request, TEMPLATE, TITLE, values={}, error=SERVICE_UNAVAILABLE, status_code=503)
        # The link proves the inbox, not who is at the keyboard, so it never signs anyone in.
        signed_in = await get_current_member(request)
        return RedirectResponse("/account?confirmed=1" if signed_in else "/login?confirmed=1", status_code=303)

    member = await get_current_member(request)
    if member is None:
        return RedirectResponse("/login?next=/confirm-email", status_code=303)
    if member.email_confirmed:
        return RedirectResponse("/account", status_code=303)
    notice = f"Welcome to Infinity Den. We've sent a link to {member.email}." if sent else None
    return await render_form_page(request, TEMPLATE, TITLE, values={}, notice=notice, member=member)


@router.post("/confirm-email")
async def resend_confirmation(request: Request):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse("/login?next=/confirm-email", status_code=303)
    if member.email_confirmed:
        return RedirectResponse("/account", status_code=303)

    form = await read_form(request)
    if not form_csrf_is_valid(request, form):
        return await render_form_page(request, TEMPLATE, TITLE, values={}, error=FORM_EXPIRED, member=member, status_code=400)
    if not confirm_resend_limiter.allow(member.id):
        return await render_form_page(request, TEMPLATE, TITLE, values={}, error=TOO_MANY_ATTEMPTS, member=member, status_code=429)

    response = await render_form_page(request, TEMPLATE, TITLE, values={}, notice=f"Sent. Check {member.email}, and your spam folder.", member=member)
    send_confirmation_later(response, request, member)
    return response

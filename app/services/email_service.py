"""Sending email over SMTP with the standard library (Brevo, or any provider).

Without SMTP_HOST the message is logged instead of sent, so development and
tests never send real email. In production the body is left out of that log,
because it may hold a sign-in link.
"""

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr

from app.config.settings import settings


logger = logging.getLogger(__name__)


class EmailError(Exception):
    pass


def build_message(to: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    sender_domain = parseaddr(settings.mail_from)[1].rpartition("@")[2] or None
    message["Message-ID"] = make_msgid(domain=sender_domain)
    if settings.contact_email:
        message["Reply-To"] = settings.contact_email  # nobody reads the no-reply inbox
    message.set_content(body)
    return message


def _send(message: EmailMessage) -> None:
    context = ssl.create_default_context()
    if settings.smtp_port == 465:
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15, context=context)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
    with server:
        if settings.smtp_port != 465:
            server.starttls(context=context)
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


async def send_email(to: str, subject: str, body: str) -> None:
    """Send one plain-text email. Raises EmailError if the provider refuses it."""
    message = build_message(to, subject, body)
    if not settings.smtp_host:
        if settings.app_env == "production":
            logger.warning("Email not sent (SMTP_HOST is not set): %r", subject)
        else:
            logger.info("Email not sent (SMTP_HOST is not set). To %s: %s\n\n%s", to, subject, body)
        return
    try:
        await asyncio.to_thread(_send, message)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailError(str(exc)) from exc

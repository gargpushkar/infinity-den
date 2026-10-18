"""Password reset: links work once, expire, can't be forged or reused as a
sign-in, and a reset signs out every other device."""

import asyncio
import re
from datetime import timedelta

import pytest
from bson import ObjectId
from starlette.requests import Request

from app.config.settings import settings
from app.models.user import USER_COLLECTION, UserDocument
from app.routes.public import form_pages as routes
from app.services import email_service, password_reset_service, user_service
from app.services.member_session import MEMBER_AUTH_COOKIE, create_member_token, get_current_member
from app.services.password_reset_service import InvalidResetLinkError, PasswordResetService, create_reset_token
from app.utils.security import create_access_token, hash_password, verify_password
from tests.fakes import FakeCollection


@pytest.fixture
def setup(monkeypatch):
    member = {"_id": ObjectId(), **UserDocument(username="mira", display_name="Mira", email="mira@example.org",
                                              password_hash=hash_password("old-password-123")).to_mongo()}
    database = {USER_COLLECTION: FakeCollection([member])}
    sent: list[tuple[str, str, str]] = []

    async def fake_send(to, subject, body):
        sent.append((to, subject, body))

    monkeypatch.setattr(password_reset_service, "send_email", fake_send)
    monkeypatch.setattr(user_service, "get_database", lambda: database)
    return PasswordResetService(database=database), database[USER_COLLECTION].documents[0], sent


def _link_token(sent) -> str:
    return re.search(r"/reset-password\?token=(\S+)", sent[-1][2]).group(1)


def _request_with_cookie(token: str) -> Request:
    return Request({"type": "http", "headers": [(b"cookie", f"{MEMBER_AUTH_COOKIE}={token}".encode())]})


def test_reset_link_works_once_and_signs_out_other_devices(setup):
    service, member, sent = setup
    old_session = create_member_token(user_service.MemberRead.model_validate(member))
    assert asyncio.run(get_current_member(_request_with_cookie(old_session))) is not None

    asyncio.run(service.send_reset_link(" Mira@Example.org ", "https://infinityden.test"))
    assert sent[0][0] == "mira@example.org" and "https://infinityden.test/reset-password?token=" in sent[0][2]
    token = _link_token(sent)

    updated = asyncio.run(service.reset_password(token, "new-password-456", "https://infinityden.test"))
    assert verify_password("new-password-456", member["password_hash"])
    assert updated.session_version == 1 and "was changed" in sent[-1][1]

    with pytest.raises(InvalidResetLinkError):  # the same link again
        asyncio.run(service.reset_password(token, "third-password-789", "https://infinityden.test"))
    assert asyncio.run(get_current_member(_request_with_cookie(old_session))) is None
    assert asyncio.run(get_current_member(_request_with_cookie(create_member_token(updated)))) is not None


def test_unknown_or_disabled_address_gets_no_email(setup):
    service, member, sent = setup
    asyncio.run(service.send_reset_link("nobody@example.org", "https://infinityden.test"))
    member["is_active"] = False
    asyncio.run(service.send_reset_link("mira@example.org", "https://infinityden.test"))
    assert sent == []


def test_expired_forged_and_sign_in_tokens_are_not_reset_links(setup):
    service, member, _ = setup
    member_id = str(member["_id"])
    expired = create_access_token(subject=member_id, secret_key=settings.auth_secret_key, expires_delta=timedelta(seconds=-1),
                                  claims={"kind": "password_reset", "pw": "x"})
    forged = create_reset_token(member_id, member["password_hash"]).rsplit(".", 1)[0] + ".bad-signature"
    sign_in = create_member_token(user_service.MemberRead.model_validate(member))
    for token in (expired, forged, sign_in, "", "not-a-token"):
        with pytest.raises(InvalidResetLinkError):
            asyncio.run(service.check_link(token))


def test_reset_link_is_not_a_sign_in_cookie(setup):
    _, member, _ = setup
    token = create_reset_token(str(member["_id"]), member["password_hash"])
    assert asyncio.run(get_current_member(_request_with_cookie(token))) is None


def test_links_ignore_the_host_header_in_production(monkeypatch):
    request = Request({"type": "http", "scheme": "https", "server": ("evil.example", 443), "path": "/", "headers": [(b"host", b"evil.example")]})
    monkeypatch.setattr(routes, "settings", type("S", (), {"site_url": "", "app_env": "production"})())
    assert routes.site_url(request) == ""
    monkeypatch.setattr(routes, "settings", type("S", (), {"site_url": "https://infinityden.com/", "app_env": "production"})())
    assert routes.site_url(request) == "https://infinityden.com"


def test_email_is_logged_not_sent_without_smtp(monkeypatch, caplog):
    def no_network(*_args, **_kwargs):
        raise AssertionError("tried to connect")

    monkeypatch.setattr(email_service.smtplib, "SMTP", no_network)
    caplog.set_level("INFO")
    asyncio.run(email_service.send_email("mira@example.org", "Hello", "Body text"))
    assert "Email not sent" in caplog.text


def test_message_headers():
    message = email_service.build_message("mira@example.org", "Subject", "Body")
    assert message["From"] == settings.mail_from and message["Reply-To"] == settings.contact_email
    assert message["Message-ID"].endswith("@infinityden.com>")

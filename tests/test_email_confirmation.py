"""Email confirmation: new members start unconfirmed and can't take part until
they open the link; unconfirmed sign-ups reserve nothing and expire."""

import asyncio
import re
from datetime import datetime, timezone

import pytest

from app.models.user import USER_COLLECTION
from app.schemas.user import MemberRead, MemberSignup
from app.services import email_confirmation_service as confirmation
from app.services.email_confirmation_service import EmailConfirmationService, InvalidConfirmLinkError, create_confirm_token
from app.services.member_session import create_member_token, unconfirmed_redirect
from app.services.password_reset_service import PasswordResetService, create_reset_token
from app.services.user_service import EmailTakenError, UserService
from tests.fakes import FakeCollection


def _signup(username="mira", email="mira@example.org") -> MemberSignup:
    return MemberSignup(username=username, display_name="Mira", email=email, password="a-long-password")


@pytest.fixture
def db():
    return {USER_COLLECTION: FakeCollection(unique=("email",))}


def test_new_member_is_unconfirmed_and_expires(db):
    member = asyncio.run(UserService(database=db).create_member(_signup()))
    stored = db[USER_COLLECTION].documents[0]
    assert member.email_confirmed is False and stored["email_confirmed"] is False
    days = (stored["pending_expires_at"] - datetime.now(timezone.utc)).days
    assert 6 <= days <= 7
    assert unconfirmed_redirect(member).headers["location"] == "/confirm-email"


def test_accounts_from_before_confirmation_count_as_confirmed():
    legacy = MemberRead.model_validate({"_id": "0123456789abcdef01234567", "username": "old", "display_name": "Old",
                                        "email": "old@example.org", "created_at": datetime.now(timezone.utc)})
    assert legacy.email_confirmed and unconfirmed_redirect(legacy) is None


def test_link_confirms_and_clears_the_expiry(db, monkeypatch):
    sent = []

    async def fake_send(to, subject, body):
        sent.append(body)

    monkeypatch.setattr(confirmation, "send_email", fake_send)
    member = asyncio.run(UserService(database=db).create_member(_signup()))
    asyncio.run(EmailConfirmationService(database=db).send_link(member, "https://infinityden.test"))
    token = re.search(r"/confirm-email\?token=(\S+)", sent[0]).group(1)

    confirmed = asyncio.run(EmailConfirmationService(database=db).confirm(token))
    assert confirmed.email_confirmed
    assert db[USER_COLLECTION].documents[0]["pending_expires_at"] is None
    assert asyncio.run(EmailConfirmationService(database=db).confirm(token)).email_confirmed  # twice is harmless


def test_other_tokens_are_not_confirmation_links(db):
    member = asyncio.run(UserService(database=db).create_member(_signup()))
    stored = db[USER_COLLECTION].documents[0]
    for token in (create_member_token(member), create_reset_token(member.id, stored["password_hash"]),
                  create_confirm_token(member.id, "someone-else@example.org"), "nonsense"):
        with pytest.raises(InvalidConfirmLinkError):
            asyncio.run(EmailConfirmationService(database=db).confirm(token))
    assert db[USER_COLLECTION].documents[0]["email_confirmed"] is False


def test_unconfirmed_sign_ups_reserve_nothing(db):
    users = UserService(database=db)
    first = asyncio.run(users.create_member(_signup(email="typo@example.org")))
    # Same username, corrected email: the unconfirmed account is replaced.
    second = asyncio.run(users.create_member(_signup(email="mira@example.org")))
    assert [d["email"] for d in db[USER_COLLECTION].documents] == ["mira@example.org"]
    assert first.id != second.id
    # A stranger's unconfirmed sign-up with your email doesn't block you.
    db[USER_COLLECTION].documents[0]["username"] = "stranger"
    asyncio.run(users.create_member(_signup(username="mira", email="mira@example.org")))
    assert [d["username"] for d in db[USER_COLLECTION].documents] == ["mira"]


def test_confirmed_accounts_are_never_replaced(db):
    users = UserService(database=db)
    asyncio.run(users.create_member(_signup()))
    db[USER_COLLECTION].documents[0]["email_confirmed"] = True
    with pytest.raises(EmailTakenError):
        asyncio.run(users.create_member(_signup(username="other")))
    assert len(db[USER_COLLECTION].documents) == 1


def test_unconfirmed_members_have_no_public_profile(db):
    users = UserService(database=db)
    asyncio.run(users.create_member(_signup()))
    assert asyncio.run(users.get_member_by_username("mira")) is None
    db[USER_COLLECTION].documents[0]["email_confirmed"] = True
    assert asyncio.run(users.get_member_by_username("mira")) is not None


def test_password_reset_also_confirms_the_email(db, monkeypatch):
    async def quiet(*_args):
        return None

    monkeypatch.setattr("app.services.password_reset_service.send_email", quiet)
    asyncio.run(UserService(database=db).create_member(_signup()))
    stored = db[USER_COLLECTION].documents[0]
    token = create_reset_token(str(stored["_id"]), stored["password_hash"])
    member = asyncio.run(PasswordResetService(database=db).reset_password(token, "another-long-password", "https://x.test"))
    assert member.email_confirmed and stored["pending_expires_at"] is None

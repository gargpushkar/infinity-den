"""Members request deletion; editors delete, removing everything the member
wrote. Editors' review decisions email the writer."""

import asyncio

import pytest
from bson import ObjectId

from app.models.article import ARTICLE_COLLECTION
from app.models.bookmark import BOOKMARK_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.models.comment import COMMENT_COLLECTION
from app.models.debate import ARGUMENT_COLLECTION
from app.models.question import RESPONSE_COLLECTION
from app.models.report import REPORT_COLLECTION
from app.models.user import USER_COLLECTION, UserDocument
from app.schemas.article import ArticleUpdate
from app.schemas.user import MemberRead
from app.services import cover_upload_service as covers
from app.services import review_email_service
from app.models.deletion_request import DELETION_REQUEST_COLLECTION
from app.schemas.user import MemberLogin
from app.services.account_deletion_service import DELETED_REPORTER, AccountDeletionService, WrongPasswordError, parse_emails
from app.services.user_service import DeletionRequestedError, InvalidCredentialsError, UserService
from app.services.member_article_service import MemberArticleService
from app.utils.security import hash_password
from tests.fakes import FakeCollection
from tests.test_member_publishing import _input


def _world(tmp_path):
    mira, other = ObjectId(), ObjectId()
    users = [
        {"_id": mira, **UserDocument(username="mira", display_name="Mira", email="mira@example.org", password_hash=hash_password("mira-password-1")).to_mongo()},
        {"_id": other, **UserDocument(username="omar", display_name="Omar", email="omar@example.org", password_hash=hash_password("omar-password-1")).to_mongo()},
    ]
    cover = "/media/covers/" + "c" * 32 + ".webp"
    (tmp_path / ("c" * 32 + ".webp")).write_bytes(b"x")
    piece, others_piece = ObjectId(), ObjectId()
    db = {
        USER_COLLECTION: FakeCollection(users),
        ARTICLE_COLLECTION: FakeCollection([
            {"_id": piece, "author_id": str(mira), "slug": "mine", "cover_image": cover},
            {"_id": others_piece, "author_id": str(other), "slug": "theirs"},
        ]),
        COMMENT_COLLECTION: FakeCollection([
            {"user_id": str(mira), "article_id": str(others_piece)},        # Mira's comment elsewhere
            {"user_id": str(other), "article_id": str(piece)},              # a comment on Mira's piece
            {"user_id": str(other), "article_id": str(others_piece)},       # unrelated, stays
        ]),
        RESPONSE_COLLECTION: FakeCollection([{"user_id": str(mira)}, {"user_id": str(other)}]),
        ARGUMENT_COLLECTION: FakeCollection([{"user_id": str(mira)}, {"user_id": str(other)}]),
        BOOKMARK_COLLECTION: FakeCollection([
            {"user_id": str(mira), "article_id": str(others_piece)},
            {"user_id": str(other), "article_id": str(piece)},             # someone saved Mira's piece
            {"user_id": str(other), "article_id": str(others_piece)},      # stays
        ]),
        REPORT_COLLECTION: FakeCollection([
            {"reporter_id": str(mira), "target_id": str(others_piece), "status": "open"},
            {"reporter_id": str(other), "target_id": str(piece), "status": "open"},
        ]),
        DELETION_REQUEST_COLLECTION: FakeCollection(),
    }
    return db, str(mira), str(other)


@pytest.fixture
def media(tmp_path, monkeypatch):
    monkeypatch.setattr(covers, "covers_dir", lambda: tmp_path)
    return tmp_path


def test_requesting_deletion_deactivates_but_deletes_nothing(media):
    db, mira, _ = _world(media)
    service = AccountDeletionService(database=db)
    asyncio.run(service.request(mira, "mira-password-1"))
    asyncio.run(service.request(mira, "mira-password-1"))  # asking twice makes one request
    account = next(u for u in db[USER_COLLECTION].documents if str(u["_id"]) == mira)
    assert account["is_active"] is False and account["deletion_requested_at"] and account["session_version"] == 2
    assert [r["status"] for r in db[DELETION_REQUEST_COLLECTION].documents] == ["pending"]
    assert len(db[ARTICLE_COLLECTION].documents) == 2 and list(media.iterdir())  # nothing removed yet
    assert asyncio.run(service.pending_count()) == 1


def test_signing_in_after_a_request_explains_why(media):
    db, mira, _ = _world(media)
    asyncio.run(AccountDeletionService(database=db).request(mira, "mira-password-1"))
    users = UserService(database=db)
    with pytest.raises(DeletionRequestedError):
        asyncio.run(users.authenticate(MemberLogin(email="mira@example.org", password="mira-password-1")))
    with pytest.raises(InvalidCredentialsError):  # a wrong password reveals nothing
        asyncio.run(users.authenticate(MemberLogin(email="mira@example.org", password="wrong-password")))


def test_editor_deletion_removes_everything_and_keeps_only_the_email(media):
    db, mira, other = _world(media)
    service = AccountDeletionService(database=db)
    asyncio.run(service.request(mira, "mira-password-1"))
    preview = asyncio.run(service.preview(parse_emails("MIRA@example.org, nobody@example.org\nmira@example.org")))
    assert [(row["email"], row["found"]) for row in preview] == [("mira@example.org", True), ("nobody@example.org", False)]
    assert preview[0]["pieces"] == 1 and preview[0]["arguments"] == 1 and preview[0]["requested"] is True
    assert len(db[USER_COLLECTION].documents) == 2  # previewing deletes nothing

    results = asyncio.run(service.delete_by_emails(["mira@example.org", "nobody@example.org"], editor="ed"))
    assert [(r["email"], r["deleted"]) for r in results] == [("mira@example.org", True), ("nobody@example.org", False)]
    assert results[0]["requested"] is True

    assert [str(u["_id"]) for u in db[USER_COLLECTION].documents] == [other]
    assert all(a["author_id"] == other for a in db[ARTICLE_COLLECTION].documents)
    assert len(db[COMMENT_COLLECTION].documents) == 1 and db[COMMENT_COLLECTION].documents[0]["user_id"] == other
    assert [r["user_id"] for r in db[RESPONSE_COLLECTION].documents] == [other]
    assert [a["user_id"] for a in db[ARGUMENT_COLLECTION].documents] == [other]
    assert len(db[BOOKMARK_COLLECTION].documents) == 1
    assert not list(media.iterdir())
    filed, about_mira = db[REPORT_COLLECTION].documents
    assert filed["reporter_id"] == DELETED_REPORTER and about_mira["status"] == "resolved"
    request = db[DELETION_REQUEST_COLLECTION].documents[0]
    assert request["status"] == "deleted" and request["handled_by"] == "ed"
    assert request["email"] == "mira@example.org" and request["username"] is None and request["display_name"] is None


def test_editors_can_delete_accounts_that_did_not_ask(media):
    db, _, other = _world(media)
    service = AccountDeletionService(database=db)
    asyncio.run(service.request(other, "omar-password-1"))  # asked once, then changed their mind
    asyncio.run(service.cancel(str(db[DELETION_REQUEST_COLLECTION].documents[0]["_id"]), "ed"))
    results = asyncio.run(service.delete_by_emails(["omar@example.org"], editor="ed"))
    assert results[0]["deleted"] and results[0]["requested"] is False
    assert other not in [str(u["_id"]) for u in db[USER_COLLECTION].documents]
    cancelled = db[DELETION_REQUEST_COLLECTION].documents[0]
    assert cancelled["status"] == "cancelled" and cancelled["username"] is None and cancelled["display_name"] is None


def test_cancelling_a_request_reactivates_the_account(media):
    db, mira, _ = _world(media)
    service = AccountDeletionService(database=db)
    asyncio.run(service.request(mira, "mira-password-1"))
    request_id = str(db[DELETION_REQUEST_COLLECTION].documents[0]["_id"])
    assert asyncio.run(service.cancel(request_id, "ed"))
    account = next(u for u in db[USER_COLLECTION].documents if str(u["_id"]) == mira)
    assert account["is_active"] is True and account["deletion_requested_at"] is None
    assert db[DELETION_REQUEST_COLLECTION].documents[0]["status"] == "cancelled"
    assert not asyncio.run(service.cancel(request_id, "ed"))  # already handled


def test_wrong_password_requests_nothing(media):
    db, mira, _ = _world(media)
    for password in ("wrong-password", "omar-password-1", ""):
        with pytest.raises(WrongPasswordError):
            asyncio.run(AccountDeletionService(database=db).request(mira, password))
    assert db[DELETION_REQUEST_COLLECTION].documents == []
    assert all(u["is_active"] for u in db[USER_COLLECTION].documents)


def test_parse_emails_accepts_any_separator():
    assert parse_emails(" A@x.org,b@x.org;\n\na@x.org  c@x.org ") == ["a@x.org", "b@x.org", "c@x.org"]


@pytest.fixture
def review(monkeypatch):
    sent = []

    async def fake_send(to, subject, body):
        sent.append((to, subject, body))

    monkeypatch.setattr(review_email_service, "send_email", fake_send)
    member_id = "0123456789abcdef01234567"
    db = {
        USER_COLLECTION: FakeCollection([{"_id": ObjectId(member_id), "display_name": "Mira", "email": "mira@example.org", "is_active": True}]),
        ARTICLE_COLLECTION: FakeCollection(),
        CATEGORY_COLLECTION: FakeCollection([{"slug": "personal-stories"}]),
    }
    service = MemberArticleService(database=db)
    member = MemberRead(_id=member_id, username="mira", display_name="Mira", email="mira@example.org", created_at="2026-10-18T00:00:00Z")
    piece = asyncio.run(service.save(member, _input(), submit=True))
    return service, member, piece, sent


def test_publishing_a_member_piece_emails_the_writer(review):
    service, _, piece, sent = review
    assert sent == []  # submitting for review sends nothing
    asyncio.run(service.articles.update_article(piece.id, ArticleUpdate(status="published")))
    assert sent[0][0] == "mira@example.org" and "published" in sent[0][1] and f"/articles/{piece.slug}" in sent[0][2]
    asyncio.run(service.articles.update_article(piece.id, ArticleUpdate(status="published", title="Retitled piece")))
    assert len(sent) == 1  # saving a published piece again doesn't repeat it


def test_sending_back_emails_the_note_but_member_saves_do_not(review):
    service, member, piece, sent = review
    asyncio.run(service.articles.update_article(piece.id, ArticleUpdate(status="draft", review_note="Add a source for the 1987 figure.")))
    assert "needs a few changes" in sent[0][1] and "Add a source for the 1987 figure." in sent[0][2] and f"/write/{piece.id}" in sent[0][2]
    asyncio.run(service.save(member, _input(), submit=False, article_id=piece.id))
    assert len(sent) == 1


def test_editorial_pieces_send_no_email(review):
    service, _, _, sent = review
    service.database[ARTICLE_COLLECTION].documents.append({"_id": ObjectId(), "author_id": None, "status": "draft", "title": "Editorial",
                                                           "slug": "editorial", "excerpt": "An editorial piece.", "content": "Body",
                                                           "author": "Editors", "created_at": "2026-10-18T00:00:00Z", "updated_at": "2026-10-18T00:00:00Z"})
    editorial_id = str(service.database[ARTICLE_COLLECTION].documents[-1]["_id"])
    asyncio.run(service.articles.update_article(editorial_id, ArticleUpdate(status="published")))
    assert sent == []

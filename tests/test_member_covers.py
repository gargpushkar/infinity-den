"""Cover images: uploads are re-encoded without metadata, links are https only,
and a replaced upload is deleted once nothing uses it."""

import asyncio
import io

import pytest
from PIL import Image

from app.middleware.security_headers import MAX_BODY_BYTES, UPLOAD_BODY_BYTES, body_limit
from app.routes.public import write
from app.services import cover_upload_service as covers
from app.services.cover_upload_service import CoverError, cover_link, discard_unused_cover
from tests.test_member_publishing import _input, _member, _service, _stored


GPS_TAG = 0x8825


def _photo(fmt="JPEG", size=(3000, 2000)) -> bytes:
    image = Image.new("RGB", size, (194, 86, 47))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # camera make
    exif.get_ifd(GPS_TAG)[2] = (40.0, 44.0, 54.0)  # latitude
    output = io.BytesIO()
    image.save(output, fmt, exif=exif)
    return output.getvalue()


@pytest.fixture
def media(tmp_path, monkeypatch):
    monkeypatch.setattr(covers, "covers_dir", lambda: tmp_path)
    return tmp_path


def test_upload_is_resized_and_loses_its_location(media):
    url = asyncio.run(covers.save_cover_upload(_photo()))
    assert covers.UPLOADED_COVER.match(url)
    with Image.open(media / url.rsplit("/", 1)[1]) as stored:
        assert stored.format == "WEBP" and max(stored.size) == 1600
        assert not stored.getexif() and "exif" not in stored.info


@pytest.mark.parametrize(
    "data",
    [b"<svg xmlns='http://www.w3.org/2000/svg'/>", b"not an image", _photo("GIF", (10, 10)),
     b"\xff\xd8" + b"0" * (covers.MAX_UPLOAD_BYTES + 1)],
    ids=["svg", "text", "gif", "too-big"],
)
def test_only_real_images_within_the_limit_are_accepted(media, data):
    with pytest.raises(CoverError):
        asyncio.run(covers.save_cover_upload(data))
    assert not list(media.iterdir())


@pytest.mark.parametrize("link", ["http://example.org/a.jpg", "javascript:alert(1)", "/media/covers/x.webp", "https://", "https://host/ space.jpg"])
def test_cover_links_must_be_https(link):
    with pytest.raises(CoverError):
        cover_link(link)


def test_https_cover_link_is_kept():
    assert cover_link(" https://images.example.org/photo.jpg ") == "https://images.example.org/photo.jpg"


def test_member_cover_choice():
    upload = "/media/covers/" + "a" * 32 + ".webp"
    choose = lambda current, link="", remove=False: asyncio.run(
        write._chosen_cover(current, {"cover_url": link, "cover_remove": remove}, None))
    assert choose(upload) == upload  # untouched form keeps the uploaded cover
    assert choose(upload, remove=True) is None
    assert choose(upload, link="https://example.org/b.jpg") == "https://example.org/b.jpg"
    assert choose("https://example.org/b.jpg") is None  # the member cleared the link


def test_replaced_upload_is_deleted_only_when_unused(media):
    service = _service()
    first = asyncio.run(covers.save_cover_upload(_photo()))
    piece = asyncio.run(service.save(_member(), _input(), submit=False, cover_image=first))
    assert _stored(service)[0]["cover_image"] == first

    # Another article still using the file keeps it on disk.
    _stored(service).append({"slug": "copy", "cover_image": first})
    asyncio.run(service.save(_member(), _input(), submit=False, article_id=piece.id, cover_image=None))
    assert (media / first.rsplit("/", 1)[1]).exists()

    _stored(service).pop()
    asyncio.run(discard_unused_cover(service.database, first))
    assert not (media / first.rsplit("/", 1)[1]).exists()


def test_deleting_an_article_deletes_its_upload(media):
    service = _service()
    url = asyncio.run(covers.save_cover_upload(_photo()))
    piece = asyncio.run(service.save(_member(), _input(), submit=False, cover_image=url))
    assert asyncio.run(service.articles.delete_article(piece.id))
    assert not list(media.iterdir())


def test_discard_ignores_paths_that_are_not_uploads(media):
    (media / "keep.webp").write_bytes(b"x")
    for url in ("/media/covers/../keep.webp", "/static/images/brand/og-default.png", "https://example.org/x.webp"):
        asyncio.run(discard_unused_cover({}, url))
    assert (media / "keep.webp").exists()


def test_only_upload_pages_accept_large_bodies():
    assert body_limit("/write") == body_limit("/write/abc123") == body_limit("/api/admin/covers") == UPLOAD_BODY_BYTES
    assert body_limit("/api/articles") == body_limit("/write/abc/extra") == MAX_BODY_BYTES

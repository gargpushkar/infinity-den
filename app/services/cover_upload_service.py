"""Cover images people upload or link to.

Every upload is re-encoded: resized to at most MAX_SIDE pixels, saved as WebP,
and stripped of metadata (phone photos carry the GPS position they were taken
at). Files live in MEDIA_DIR/covers and are served at /media/covers/.
"""

import asyncio
import io
import re
import secrets
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config.settings import settings
from app.models.article import ARTICLE_COLLECTION


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_SIDE = 1600
MAX_PIXELS = 40_000_000  # refuses "decompression bombs" before decoding them
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MEDIA_URL = "/media"
UPLOADED_COVER = re.compile(r"^/media/covers/[0-9a-f]{32}\.webp$")


class CoverError(ValueError):
    pass


def covers_dir() -> Path:
    return Path(settings.media_dir) / "covers"


def cover_link(url: str) -> str:
    """A pasted cover link: https only, so pages never load mixed content."""
    url = url.strip()
    if not re.match(r"^https://[^\s/]+\.[^\s/]+/\S*$", url) or len(url) > 500:
        raise CoverError("Paste a link that starts with https://, or upload an image instead.")
    return url


def _encode(data: bytes) -> bytes:
    if len(data) > MAX_UPLOAD_BYTES:
        raise CoverError("That image is over 5 MB. Choose a smaller one.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in ALLOWED_FORMATS:
                raise CoverError("Upload a JPEG, PNG, or WebP image.")
            if image.width * image.height > MAX_PIXELS:
                raise CoverError("That image is too large. Choose a smaller one.")
            image = ImageOps.exif_transpose(image)  # keep phone photos upright once the metadata is gone
            image.thumbnail((MAX_SIDE, MAX_SIDE))
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB")
            output = io.BytesIO()
            image.save(output, "WEBP", quality=82, method=4)  # no exif/icc passed, so none is written
            return output.getvalue()
    except CoverError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise CoverError("That file isn't an image we can read. Upload a JPEG, PNG, or WebP image.") from exc


def _write(encoded: bytes) -> str:
    folder = covers_dir()
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{secrets.token_hex(16)}.webp"
    (folder / name).write_bytes(encoded)
    return f"{MEDIA_URL}/covers/{name}"


async def save_cover_upload(data: bytes) -> str:
    """Store an uploaded image; returns its /media URL. Raises CoverError."""
    encoded = await asyncio.to_thread(_encode, data)
    return await asyncio.to_thread(_write, encoded)


async def discard_unused_cover(database: Any, url: str | None) -> None:
    """Delete an uploaded cover file once no article uses it any more."""
    if not url or not UPLOADED_COVER.match(url):
        return
    if await database[ARTICLE_COLLECTION].count_documents({"cover_image": url}, limit=1):
        return
    (covers_dir() / url.rsplit("/", 1)[1]).unlink(missing_ok=True)

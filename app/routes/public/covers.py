from fastapi import APIRouter, HTTPException, Path, Response
from fastapi import status as http_status

from app.utils.covers import PATTERNS, cover_svg


router = APIRouter()

# The drawing depends only on the URL, so browsers can keep it for a year;
# cover_url() adds ?v= so a new COVER_VERSION reaches everyone.
CACHE_HEADERS = {
    "Cache-Control": "public, max-age=31536000, immutable",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
}


@router.get("/covers/{room}/{slug}.svg", include_in_schema=False)
async def cover(
    room: str = Path(max_length=40),
    slug: str = Path(pattern=r"^[a-z0-9][a-z0-9-]{0,159}$"),
) -> Response:
    if room not in PATTERNS:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Cover was not found.")
    return Response(cover_svg(room, slug), media_type="image/svg+xml", headers=CACHE_HEADERS)

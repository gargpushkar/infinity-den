from urllib.parse import parse_qs

from fastapi import HTTPException, Request
from fastapi import status as http_status


MAX_FORM_BYTES = 64 * 1024


async def read_form(request: Request) -> dict[str, str]:
    """Parse a plain (urlencoded) HTML form with the standard library.

    Covers text-only forms without the python-multipart dependency; forms
    with file uploads would need it. Keeps the first value of each field.
    """
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_FORM_BYTES:
            raise HTTPException(
                status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Form is too large.",
            )

    fields = parse_qs(bytes(body).decode("utf-8", errors="replace"), keep_blank_values=True)
    return {name: values[0] for name, values in fields.items()}

from urllib.parse import parse_qs

from fastapi import HTTPException, Request
from fastapi import status as http_status


MAX_FORM_BYTES = 64 * 1024


async def read_form(request: Request) -> dict[str, str]:
    """Parse a plain (urlencoded) HTML form with the standard library.

    For text-only forms; forms with a file use read_upload_form. Keeps the
    first value of each field.
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


async def read_upload_form(request: Request, file_field: str, max_file_bytes: int) -> tuple[dict[str, str], bytes | None]:
    """A multipart form with at most one file: (text fields, the file's bytes or None).

    Reads at most max_file_bytes + 1 of the file, so the caller can tell it is too big.
    """
    form = await request.form(max_files=1, max_fields=50, max_part_size=256 * 1024)
    fields: dict[str, str] = {}
    for name, value in form.multi_items():
        if isinstance(value, str):
            fields.setdefault(name, value)
    upload = form.get(file_field)
    data = await upload.read(max_file_bytes + 1) if upload is not None and not isinstance(upload, str) else None
    await form.close()
    return fields, data or None

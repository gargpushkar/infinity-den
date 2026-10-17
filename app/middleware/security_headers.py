"""Security headers on every response, and a cap on request bodies.

The templates have no inline scripts or styles, so the Content Security Policy
can allow scripts and styles only from this site and jsDelivr (Bootstrap).
Fonts are served from this site. JSON-LD blocks are data, not scripts, so CSP does not block them.
"""

import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' https://cdn.jsdelivr.net",
        "style-src 'self' https://cdn.jsdelivr.net",
        "font-src 'self'",
        "img-src 'self' data: https:",  # uploaded covers may live on other https hosts
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
# FastAPI's interactive docs load their own inline scripts.
DOCS_PATHS = ("/docs", "/redoc")

# Forms are already capped at 64 KB in app/utils/forms.py; this covers JSON too.
# ponytail: trusts Content-Length; a chunked upload without one is not counted.
MAX_BODY_BYTES = 1024 * 1024
# Pages that take a cover upload (5 MB image plus the rest of the form).
UPLOAD_BODY_BYTES = 6 * 1024 * 1024
UPLOAD_PATHS = re.compile(r"^(/write(/[^/]+)?|/api/admin/covers)$")


def body_limit(path: str) -> int:
    return UPLOAD_BODY_BYTES if UPLOAD_PATHS.match(path) else MAX_BODY_BYTES


def register_security_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > body_limit(request.url.path):
            return JSONResponse(
                status_code=413,
                content={"error": {"type": "request_too_large", "status_code": 413, "message": "That request is too large."}},
            )

        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            if header == "Content-Security-Policy" and request.url.path.startswith(DOCS_PATHS):
                continue
            response.headers.setdefault(header, value)  # covers keep their stricter policy
        return response

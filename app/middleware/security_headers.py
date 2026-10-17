"""Security headers on every response, and a cap on request bodies.

The templates have no inline scripts or styles, so the Content Security Policy
can allow scripts and styles only from this site, jsDelivr (Bootstrap), and
Google Fonts. JSON-LD blocks are data, not scripts, so CSP does not block them.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' https://cdn.jsdelivr.net",
        "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
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


def register_security_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_BODY_BYTES:
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

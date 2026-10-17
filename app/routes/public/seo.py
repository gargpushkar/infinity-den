from fastapi import Request


def social_image_url(request: Request, image_url: str | None) -> str:
    """An absolute URL for og:image, or "" to use the site's default preview.

    Facebook, LinkedIn and X do not show SVG previews, so generated covers
    (and any other SVG) fall back to the branded PNG in the base layout.
    """
    clean_image_url = str(image_url or "").strip()
    if not clean_image_url or clean_image_url.split("?", 1)[0].endswith(".svg"):
        return ""
    if clean_image_url.startswith(("http://", "https://")):
        return clean_image_url
    if clean_image_url.startswith("/static/"):
        return str(request.url_for("static", path=clean_image_url.removeprefix("/static/")))
    return f"{str(request.base_url).rstrip('/')}/{clean_image_url.lstrip('/')}"

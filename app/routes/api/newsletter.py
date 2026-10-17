from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http_status

from app.schemas.newsletter import (
    NewsletterSubscriptionCreate,
    NewsletterSubscriptionResponse,
)
from app.services.newsletter_service import (
    NewsletterService,
    NewsletterSubscriberConflictError,
    get_newsletter_service,
)
from app.utils.rate_limit import client_key, newsletter_limiter


router = APIRouter(prefix="/api/newsletter", tags=["Newsletter"])

SUBSCRIBED = "You're on the list."


def get_public_newsletter_service() -> NewsletterService:
    return get_newsletter_service()


@router.post(
    "/subscribe",
    response_model=NewsletterSubscriptionResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def subscribe_to_newsletter(
    request: Request,
    payload: NewsletterSubscriptionCreate,
    newsletter_service: NewsletterService = Depends(get_public_newsletter_service),
) -> NewsletterSubscriptionResponse:
    if not newsletter_limiter.allow(client_key(request)):
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
        )
    try:
        await newsletter_service.create_subscription(payload)
    except NewsletterSubscriberConflictError:
        # Same answer either way, so nobody can test whose email is on the list.
        pass
    return NewsletterSubscriptionResponse(message=SUBSCRIBED)

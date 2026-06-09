from fastapi import APIRouter, Depends, HTTPException
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


router = APIRouter(prefix="/api/newsletter", tags=["Newsletter"])


def get_public_newsletter_service() -> NewsletterService:
    return get_newsletter_service()


@router.post(
    "/subscribe",
    response_model=NewsletterSubscriptionResponse,
    response_model_by_alias=False,
    status_code=http_status.HTTP_201_CREATED,
)
async def subscribe_to_newsletter(
    payload: NewsletterSubscriptionCreate,
    newsletter_service: NewsletterService = Depends(get_public_newsletter_service),
) -> NewsletterSubscriptionResponse:
    try:
        subscriber = await newsletter_service.create_subscription(payload)
    except NewsletterSubscriberConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="This email is already subscribed.",
        ) from exc

    return NewsletterSubscriptionResponse(
        subscriber=subscriber,
        message="Newsletter subscription created.",
    )

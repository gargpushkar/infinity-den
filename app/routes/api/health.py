from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.services.health_service import get_health_status, is_unhealthy


router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    health_status = await get_health_status()
    response_status = (
        status.HTTP_503_SERVICE_UNAVAILABLE
        if is_unhealthy(health_status)
        else status.HTTP_200_OK
    )

    return JSONResponse(health_status, status_code=response_status)

from datetime import UTC, datetime
from typing import Any

from pymongo.errors import PyMongoError

from app.config.settings import settings
from app.database.mongodb import mongodb


async def get_health_status() -> dict[str, Any]:
    mongodb_health = await _get_mongodb_health()
    app_status = _get_app_status(mongodb_health["status"])

    return {
        "status": app_status,
        "service": settings.app_name,
        "environment": settings.app_env,
        "timestamp": datetime.now(UTC).isoformat(),
        "components": {
            "mongodb": mongodb_health,
        },
    }


def is_unhealthy(health_status: dict[str, Any]) -> bool:
    return health_status["status"] == "unhealthy"


async def _get_mongodb_health() -> dict[str, str]:
    if mongodb.database is None:
        return {
            "status": "unavailable",
            "message": "MongoDB connection is not initialized.",
        }

    try:
        await mongodb.database.command("ping")
    except PyMongoError as exc:
        return {
            "status": "unavailable",
            "message": str(exc),
        }

    return {
        "status": "ok",
        "message": "MongoDB connection is healthy.",
    }


def _get_app_status(mongodb_status: str) -> str:
    if mongodb_status == "ok":
        return "ok"
    if settings.mongodb_required:
        return "unhealthy"
    return "degraded"

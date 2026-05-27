import uvicorn

from app.config.logging_config import configure_logging
from app.config.settings import settings


if __name__ == "__main__":
    configure_logging()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )

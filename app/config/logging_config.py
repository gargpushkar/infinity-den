import logging
from logging.config import dictConfig

from app.config.settings import settings


LOG_FORMATS = {
    "plain": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    "detailed": "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
}


def configure_logging() -> None:
    log_level = settings.log_level.upper()
    if not isinstance(logging.getLevelName(log_level), int):
        log_level = "INFO"

    log_format = LOG_FORMATS.get(settings.log_format.lower(), LOG_FORMATS["plain"])

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": log_format,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": log_level,
                },
            },
            "root": {
                "handlers": ["console"],
                "level": log_level,
            },
            "loggers": {
                "app": {
                    "handlers": ["console"],
                    "level": log_level,
                    "propagate": False,
                },
                "uvicorn": {
                    "handlers": ["console"],
                    "level": log_level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["console"],
                    "level": log_level,
                    "propagate": False,
                },
            },
        }
    )

from dataclasses import dataclass

from starlette.config import Config


config = Config(".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = config("APP_NAME", default="Infinity Den")
    app_env: str = config("APP_ENV", default="development")
    debug: bool = config("DEBUG", cast=bool, default=False)
    host: str = config("HOST", default="127.0.0.1")
    port: int = config("PORT", cast=int, default=8000)
    log_level: str = config("LOG_LEVEL", default="INFO")
    log_format: str = config("LOG_FORMAT", default="plain")
    mongodb_uri: str = config("MONGODB_URI", default="mongodb://localhost:27017")
    mongodb_db_name: str = config("MONGODB_DB_NAME", default="infinity_den")
    mongodb_required: bool = config("MONGODB_REQUIRED", cast=bool, default=False)
    mongodb_server_selection_timeout_ms: int = config(
        "MONGODB_SERVER_SELECTION_TIMEOUT_MS",
        cast=int,
        default=2000,
    )
    auth_secret_key: str = config("AUTH_SECRET_KEY", default="")
    auth_token_expire_minutes: int = config(
        "AUTH_TOKEN_EXPIRE_MINUTES",
        cast=int,
        default=60,
    )
    auth_cookie_secure: bool = config(
        "AUTH_COOKIE_SECURE",
        cast=bool,
        default=False,
    )


settings = Settings()

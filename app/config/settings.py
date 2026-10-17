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
    # Decides when "today's question" changes. The audience is US-based.
    site_timezone: str = config("SITE_TIMEZONE", default="America/New_York")
    member_token_expire_days: int = config(
        "MEMBER_TOKEN_EXPIRE_DAYS",
        cast=int,
        default=30,
    )
    # The public address used in emailed links (https://infinityden.com in
    # production), never the request's Host header, which a visitor controls.
    site_url: str = config("SITE_URL", default="")
    # Outgoing email over SMTP (Brevo: smtp-relay.brevo.com, port 587 or 2525).
    # Without SMTP_HOST, emails are written to the log instead of sent.
    smtp_host: str = config("SMTP_HOST", default="")
    smtp_port: int = config("SMTP_PORT", cast=int, default=587)
    smtp_username: str = config("SMTP_USERNAME", default="")
    smtp_password: str = config("SMTP_PASSWORD", default="")
    mail_from: str = config("MAIL_FROM", default="Infinity Den <noreply@infinityden.com>")
    # Shown in the footer and the policy pages for questions and data requests.
    contact_email: str = config("CONTACT_EMAIL", default="gargpushkar96@gmail.com")
    # Uploaded images. Keep it outside the code checkout on servers, and back it up.
    media_dir: str = config("MEDIA_DIR", default="media")
    auth_cookie_secure: bool = config(
        "AUTH_COOKIE_SECURE",
        cast=bool,
        default=False,
    )


settings = Settings()

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any


JWT_ALGORITHM = "HS256"
PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 210_000
PASSWORD_SALT_BYTES = 16
CSRF_TOKEN_BYTES = 32


class SecurityError(Exception):
    pass


class TokenValidationError(SecurityError):
    pass


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )

    return "$".join(
        [
            PASSWORD_HASH_ALGORITHM,
            str(PASSWORD_HASH_ITERATIONS),
            _base64url_encode(salt),
            _base64url_encode(digest),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False

        iterations = int(iterations_text)
        salt = _base64url_decode(salt_text)
        expected_digest = _base64url_decode(digest_text)
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(
    *,
    subject: str,
    secret_key: str,
    expires_delta: timedelta,
    claims: dict[str, Any] | None = None,
) -> str:
    if not secret_key:
        raise SecurityError("AUTH_SECRET_KEY must be configured.")

    now = datetime.now(timezone.utc)
    expires_at = now + expires_delta
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        **(claims or {}),
    }
    encoded_header = _base64url_json(header)
    encoded_payload = _base64url_json(payload)
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = _sign(signing_input, secret_key)

    return f"{signing_input}.{signature}"


def decode_access_token(token: str, secret_key: str) -> dict[str, Any]:
    if not secret_key:
        raise TokenValidationError("AUTH_SECRET_KEY must be configured.")

    try:
        encoded_header, encoded_payload, signature = token.split(".", 2)
    except ValueError as exc:
        raise TokenValidationError("Token format is invalid.") from exc

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = _sign(signing_input, secret_key)
    if not hmac.compare_digest(signature, expected_signature):
        raise TokenValidationError("Token signature is invalid.")

    try:
        header = json.loads(_base64url_decode(encoded_header))
        payload = json.loads(_base64url_decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise TokenValidationError("Token payload is invalid.") from exc

    if header.get("alg") != JWT_ALGORITHM:
        raise TokenValidationError("Token algorithm is invalid.")

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int):
        raise TokenValidationError("Token expiration is missing.")
    if datetime.now(timezone.utc).timestamp() >= expires_at:
        raise TokenValidationError("Token has expired.")

    return payload


def create_csrf_token(secret_key: str) -> str:
    if not secret_key:
        raise SecurityError("AUTH_SECRET_KEY must be configured.")

    nonce = _base64url_encode(secrets.token_bytes(CSRF_TOKEN_BYTES))
    signature = _sign(nonce, secret_key)

    return f"{nonce}.{signature}"


def verify_csrf_token(token: str, secret_key: str) -> bool:
    if not secret_key:
        raise SecurityError("AUTH_SECRET_KEY must be configured.")

    try:
        nonce, signature = token.split(".", 1)
    except ValueError:
        return False

    expected_signature = _sign(nonce, secret_key)

    return hmac.compare_digest(signature, expected_signature)


def _sign(signing_input: str, secret_key: str) -> str:
    digest = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return _base64url_encode(digest)


def _base64url_json(value: dict[str, Any]) -> str:
    payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _base64url_encode(payload)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)

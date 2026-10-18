from collections import deque
from time import monotonic

from fastapi import Request


class RateLimiter:
    """Allow at most `limit` attempts per key within `window_seconds`.

    ponytail: counters live in this process's memory, so they reset on restart
    and are not shared between workers. Move them to MongoDB (a TTL-indexed
    collection) or Redis before running more than one server process.
    """

    def __init__(self, *, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = {}

    def allow(self, key: str, *, now: float | None = None) -> bool:
        now = monotonic() if now is None else now
        cutoff = now - self.window_seconds
        attempts = self._attempts.setdefault(key, deque())
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

        if len(attempts) >= self.limit:
            return False

        attempts.append(now)
        return True


def client_key(request: Request) -> str:
    # ponytail: the direct peer address. Behind a reverse proxy this is the
    # proxy, so read the forwarded client address there instead.
    return request.client.host if request.client else "unknown"


member_login_limiter = RateLimiter(limit=10, window_seconds=15 * 60)
newsletter_limiter = RateLimiter(limit=5, window_seconds=60 * 60)
member_signup_limiter = RateLimiter(limit=5, window_seconds=60 * 60)
admin_login_limiter = RateLimiter(limit=10, window_seconds=15 * 60)
# Reset emails: per IP, and per address so one inbox can't be flooded.
reset_request_limiter = RateLimiter(limit=5, window_seconds=60 * 60)
reset_email_limiter = RateLimiter(limit=3, window_seconds=60 * 60)
reset_password_limiter = RateLimiter(limit=10, window_seconds=15 * 60)
confirm_resend_limiter = RateLimiter(limit=3, window_seconds=60 * 60)  # per member
account_delete_limiter = RateLimiter(limit=5, window_seconds=15 * 60)  # per member: password guesses
# Keyed by member id rather than IP: these protect editors' review time.
member_submit_limiter = RateLimiter(limit=5, window_seconds=60 * 60)
member_save_limiter = RateLimiter(limit=30, window_seconds=60 * 60)
member_response_limiter = RateLimiter(limit=10, window_seconds=60 * 60)
member_comment_limiter = RateLimiter(limit=10, window_seconds=60 * 60)
member_report_limiter = RateLimiter(limit=10, window_seconds=60 * 60)
member_argument_limiter = RateLimiter(limit=10, window_seconds=60 * 60)

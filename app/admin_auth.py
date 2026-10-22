"""Login for /admin and /demo: one password from .env and a signed cookie.

Cookie value: "<expiry unix time>.<HMAC-SHA256 of 'admin:<expiry>' with COOKIE_SECRET>".
Without COOKIE_SECRET nobody can make a valid cookie, and it stops working after 8 hours.
"""

import hashlib
import hmac
import time

COOKIE_NAME = "pixelkiln_admin"
LIFETIME_S = 8 * 3600


def _signature(secret: str, expiry: int) -> str:
    return hmac.new(secret.encode(), f"admin:{expiry}".encode(), hashlib.sha256).hexdigest()


def make_token(secret: str, now: float | None = None) -> str:
    expiry = int((now or time.time()) + LIFETIME_S)
    return f"{expiry}.{_signature(secret, expiry)}"


def token_valid(token: str | None, secret: str, now: float | None = None) -> bool:
    if not token or "." not in token:
        return False
    expiry_text, signature = token.split(".", 1)
    if not expiry_text.isdigit() or int(expiry_text) < (now or time.time()):
        return False
    # compare_digest takes the same time for any input, so the signature cannot be guessed byte by byte
    return hmac.compare_digest(signature, _signature(secret, int(expiry_text)))


def password_ok(given: str, expected: str) -> bool:
    return hmac.compare_digest(given.encode(), expected.encode())

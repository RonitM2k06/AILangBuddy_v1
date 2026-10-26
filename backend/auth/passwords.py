"""Password hashing with scrypt from the standard library (no extra dependency).

Stored format: scrypt$N$r$p$salt_b64$hash_b64. Parameters are stored per hash so they can be
raised later without invalidating existing passwords.
"""
import base64
import hashlib
import hmac
import os

N, R, P = 2**15, 8, 1
SALT_BYTES = 16
KEY_BYTES = 32
MAXMEM = 128 * 1024 * 1024


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=KEY_BYTES, maxmem=MAXMEM)


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    key = _derive(password, salt, N, R, P)
    return "$".join(["scrypt", str(N), str(R), str(P), base64.b64encode(salt).decode(), base64.b64encode(key).decode()])


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, key_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(key_b64)
        actual = _derive(password, base64.b64decode(salt_b64), int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)

"""RFC 6238 TOTP with the standard library (Phase 14D): HMAC-SHA1, 6 digits, 30-second steps, one step of clock drift either way.

Time is whole UNIX seconds (an int): the step is seconds // 30, with no floating point anywhere. A code is exactly six ASCII digits;
anything else (spaces, other digits, other lengths) is refused before any comparison. Comparisons are constant-time."""
import base64
import hashlib
import hmac
import re
import secrets
import struct
from urllib.parse import quote

from .. import settings

_CODE = re.compile(r"[0-9]{6}")          # ASCII only: \\d would also match other scripts' digits


def new_secret() -> bytes:
    return secrets.token_bytes(settings.TOTP_SECRET_BYTES)


def b32(secret: bytes) -> str:
    """The secret as authenticator apps expect it: base32, no padding."""
    return base64.b32encode(secret).decode("ascii").rstrip("=")


def step_at(unix_seconds: int) -> int:
    return int(unix_seconds) // settings.TOTP_PERIOD_SECONDS


def generate_totp(secret: bytes, timestep: int, digits: int = None) -> str:
    """The code for one time step (RFC 4226 HOTP over the step counter)."""
    digits = settings.TOTP_DIGITS if digits is None else digits
    mac = hmac.new(secret, struct.pack(">Q", timestep), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    value = int.from_bytes(mac[offset:offset + 4], "big") & 0x7FFFFFFF
    return str(value % (10 ** digits)).zfill(digits)


def normalize_code(code):
    """The code if it is exactly six ASCII digits, else None."""
    if not isinstance(code, str) or not _CODE.fullmatch(code):
        return None
    return code


def matching_step(secret: bytes, code, unix_seconds: int):
    """The time step (now, or one step either side) whose code equals `code`, or None. Every candidate is compared."""
    code = normalize_code(code)
    if code is None:
        return None
    now = step_at(unix_seconds)
    found = None
    for step in range(now - settings.TOTP_DRIFT_STEPS, now + settings.TOTP_DRIFT_STEPS + 1):
        if hmac.compare_digest(generate_totp(secret, step), code):
            found = step
    return found


def verify_totp(secret: bytes, code, unix_seconds: int) -> bool:
    return matching_step(secret, code, unix_seconds) is not None


def otpauth_uri(secret: bytes, account: str) -> str:
    """otpauth://totp/<issuer>:<account>?secret=...&issuer=... with every label part percent-encoded."""
    issuer = settings.TOTP_ISSUER
    label = f"{quote(issuer, safe='')}:{quote(account, safe='')}"
    return (f"otpauth://totp/{label}?secret={b32(secret)}&issuer={quote(issuer, safe='')}"
            f"&algorithm=SHA1&digits={settings.TOTP_DIGITS}&period={settings.TOTP_PERIOD_SECONDS}")

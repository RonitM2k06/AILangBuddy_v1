"""AES-256-GCM encryption of TOTP secrets at rest (Phase 14D).

  * The key is TOTP_ENC_KEY: exactly 32 bytes, base64url-encoded (padding optional). It is read from the environment on every use, never
    generated, stored, logged or returned. Missing or malformed, every operation raises KeyUnavailable and 2FA cannot be set up or verified
    (fail closed; recovery codes, which do not depend on the key, still work).
  * Every encryption uses a fresh random 96-bit nonce. The ciphertext includes GCM's 128-bit tag, so any change to it, the nonce or the key
    is detected (SecretUnreadable).
  * The associated data binds a ciphertext to its user: a ciphertext copied onto another account does not decrypt.
  * Error messages never contain the key, the secret or the ciphertext."""
import base64
import binascii
import os
import re

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .. import settings

NONCE_BYTES = 12
KEY_BYTES = 32
_KEY_TEXT = re.compile(r"^[A-Za-z0-9_-]{43}=?$")          # 32 bytes in base64url is 43 characters (+ one optional "=")


class KeyUnavailable(Exception):
    """TOTP_ENC_KEY is missing or is not a 32-byte base64url value."""


class SecretUnreadable(Exception):
    """The stored ciphertext does not decrypt with this key for this user (changed key, tampered row, or a row from another user)."""


def load_key():
    raw = settings.totp_enc_key()
    if raw is None or not _KEY_TEXT.match(raw):
        raise KeyUnavailable("TOTP_ENC_KEY is not set to a 32-byte base64url value")
    try:
        key = base64.urlsafe_b64decode(raw.rstrip("=") + "=")
    except (binascii.Error, ValueError) as exc:
        raise KeyUnavailable("TOTP_ENC_KEY is not set to a 32-byte base64url value") from exc
    if len(key) != KEY_BYTES:
        raise KeyUnavailable("TOTP_ENC_KEY is not set to a 32-byte base64url value")
    return key


def key_status():
    """'valid', 'missing' or 'malformed' (never the key)."""
    if settings.totp_enc_key() is None:
        return "missing"
    try:
        load_key()
        return "valid"
    except KeyUnavailable:
        return "malformed"


def available():
    try:
        load_key()
        return True
    except KeyUnavailable:
        return False


def _aad(user_id):
    return f"lingobuddy/totp-secret/v1/user/{int(user_id)}".encode()


def encrypt(secret: bytes, user_id) -> tuple:
    """Returns (ciphertext, nonce) for this user's secret."""
    nonce = os.urandom(NONCE_BYTES)
    return AESGCM(load_key()).encrypt(nonce, secret, _aad(user_id)), nonce


def decrypt(ciphertext: bytes, nonce: bytes, user_id) -> bytes:
    key = load_key()
    if not isinstance(nonce, (bytes, bytearray)) or len(nonce) != NONCE_BYTES:
        raise SecretUnreadable("the stored secret cannot be read")
    try:
        return AESGCM(key).decrypt(bytes(nonce), bytes(ciphertext), _aad(user_id))
    except (InvalidTag, ValueError, TypeError) as exc:
        raise SecretUnreadable("the stored secret cannot be read") from exc

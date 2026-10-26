"""TOTP two-factor authentication flows (Phase 14D). No HTTP in here.

  * Setup needs the current password (a stolen session alone cannot enrol an attacker's authenticator). It stores a pending, AES-GCM
    encrypted secret for TOTP_SETUP_SECONDS and returns the setup material once. Confirming with a correct code enables it, issues
    RECOVERY_CODE_COUNT one-time recovery codes (returned once, stored as hashes) and replaces the current session with an MFA session.
  * Sign-in for an account with 2FA: a correct password opens a login challenge (service.login -> MfaRequired); only verifying a TOTP or
    recovery code against that challenge creates a session, with mfa_level 1. Challenges live MFA_CHALLENGE_SECONDS, allow
    MFA_CHALLENGE_MAX_ATTEMPTS wrong codes, and complete once.
  * Replay: a TOTP code is accepted for a time step strictly later than the last one used; a recovery code is spent once. Both are
    conditional UPDATEs inside the transaction that creates the session, so concurrent requests cannot both succeed.
  * Wrong second-factor attempts are recorded in the database per user; MFA_MAX_FAILURES within MFA_WINDOW_SECONDS blocks every
    second-factor check for that user (429 with Retry-After) until the oldest failure leaves the window. Nothing is ever locked forever.
    Every attempt is counted BEFORE anything is checked (a failure row reserved in one statement, and one of the challenge's attempts) and
    the failure row is given back when the attempt succeeds or stops before a wrong answer, so concurrent requests cannot exceed either limit
    (Phase 14F).
  * Turning 2FA off needs the password AND a current code or recovery code, and is refused for administrators.
Secrets, codes and tokens never appear in return values other than the one-time setup material and recovery codes, nor in errors."""
import base64
import calendar
import hashlib
import math
import re
import secrets
from contextlib import contextmanager
from datetime import timedelta

from .. import settings
from ..db import connect
from ..repositories import sessions as session_repo
from ..repositories import two_factor as repo
from ..repositories import users
from . import events, qr, service, totp, totp_crypto
from .passwords import verify_password

TooManyAttempts = service.TooManyAttempts
_RECOVERY = re.compile(r"[A-Z2-7]{16}")


class NotConfigured(Exception):
    """TOTP_ENC_KEY is missing or malformed, or the stored secret cannot be read with it."""


class AlreadyEnabled(Exception):
    pass


class NotEnabled(Exception):
    pass


class NoPendingSetup(Exception):
    pass


class WrongCredentials(Exception):
    """A wrong code, recovery code or password. One answer for all of them."""


class ChallengeInvalid(Exception):
    """No live login challenge behind this cookie (unknown, expired, used up or completed)."""


class AdminCannotDisable(Exception):
    pass


def _fmt(dt):
    return service._fmt(dt)


def _unix(now):
    return calendar.timegm(now.utctimetuple())


def _sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def normalize_recovery_code(code):
    """Recovery codes are 16 base32 characters, shown as XXXX-XXXX-XXXX-XXXX; dashes, spaces and case are ignored."""
    if not isinstance(code, str):
        return None
    compact = code.replace("-", "").replace(" ", "").upper()
    return compact if _RECOVERY.fullmatch(compact) else None


def recovery_hash(normalized):
    return _sha256("lingobuddy/recovery-code/v1/" + normalized)


def _new_recovery_codes():
    codes = [base64.b32encode(secrets.token_bytes(10)).decode() for _ in range(settings.RECOVERY_CODE_COUNT)]   # 80 bits each
    return codes, ["-".join(c[i:i + 4] for i in range(0, 16, 4)) for c in codes]


# ---------- used by service.login ----------
def enabled_for(conn, user_id):
    return repo.is_enabled(conn, user_id)


def open_challenge(conn, user_id, now):
    token = secrets.token_urlsafe(32)
    repo.create_challenge(conn, user_id, _sha256(token), _fmt(now), _fmt(now + timedelta(seconds=settings.MFA_CHALLENGE_SECONDS)))
    return token


# ---------- throttling (database-backed) ----------
def _reserve(db_path, user_id, kind, now, stage, client):
    """Count this attempt as a failure before anything is checked, or raise TooManyAttempts (recording mfa_throttled) if this user already
    has MFA_MAX_FAILURES recent failures. Returns the reserved failure row's id."""
    window = settings.MFA_WINDOW_SECONDS
    since = _fmt(now - timedelta(seconds=window))
    with connect(db_path) as conn:
        reserved = repo.reserve_failure(conn, user_id, kind, _fmt(now), since, settings.MFA_MAX_FAILURES)
        times = repo.failures_since(conn, user_id, since) if reserved is None else None
    if reserved is None:
        events.record_quiet(db_path, "mfa_throttled", "denied", user_id=user_id, reason="throttled", stage=stage, client=client)
        oldest = service._parse(times[0]) if times else now
        raise TooManyAttempts(max(1, math.ceil(window - (now - oldest).total_seconds())))
    return reserved


@contextmanager
def _attempt(db_path, user_id, kind, now, stage, client):
    """One second-factor attempt, counted up front (see _reserve); yields the reserved failure row's id. A wrong answer (WrongCredentials)
    keeps it: that is the failure. Any other way out (no setup, no key, a dead challenge) gives it back; a success gives it back itself,
    inside its own transaction (repo.release_failure)."""
    reserved = _reserve(db_path, user_id, kind, now, stage, client)
    try:
        yield reserved
    except WrongCredentials:
        raise
    except BaseException:
        with connect(db_path) as conn:
            repo.release_failure(conn, user_id, reserved)
        raise


def _fail(db_path, user_id, *, event="mfa_failure", reason="wrong_code", stage=None, client=None):
    """The security event for a wrong second-factor attempt (already counted by _attempt)."""
    events.record_now(db_path, event, "failed", user_id=user_id, reason=reason, stage=stage, client=client)


def _secret(cred, user_id):
    try:
        return totp_crypto.decrypt(cred["secret_ciphertext"], cred["secret_nonce"], user_id)
    except (totp_crypto.KeyUnavailable, totp_crypto.SecretUnreadable) as exc:
        raise NotConfigured() from exc


def _password_ok(db_path, user_id, password):
    with connect(db_path) as conn:
        stored = users.get_password_hash(conn, user_id)
    return bool(stored) and isinstance(password, str) and verify_password(password, stored)


# ---------- status ----------
def status(db_path, user):
    now = _fmt(service.utcnow())
    with connect(db_path) as conn:
        cred = repo.get_credential(conn, user.id)
        enabled = bool(cred) and cred["status"] == "enabled"
        return {"enabled": enabled, "pending": bool(cred) and cred["status"] == "pending" and cred["setup_expires_at"] > now,
                "recovery_codes_remaining": repo.unused_recovery_codes(conn, user.id) if enabled else 0,
                "available": totp_crypto.available(), "required": user.has_any_role("admin"), "session_mfa": user.mfa_level >= 1}


# ---------- setup ----------
def begin_setup(db_path, user, password, client=None):
    now = service.utcnow()
    if not totp_crypto.available():
        raise NotConfigured()
    with _attempt(db_path, user.id, "confirm", now, "setup", client) as reserved:
        with connect(db_path) as conn:
            cred = repo.get_credential(conn, user.id)
        if cred and cred["status"] == "enabled":
            raise AlreadyEnabled()
        if not _password_ok(db_path, user.id, password):
            _fail(db_path, user.id, reason="wrong_credentials", stage="setup", client=client)
            raise WrongCredentials()
        secret = totp.new_secret()
        ciphertext, nonce = totp_crypto.encrypt(secret, user.id)
        with connect(db_path) as conn:
            repo.put_pending(conn, user.id, ciphertext, nonce, _fmt(now), _fmt(now + timedelta(seconds=settings.TOTP_SETUP_SECONDS)))
            repo.release_failure(conn, user.id, reserved)
            events.record(conn, "mfa_setup_started", "ok", user_id=user.id, stage="setup", client=client)
    uri = totp.otpauth_uri(secret, user.email or user.handle)
    try:
        picture = qr.matrix(uri)
    except Exception:                                   # the manual key below still works without a picture
        picture = None
    return {"secret": totp.b32(secret), "otpauth_uri": uri, "qr": picture, "expires_in_seconds": settings.TOTP_SETUP_SECONDS}


def confirm_setup(db_path, user, code, current_token, client=None):
    """Returns (recovery codes for display, new session token)."""
    now = service.utcnow()
    with _attempt(db_path, user.id, "confirm", now, "confirm", client) as reserved:
        with connect(db_path) as conn:
            cred = repo.get_credential(conn, user.id)
        if not cred or cred["status"] != "pending" or cred["setup_expires_at"] <= _fmt(now):
            raise NoPendingSetup()
        step = totp.matching_step(_secret(cred, user.id), code, _unix(now))
        if step is None:
            _fail(db_path, user.id, stage="confirm", client=client)
            raise WrongCredentials()
        raw, shown = _new_recovery_codes()
        with connect(db_path) as conn:
            if repo.enable(conn, user.id, step, _fmt(now)) != 1:
                raise NoPendingSetup()
            repo.replace_recovery_codes(conn, user.id, [recovery_hash(c) for c in raw], _fmt(now))
            token, _ = service._start_session(conn, user.id, now, replaces=current_token, mfa_level=1, auth_method="password+totp")
            repo.release_failure(conn, user.id, reserved)
            events.record(conn, "mfa_enabled", "ok", user_id=user.id, method="password+totp", stage="confirm", client=client)
    return shown, token


# ---------- sign-in ----------
def _invalid_challenge(db_path, user_id, client):
    events.record_quiet(db_path, "mfa_failure", "failed", user_id=user_id, reason="expired_challenge", stage="sign_in", client=client)
    return ChallengeInvalid()


def verify_challenge(db_path, challenge_token, *, code=None, recovery_code=None, presented_session=None, client=None):
    """Returns (User, session token). The session is created only here, with mfa_level 1."""
    now = service.utcnow()
    if not challenge_token:
        raise ChallengeInvalid()                             # no cookie at all: nothing was attempted
    with connect(db_path) as conn:
        ch = repo.live_challenge(conn, _sha256(challenge_token), _fmt(now), settings.MFA_CHALLENGE_MAX_ATTEMPTS)
    if ch is None:
        raise _invalid_challenge(db_path, None, client)
    user_id = ch["user_id"]
    with _attempt(db_path, user_id, "verify", now, "sign_in", client) as reserved:
        with connect(db_path) as conn:
            taken = repo.take_attempt(conn, ch["id"], _fmt(now), settings.MFA_CHALLENGE_MAX_ATTEMPTS)
        if taken != 1:                                       # used up or completed by concurrent requests meanwhile
            raise _invalid_challenge(db_path, user_id, client)
        with connect(db_path) as conn:
            cred = repo.get_credential(conn, user_id)
        if not cred or cred["status"] != "enabled":
            raise _invalid_challenge(db_path, user_id, client)
        step = normalized = None
        if code is not None:
            try:
                secret = _secret(cred, user_id)
            except NotConfigured:
                events.record_now(db_path, "mfa_failure", "failed", user_id=user_id, reason="not_configured", stage="sign_in", client=client)
                raise
            step = totp.matching_step(secret, code, _unix(now))
        elif recovery_code is not None:
            normalized = normalize_recovery_code(recovery_code)
        with connect(db_path) as conn:
            spent = ((step is not None and repo.spend_step(conn, user_id, step) == 1)
                     or (normalized is not None and repo.spend_recovery_code(conn, user_id, recovery_hash(normalized), _fmt(now)) == 1))
            if spent:
                if repo.complete_challenge(conn, ch["id"], _fmt(now)) != 1:
                    raise ChallengeInvalid()                 # rolls the spend back: someone else completed it first
                method = "password+totp" if step is not None else "password+recovery"
                token, public_id = service._start_session(conn, user_id, now, replaces=presented_session, mfa_level=1, auth_method=method)
                row = conn.execute("SELECT id, handle, display_name, email FROM users WHERE id = ?", (user_id,)).fetchone()
                roles = users.get_roles(conn, user_id)
                repo.release_failure(conn, user_id, reserved)
                events.record(conn, "mfa_success", "ok", user_id=user_id, method=method, stage="sign_in", client=client)
                if normalized is not None:
                    events.record(conn, "mfa_recovery_code_used", "ok", user_id=user_id, method=method, stage="sign_in",
                                  count=repo.unused_recovery_codes(conn, user_id), client=client)
                if "admin" in roles:
                    events.record(conn, "admin_login", "ok", user_id=user_id, method=method, stage="sign_in", client=client)
        if not spent:
            _fail(db_path, user_id, reason="wrong_recovery_code" if recovery_code is not None else "wrong_code", stage="sign_in", client=client)
            raise WrongCredentials()
    return service.User(row["id"], row["handle"], row["display_name"], row["email"], frozenset(roles), public_id, 1, method), token


# ---------- turning it off, new recovery codes ----------
def _second_factor(conn, cred, user_id, code, recovery_code, now, allow_recovery):
    """Spend a current code (or, if allowed, a recovery code) inside the caller's transaction. True if one was spent."""
    if code is not None:
        step = totp.matching_step(_secret(cred, user_id), code, _unix(now))
        return step is not None and repo.spend_step(conn, user_id, step) == 1
    if allow_recovery and recovery_code is not None:
        normalized = normalize_recovery_code(recovery_code)
        return normalized is not None and repo.spend_recovery_code(conn, user_id, recovery_hash(normalized), _fmt(now)) == 1
    return False


def _enabled_credential(db_path, user):
    with connect(db_path) as conn:
        cred = repo.get_credential(conn, user.id)
    if not cred or cred["status"] != "enabled":
        raise NotEnabled()
    return cred


def disable(db_path, user, *, password, code=None, recovery_code=None, current_token=None, client=None):
    """Password AND a current code or recovery code. Every session ends; this browser gets a fresh password-only session. Never for admins."""
    if user.has_any_role("admin"):
        events.record_quiet(db_path, "mfa_disable_failed", "denied", user_id=user.id, reason="admin_cannot_disable", stage="disable", client=client)
        raise AdminCannotDisable()
    now = service.utcnow()
    with _attempt(db_path, user.id, "disable", now, "disable", client) as reserved:
        cred = _enabled_credential(db_path, user)
        ok = _password_ok(db_path, user.id, password)
        with connect(db_path) as conn:
            if ok and _second_factor(conn, cred, user.id, code, recovery_code, now, allow_recovery=True):
                repo.remove(conn, user.id)
                revoked = session_repo.delete_all_for_user(conn, user.id)
                token, _ = service._start_session(conn, user.id, now)
                repo.release_failure(conn, user.id, reserved)
                events.record(conn, "mfa_disabled", "ok", user_id=user.id, stage="disable", count=revoked, client=client)
                return token
        _fail(db_path, user.id, event="mfa_disable_failed", reason="wrong_credentials", stage="disable", client=client)
        raise WrongCredentials()


def regenerate_recovery_codes(db_path, user, *, password, code, client=None):
    """Password AND a current code. The old codes stop working; the new ones are returned once."""
    now = service.utcnow()
    with _attempt(db_path, user.id, "regenerate", now, "regenerate", client) as reserved:
        cred = _enabled_credential(db_path, user)
        ok = _password_ok(db_path, user.id, password)
        raw, shown = _new_recovery_codes()
        with connect(db_path) as conn:
            if ok and _second_factor(conn, cred, user.id, code, None, now, allow_recovery=False):
                repo.replace_recovery_codes(conn, user.id, [recovery_hash(c) for c in raw], _fmt(now))
                repo.release_failure(conn, user.id, reserved)
                events.record(conn, "mfa_recovery_codes_regenerated", "ok", user_id=user.id, stage="regenerate", count=len(raw), client=client)
                return shown
        _fail(db_path, user.id, reason="wrong_credentials", stage="regenerate", client=client)
        raise WrongCredentials()

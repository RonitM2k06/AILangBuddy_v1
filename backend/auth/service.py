"""Authentication business logic: registration, login, sessions, password change. No HTTP and no SQL in here.

Sessions (Phase 14C):
  * a session is a random 256-bit token in an HttpOnly cookie; the database keeps only its SHA-256 and a random public_id;
  * signing in or registering always issues a fresh session, and the session this browser presented (if any) is revoked in the same
    transaction: a session never changes hands and is never upgraded in place;
  * a session ends at its absolute expiry (SESSION_TTL_DAYS after sign-in, never extended) or after session_idle_minutes() unused;
    last_seen_at is written server-side, at most every SESSION_TOUCH_SECONDS, and only for a valid session;
  * a user may list and revoke only their own sessions, sign out every other session, and change their password (which revokes every
    other session and rotates the current one).
Throttling: see backend/auth/throttle.py."""
import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .. import settings
from ..db import connect
from ..repositories import sessions, users
from . import events, throttle
from .passwords import hash_password, verify_password

MAX_FAILURES = settings.LOGIN_ACCOUNT_MAX_FAILURES        # kept for callers that predate the layered throttle
FAILURE_WINDOW = timedelta(seconds=settings.LOGIN_WINDOW_SECONDS)

# Verified against when the email is unknown, so "no such user" costs the same time as "wrong password".
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class AuthError(Exception):
    pass


class EmailTaken(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class WrongPassword(AuthError):
    """The current password given for a password change is not the user's."""


class NotFound(AuthError):
    """No such session for this user (unknown and someone else's look the same)."""


class MfaRequired(AuthError):
    """The password was right, but the account has two-factor authentication: no session yet, only a login challenge (raw token)."""

    def __init__(self, challenge_token):
        super().__init__("A second factor is required")
        self.challenge_token = challenge_token


class TooManyAttempts(AuthError):
    def __init__(self, retry_after):
        super().__init__("Too many attempts")
        self.retry_after = retry_after


@dataclass(frozen=True)
class User:
    id: int
    handle: str
    display_name: str
    email: str | None
    roles: frozenset
    session_id: str | None = None          # the public id of the session this request came with (server-derived, never from the client)
    mfa_level: int = 0                     # the session's: 1 only for a session created after a verified second factor (Phase 14D)
    auth_method: str = "password"

    def has_any_role(self, *names):
        return bool(self.roles & set(names))


def utcnow():
    return datetime.now(timezone.utc)


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")  # same shape as SQLite CURRENT_TIMESTAMP; sorts correctly as text


def _parse(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _idle_cutoff(now):
    return now - timedelta(minutes=settings.session_idle_minutes())


def normalize_email(email):
    return email.strip().lower()


def _new_token():
    token = secrets.token_urlsafe(32)
    return token, _hash_token(token)


def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def reset_throttle():
    throttle.reset_all()


def _start_session(conn, user_id, now, replaces=None, mfa_level=0, auth_method="password"):
    """A fresh session for `user_id`; the presented session (raw token `replaces`), whoever's it was, is revoked in the same transaction."""
    if replaces:
        sessions.delete_by_token_hash(conn, _hash_token(replaces))
    token, token_hash = _new_token()
    public_id = sessions.create(conn, user_id, token_hash, _fmt(now), _fmt(now + timedelta(days=settings.SESSION_TTL_DAYS)),
                                mfa_level=mfa_level, auth_method=auth_method)
    return token, public_id


def _throttled(*checks):
    waits = [w for w in checks if w is not None]
    if waits:
        raise TooManyAttempts(max(waits))


def create_user(db_path, *, email, password, display_name, roles, with_session=True, client=None, replaces=None):
    """Create a user with the given roles (and optionally a first session) in one transaction. Returns (user, token). The caller decides
    which roles are allowed; HTTP callers never allow admin. `client` (the caller's address) is throttled when given: every attempt counts."""
    now = utcnow()
    if client is not None:
        _throttled(throttle.register_ip.acquire(client, now))
    email = normalize_email(email)
    password_hash = hash_password(password)  # slow on purpose; done before the transaction opens
    handle = "u_" + secrets.token_hex(8)  # server-generated; never chosen by the client
    token = public_id = None
    try:
        with connect(db_path) as conn:
            user_id = users.create_user(conn, handle, display_name, email, password_hash)
            for role in roles:
                users.assign_role(conn, user_id, role)
            if with_session:
                token, public_id = _start_session(conn, user_id, now, replaces)
            role_names = users.get_roles(conn, user_id)
    except sqlite3.IntegrityError as exc:
        if "users.email" in str(exc):
            raise EmailTaken() from exc
        raise
    return User(user_id, handle, display_name, email, frozenset(role_names), public_id), token


def login(db_path, *, email, password, client="-", replaces=None):
    """Returns (user, token) or raises InvalidCredentials / TooManyAttempts / MfaRequired. Failures count against the account (from any
    address) and against the address (for any account); a success clears only the account's count, so one valid account cannot reset an
    address. Every attempt is counted before the password is checked and given back if it was right, so concurrent guesses cannot exceed
    the limits. For an account with two-factor authentication a correct password creates NO session, only a login challenge (MfaRequired)."""
    email = normalize_email(email)
    now = utcnow()
    account_wait, address_wait = throttle.login_account.acquire(email, now), throttle.login_ip.acquire(client, now)
    if account_wait is not None or address_wait is not None:
        if account_wait is None:
            throttle.login_account.release(email, now)
        if address_wait is None:
            throttle.login_ip.release(client, now)
        events.record_quiet(db_path, "login_throttled", "denied", reason="throttled", stage="sign_in", client=client)
        _throttled(account_wait, address_wait)
    with connect(db_path) as conn:
        row = users.get_by_email(conn, email)
    ok = verify_password(password, row["password_hash"] if row else _DUMMY_HASH)
    if not (row and ok):                                      # both attempts stay counted
        events.record_now(db_path, "login_failure", "failed", user_id=row["id"] if row else None, method="password", reason="wrong_credentials",
                          stage="sign_in", client=client)
        raise InvalidCredentials()
    throttle.login_account.clear(email)
    throttle.login_ip.release(client, now)
    from . import mfa                                         # imported here: mfa builds on this module
    challenge = None
    with connect(db_path) as conn:                            # committed before raising: an exception inside would roll it back
        if mfa.enabled_for(conn, row["id"]):
            challenge = mfa.open_challenge(conn, row["id"], now)
            events.record(conn, "mfa_challenge", "ok", user_id=row["id"], method="password", stage="sign_in", client=client)
    if challenge is not None:
        raise MfaRequired(challenge)
    with connect(db_path) as conn:
        sessions.delete_expired_for_user(conn, row["id"], _fmt(now), _fmt(_idle_cutoff(now)))
        token, public_id = _start_session(conn, row["id"], now, replaces)
        events.record(conn, "login_success", "ok", user_id=row["id"], method="password", stage="sign_in", client=client)
        roles = users.get_roles(conn, row["id"])
    return User(row["id"], row["handle"], row["display_name"], row["email"], frozenset(roles), public_id), token


def authenticate(db_path, token):
    """Resolve a session token to a User, or None if unknown, expired or idle too long (such a session is deleted). A valid session's
    last_seen_at is moved to now when it is at least SESSION_TOUCH_SECONDS old."""
    if not token:
        return None
    token_hash = _hash_token(token)
    now = utcnow()
    with connect(db_path) as conn:
        row = sessions.get_user_by_token_hash(conn, token_hash)
        if row is None:
            return None
        if row["expires_at"] <= _fmt(now) or row["last_seen_at"] <= _fmt(_idle_cutoff(now)):
            sessions.delete_by_token_hash(conn, token_hash)
            return None
        if (now - _parse(row["last_seen_at"])).total_seconds() >= settings.SESSION_TOUCH_SECONDS:
            sessions.touch(conn, row["session_id"], _fmt(now))
        roles = users.get_roles(conn, row["id"])
    return User(row["id"], row["handle"], row["display_name"], row["email"], frozenset(roles), row["public_id"], row["mfa_level"], row["auth_method"])


def logout(db_path, token, client=None):
    if token:
        with connect(db_path) as conn:
            row = sessions.get_user_by_token_hash(conn, _hash_token(token))
            sessions.delete_by_token_hash(conn, _hash_token(token))
            if row is not None:
                events.record(conn, "logout", "ok", user_id=row["id"], client=client)


def list_sessions(db_path, user):
    now = utcnow()
    with connect(db_path) as conn:
        rows = sessions.list_for_user(conn, user.id, _fmt(now), _fmt(_idle_cutoff(now)))
    return [{"id": r["public_id"], "created_at": r["created_at"], "last_seen_at": r["last_seen_at"], "expires_at": r["expires_at"],
             "auth_method": r["auth_method"], "current": r["public_id"] == user.session_id} for r in rows]


def revoke_session(db_path, user, public_id, client=None):
    """Revoke one of the user's own sessions. Returns True if it was the current one. NotFound for anything else."""
    with connect(db_path) as conn:
        if not sessions.delete_for_user(conn, user.id, public_id):
            raise NotFound()
        events.record(conn, "session_revoked", "ok", user_id=user.id, count=1, client=client)
    return public_id == user.session_id


def logout_others(db_path, user, client=None):
    """Sign out every session of this user except the one making the request. Returns how many were revoked."""
    with connect(db_path) as conn:
        revoked = sessions.delete_others_for_user(conn, user.id, user.session_id)
        events.record(conn, "logout_all", "ok", user_id=user.id, count=revoked, client=client)
        return revoked


def change_password(db_path, user, *, current_password, new_password, client=None):
    """Check the current password, store the new hash, revoke every other session and rotate the current one. Returns the new token.
    Wrong current passwords are throttled per user (counted before the check, like sign-in)."""
    now = utcnow()
    key = str(user.id)
    wait = throttle.password_change.acquire(key, now)
    if wait is not None:
        events.record_quiet(db_path, "password_change_throttled", "denied", user_id=user.id, reason="throttled", client=client)
        raise TooManyAttempts(wait)
    with connect(db_path) as conn:
        stored = users.get_password_hash(conn, user.id)
    if not (stored and verify_password(current_password, stored)):
        events.record_now(db_path, "password_change_failed", "failed", user_id=user.id, reason="wrong_credentials", client=client)
        raise WrongPassword()
    new_hash = hash_password(new_password)
    with connect(db_path) as conn:                            # one transaction: the new password, no old sessions, one fresh session
        if users.set_password_hash(conn, user.id, new_hash) != 1:
            raise WrongPassword()
        revoked = sessions.delete_all_for_user(conn, user.id)    # the current one included: it is replaced by a fresh token below
        token, _ = _start_session(conn, user.id, now, mfa_level=user.mfa_level, auth_method=user.auth_method)   # keeps its second factor
        events.record(conn, "password_changed", "ok", user_id=user.id, count=revoked, client=client)
    throttle.password_change.clear(key)
    return token

"""Security events (Phase 14E): what happened to an account's security, recorded append-only in security_events (migration 0028).

What is recorded: only the closed fields below. Never a password, token, token hash, TOTP secret, recovery code, challenge cookie, e-mail
address, request body or header. The client address is stored only as a 16-character HMAC (`ip_ref`), so attempts from one address can be
grouped without keeping the address.

Failure policy:
  * Events that belong to a state change (a session created or revoked, a password or 2FA change) are written with `record(conn, ...)` in
    the SAME transaction as the change: the change and its event commit together or not at all.
  * Events with no state change of their own (a failed or throttled attempt, an admin refused for missing MFA) are written with
    `record_now(db_path, ...)` in their own transaction. A transient database problem there (sqlite3.OperationalError, e.g. "database is
    locked") is logged by its type only and swallowed, so a busy database cannot turn a wrong password into a server error or lock people
    out. A malformed event (an unknown type, outcome or field value) is a programming error and is never swallowed: it raises.
  * Refusals that cost the caller nothing to repeat (a throttled attempt, a dead login challenge, a refused admin) are written with
    `record_quiet`: at most one event per DENIAL_QUIET_SECONDS for the same type, outcome, account, reason, stage and address, so a flood
    of such requests cannot flood the table (Phase 14F). Attempts that are actually checked (a wrong password or code) are throttled, and
    each of those is recorded.
Nothing is ever updated or deleted (the schema refuses both)."""
import hashlib
import hmac
import logging
import sqlite3
from datetime import timedelta

from .. import settings
from ..db import connect

log = logging.getLogger(__name__)

EVENT_TYPES = frozenset({
    "login_success", "login_failure", "login_throttled", "logout", "logout_all", "session_revoked",
    "password_changed", "password_change_failed", "password_change_throttled",
    "mfa_setup_started", "mfa_enabled", "mfa_challenge", "mfa_success", "mfa_failure", "mfa_throttled",
    "mfa_recovery_code_used", "mfa_recovery_codes_regenerated", "mfa_disabled", "mfa_disable_failed",
    "admin_login", "admin_access_denied_mfa",
})
OUTCOMES = frozenset({"ok", "failed", "denied"})
METHODS = frozenset({"password", "password+totp", "password+recovery"})
REASONS = frozenset({"wrong_credentials", "wrong_code", "wrong_recovery_code", "expired_challenge", "throttled", "not_configured", "admin_cannot_disable"})
STAGES = frozenset({"sign_in", "setup", "confirm", "disable", "regenerate"})
MAX_COUNT = 100_000
DENIAL_QUIET_SECONDS = 60          # a repeated refusal is recorded at most once a minute (record_quiet, record_admin_denial)


def _now():
    from . import service
    return service._fmt(service.utcnow())


def ip_ref(client):
    """A 16-hex HMAC of the client address under the admin reference key; None when unknown. The address itself is never stored."""
    if not client or client == "-":
        return None
    return hmac.new(settings.admin_ref_secret(), f"ip:{client}".encode(), hashlib.sha256).hexdigest()[:16]


def _check(event_type, outcome, method, reason, stage, count):
    if event_type not in EVENT_TYPES or outcome not in OUTCOMES:
        raise ValueError("unknown security event type or outcome")
    if (method is not None and method not in METHODS) or (reason is not None and reason not in REASONS) or (stage is not None and stage not in STAGES):
        raise ValueError("unknown security event field value")
    if count is not None and (isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= MAX_COUNT):
        raise ValueError("a security event count is a small non-negative integer")


def record(conn, event_type, outcome, *, user_id=None, method=None, reason=None, stage=None, count=None, client=None):
    """Write one event on the caller's connection (its transaction)."""
    _check(event_type, outcome, method, reason, stage, count)
    conn.execute("""INSERT INTO security_events(occurred_at, event_type, outcome, user_id, method, reason, stage, count, ip_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (_now(), event_type, outcome, user_id, method, reason, stage, count, ip_ref(client)))


def record_now(db_path, event_type, outcome, **fields):
    """Write one event in its own transaction. See the failure policy above."""
    _check(event_type, outcome, fields.get("method"), fields.get("reason"), fields.get("stage"), fields.get("count"))
    try:
        with connect(db_path) as conn:
            record(conn, event_type, outcome, **fields)
    except sqlite3.OperationalError as exc:
        log.warning("security event %s not recorded (%s)", event_type, type(exc).__name__)


def record_quiet(db_path, event_type, outcome, *, user_id=None, reason=None, stage=None, client=None):
    """record_now, unless the same refusal (type, outcome, account, reason, stage, address) was recorded in the last DENIAL_QUIET_SECONDS.
    The lookup uses the time index, so it only ever reads the last minute's events."""
    _check(event_type, outcome, None, reason, stage, None)
    from . import service
    since = service._fmt(service.utcnow() - timedelta(seconds=DENIAL_QUIET_SECONDS))
    try:
        with connect(db_path) as conn:
            recent = conn.execute("""SELECT 1 FROM security_events INDEXED BY idx_security_events_time
                                     WHERE occurred_at > ? AND event_type = ? AND outcome = ? AND user_id IS ? AND reason IS ? AND stage IS ? AND ip_ref IS ?
                                     LIMIT 1""", (since, event_type, outcome, user_id, reason, stage, ip_ref(client))).fetchone()
            if recent is None:
                record(conn, event_type, outcome, user_id=user_id, reason=reason, stage=stage, client=client)
    except sqlite3.OperationalError as exc:
        log.warning("security event %s not recorded (%s)", event_type, type(exc).__name__)


def record_admin_denial(db_path, user_id, client=None):
    """admin_access_denied_mfa, at most once per DENIAL_QUIET_SECONDS per admin."""
    from . import service
    since = service._fmt(service.utcnow() - timedelta(seconds=DENIAL_QUIET_SECONDS))
    try:
        with connect(db_path) as conn:
            recent = conn.execute("SELECT 1 FROM security_events WHERE user_id = ? AND event_type = 'admin_access_denied_mfa' AND occurred_at > ? LIMIT 1",
                                  (user_id, since)).fetchone()
            if recent is None:
                record(conn, "admin_access_denied_mfa", "denied", user_id=user_id, client=client)
    except sqlite3.OperationalError as exc:
        log.warning("security event admin_access_denied_mfa not recorded (%s)", type(exc).__name__)

-- Phase 14E: security events. One new append-only table.
--
-- Authentication and security-sensitive account events (sign-in, sign-out, sessions, password, two-factor, admin access). Admin CONTENT
-- changes are not repeated here: they stay in admin_audit_log (Phase 13).
--
-- Every field is structured and closed: the event type, outcome, method, reason and stage come from fixed lists (CHECK), the count is a
-- bounded integer and the network reference is a 16-character HMAC of the client address (never the address itself). There is no free
-- text, so no password, token, code, secret, e-mail address or request body can be stored, even by mistake.
-- user_id is the account the event is about (NULL when there is none, e.g. a sign-in attempt for an unknown e-mail). Admins see it only as
-- the existing opaque HMAC reference (backend/admin/learners.py ref_for), never the id.

CREATE TABLE security_events (
    id          INTEGER PRIMARY KEY,
    occurred_at TEXT    NOT NULL,
    event_type  TEXT    NOT NULL CHECK (event_type IN (
        'login_success', 'login_failure', 'login_throttled', 'logout', 'logout_all', 'session_revoked',
        'password_changed', 'password_change_failed', 'password_change_throttled',
        'mfa_setup_started', 'mfa_enabled', 'mfa_challenge', 'mfa_success', 'mfa_failure', 'mfa_throttled',
        'mfa_recovery_code_used', 'mfa_recovery_codes_regenerated', 'mfa_disabled', 'mfa_disable_failed',
        'admin_login', 'admin_access_denied_mfa')),
    outcome     TEXT    NOT NULL CHECK (outcome IN ('ok', 'failed', 'denied')),
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    method      TEXT    CHECK (method IS NULL OR method IN ('password', 'password+totp', 'password+recovery')),
    reason      TEXT    CHECK (reason IS NULL OR reason IN ('wrong_credentials', 'wrong_code', 'wrong_recovery_code', 'expired_challenge',
                                                            'throttled', 'not_configured', 'admin_cannot_disable')),
    stage       TEXT    CHECK (stage IS NULL OR stage IN ('sign_in', 'setup', 'confirm', 'disable', 'regenerate')),
    count       INTEGER CHECK (count IS NULL OR count BETWEEN 0 AND 100000),
    ip_ref      TEXT    CHECK (ip_ref IS NULL OR (length(ip_ref) = 16 AND ip_ref NOT GLOB '*[^0-9a-f]*'))
);

-- Newest first by id (insertion order), optionally of one type; and per account.
CREATE INDEX idx_security_events_type ON security_events(event_type, id);
CREATE INDEX idx_security_events_user ON security_events(user_id, id);
CREATE INDEX idx_security_events_time ON security_events(occurred_at);

-- Append-only. The one change allowed is the foreign key's own ON DELETE SET NULL when an account is removed (every other column untouched).
CREATE TRIGGER security_events_no_update BEFORE UPDATE ON security_events
WHEN NOT (OLD.user_id IS NOT NULL AND NEW.user_id IS NULL
          AND NEW.id IS OLD.id AND NEW.occurred_at IS OLD.occurred_at AND NEW.event_type IS OLD.event_type AND NEW.outcome IS OLD.outcome
          AND NEW.method IS OLD.method AND NEW.reason IS OLD.reason AND NEW.stage IS OLD.stage AND NEW.count IS OLD.count AND NEW.ip_ref IS OLD.ip_ref)
BEGIN SELECT RAISE(ABORT, 'security events cannot be changed'); END;

CREATE TRIGGER security_events_no_delete BEFORE DELETE ON security_events
BEGIN SELECT RAISE(ABORT, 'security events cannot be deleted'); END;

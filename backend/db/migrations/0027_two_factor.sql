-- Phase 14D: TOTP two-factor authentication. Additive: new tables only (sessions already carry mfa_level and auth_method since 0026).
--
-- two_factor_credentials  one row per user: a pending setup (expires) or the enabled credential. The TOTP secret is stored ONLY as
--                         AES-GCM ciphertext (20-byte secret + 16-byte tag) with its 12-byte nonce; the key is TOTP_ENC_KEY in the
--                         environment and never in the database. last_used_step is the replay guard: a code is accepted only for a time
--                         step later than the last one used.
-- recovery_codes          SHA-256 of each one-time recovery code (never the code); used_at marks it spent.
-- login_challenges        the step between a correct password and the second factor: SHA-256 of the challenge cookie's token, its user,
--                         a 5-minute lifetime, an attempt count and when it was completed. It is never a session.
-- mfa_failures            failed second-factor attempts per user (database-backed, so a restart does not reset them).

CREATE TABLE two_factor_credentials (
    user_id           INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    secret_ciphertext BLOB    NOT NULL CHECK (typeof(secret_ciphertext) = 'blob' AND length(secret_ciphertext) = 36),
    secret_nonce      BLOB    NOT NULL CHECK (typeof(secret_nonce) = 'blob' AND length(secret_nonce) = 12),
    status            TEXT    NOT NULL CHECK (status IN ('pending', 'enabled')),
    created_at        TEXT    NOT NULL,
    setup_expires_at  TEXT,
    enabled_at        TEXT,
    last_used_step    INTEGER CHECK (last_used_step IS NULL OR last_used_step >= 0),
    CHECK ((status = 'pending') = (setup_expires_at IS NOT NULL)),
    CHECK ((status = 'enabled') = (enabled_at IS NOT NULL)),
    CHECK (setup_expires_at IS NULL OR setup_expires_at > created_at)
);

-- An enabled credential keeps its secret; it is never turned back into a pending setup (turning 2FA off deletes the row); the replay guard
-- only moves forward.
CREATE TRIGGER two_factor_enabled_secret_is_fixed BEFORE UPDATE ON two_factor_credentials
WHEN OLD.status = 'enabled' AND (NEW.status <> 'enabled' OR NEW.secret_ciphertext IS NOT OLD.secret_ciphertext
                                OR NEW.secret_nonce IS NOT OLD.secret_nonce OR NEW.enabled_at IS NOT OLD.enabled_at)
BEGIN SELECT RAISE(ABORT, 'an enabled two-factor credential cannot be changed, only used or removed'); END;

CREATE TRIGGER two_factor_step_moves_forward BEFORE UPDATE OF last_used_step ON two_factor_credentials
WHEN OLD.last_used_step IS NOT NULL AND (NEW.last_used_step IS NULL OR NEW.last_used_step <= OLD.last_used_step)
BEGIN SELECT RAISE(ABORT, 'a time step can only be used once, in order'); END;

CREATE TABLE recovery_codes (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash  TEXT    NOT NULL UNIQUE CHECK (length(code_hash) = 64 AND code_hash NOT GLOB '*[^0-9a-f]*'),
    created_at TEXT    NOT NULL,
    used_at    TEXT    CHECK (used_at IS NULL OR used_at >= created_at)
);
CREATE INDEX idx_recovery_codes_user ON recovery_codes(user_id, used_at);

-- A code is spent at most once and never "unspent"; its owner and hash never change.
CREATE TRIGGER recovery_codes_spend_once BEFORE UPDATE ON recovery_codes
WHEN NEW.user_id IS NOT OLD.user_id OR NEW.code_hash IS NOT OLD.code_hash OR NEW.created_at IS NOT OLD.created_at
  OR OLD.used_at IS NOT NULL OR NEW.used_at IS NULL
BEGIN SELECT RAISE(ABORT, 'a recovery code can only be spent, once'); END;

CREATE TABLE login_challenges (
    id           INTEGER PRIMARY KEY,
    token_hash   TEXT    NOT NULL UNIQUE CHECK (length(token_hash) = 64 AND token_hash NOT GLOB '*[^0-9a-f]*'),
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at   TEXT    NOT NULL,
    expires_at   TEXT    NOT NULL,
    attempts     INTEGER NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5),
    completed_at TEXT,
    CHECK (expires_at > created_at),
    CHECK (completed_at IS NULL OR completed_at >= created_at)
);
CREATE INDEX idx_login_challenges_user ON login_challenges(user_id);
CREATE INDEX idx_login_challenges_expiry ON login_challenges(expires_at);

-- A challenge belongs to one user for one lifetime; attempts only go up; it is completed at most once.
CREATE TRIGGER login_challenges_fixed BEFORE UPDATE ON login_challenges
WHEN NEW.token_hash IS NOT OLD.token_hash OR NEW.user_id IS NOT OLD.user_id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.expires_at IS NOT OLD.expires_at OR NEW.attempts < OLD.attempts
  OR (OLD.completed_at IS NOT NULL AND NEW.completed_at IS NOT OLD.completed_at)
BEGIN SELECT RAISE(ABORT, 'a login challenge can only count attempts and be completed once'); END;

CREATE TABLE mfa_failures (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind        TEXT    NOT NULL CHECK (kind IN ('verify', 'confirm', 'disable', 'regenerate')),
    occurred_at TEXT    NOT NULL
);
CREATE INDEX idx_mfa_failures_user ON mfa_failures(user_id, occurred_at);

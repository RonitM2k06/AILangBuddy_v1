-- Phase 14C: session hardening. Additive: existing sessions keep working until their idle or absolute expiry.
--
-- public_id     the session's public name (32 hex chars, random), used to list and revoke sessions. The token hash never leaves the server.
-- last_seen_at  when the session was last used (written at most once a minute), for the idle timeout. Server-written only.
-- auth_method   how the session was authenticated. Only 'password' exists today; the other values are reserved for Phase 14D (2FA), so
--               that step needs no table rebuild.
-- mfa_level     0 today; reserved for Phase 14D.
-- Revoking a session deletes its row, so a revoked token can never authenticate again.
--
-- SQLite's ALTER TABLE cannot add a NOT NULL column without a constant default or a UNIQUE column, so the rules ALTER cannot express
-- are triggers and a unique index below.
ALTER TABLE sessions ADD COLUMN public_id    TEXT;
ALTER TABLE sessions ADD COLUMN last_seen_at TEXT;
ALTER TABLE sessions ADD COLUMN auth_method  TEXT    NOT NULL DEFAULT 'password' CHECK (auth_method IN ('password', 'password+totp', 'password+recovery'));
ALTER TABLE sessions ADD COLUMN mfa_level    INTEGER NOT NULL DEFAULT 0 CHECK (mfa_level IN (0, 1));

-- Existing sessions: a random public id each, and "last seen" = when they were created (so a session nobody has used for longer than the
-- idle timeout ends at its next use, exactly like a new one would).
UPDATE sessions SET public_id = lower(hex(randomblob(16))), last_seen_at = created_at;

CREATE UNIQUE INDEX idx_sessions_public_id ON sessions(public_id);
-- Idle-session cleanup at login looks sessions up by user and last use.
CREATE INDEX idx_sessions_user_last_seen ON sessions(user_id, last_seen_at);

CREATE TRIGGER sessions_new_row_is_complete BEFORE INSERT ON sessions
WHEN NEW.public_id IS NULL OR length(NEW.public_id) <> 32 OR NEW.public_id GLOB '*[^0-9a-f]*'
  OR NEW.last_seen_at IS NULL OR NEW.last_seen_at < NEW.created_at OR NEW.last_seen_at > NEW.expires_at
BEGIN SELECT RAISE(ABORT, 'a session needs a 32-character lowercase hex public_id and a last_seen_at within its lifetime'); END;

-- A session's identity and lifetime never change: rotation is a new row, never an edited one. Only last_seen_at moves, forward only and
-- never past the absolute expiry.
CREATE TRIGGER sessions_identity_is_fixed BEFORE UPDATE ON sessions
WHEN NEW.id IS NOT OLD.id OR NEW.user_id IS NOT OLD.user_id OR NEW.token_hash IS NOT OLD.token_hash OR NEW.public_id IS NOT OLD.public_id
  OR NEW.created_at IS NOT OLD.created_at OR NEW.expires_at IS NOT OLD.expires_at OR NEW.auth_method IS NOT OLD.auth_method
  OR NEW.mfa_level IS NOT OLD.mfa_level
  OR NEW.last_seen_at IS NULL OR NEW.last_seen_at < OLD.last_seen_at OR NEW.last_seen_at > NEW.expires_at
BEGIN SELECT RAISE(ABORT, 'a session can only be used (last_seen_at moves forward) or deleted'); END;

-- Phase 2: authentication schema.

-- users gains login credentials. SQLite cannot add a cross-column CHECK with ALTER TABLE, so the
-- table is rebuilt (copying every existing row). Nothing references users yet, so this is safe.
-- email and password_hash are NULL together (legacy/demo users cannot log in) or set together.
-- Emails are compared case-insensitively.
CREATE TABLE users_new (
    id            INTEGER PRIMARY KEY,
    handle        TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL,
    email         TEXT COLLATE NOCASE UNIQUE,
    password_hash TEXT,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((email IS NULL) = (password_hash IS NULL))
);

INSERT INTO users_new(id, handle, display_name, created_at)
SELECT id, handle, display_name, created_at FROM users;

DROP TABLE users;

ALTER TABLE users_new RENAME TO users;

CREATE TABLE roles (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- Many-to-many: a user may hold several roles.
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    PRIMARY KEY (user_id, role_id)
);

-- Only a SHA-256 of the session token is stored, so a leaked database cannot be replayed as cookies.
CREATE TABLE sessions (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    CHECK (expires_at > created_at)
);

-- Per-user lookups (expired-session cleanup at login) and ON DELETE CASCADE from users.
CREATE INDEX idx_sessions_user ON sessions(user_id);

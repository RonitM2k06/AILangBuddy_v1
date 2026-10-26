-- Phase 1 foundation schema.

-- Legacy prototype state (one JSON blob per learner). Identical to the DDL the app used to
-- run inline, so on an existing buddy.db this is a no-op and no data is touched.
CREATE TABLE IF NOT EXISTS state (
    user_id TEXT PRIMARY KEY,
    data    TEXT NOT NULL,
    updated TEXT DEFAULT CURRENT_TIMESTAMP
);

-- handle is the stable external identifier; it equals the legacy state.user_id ("demo-alex").
-- Credentials, roles and email arrive with authentication in a later phase.
CREATE TABLE users (
    id           INTEGER PRIMARY KEY,
    handle       TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE languages (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL UNIQUE,
    native_name TEXT NOT NULL,
    tts_locale  TEXT NOT NULL
);

CREATE TABLE cefr_levels (
    code  TEXT PRIMARY KEY,
    rank  INTEGER NOT NULL UNIQUE CHECK (rank >= 1),
    label TEXT NOT NULL
);

CREATE TABLE cities (
    id       INTEGER PRIMARY KEY,
    slug     TEXT NOT NULL UNIQUE,
    name     TEXT NOT NULL,
    flag     TEXT NOT NULL,
    emoji    TEXT NOT NULL,
    tagline  TEXT NOT NULL,
    blurb    TEXT NOT NULL,
    is_ready INTEGER NOT NULL DEFAULT 0 CHECK (is_ready IN (0, 1))
);

-- Which languages a city offers, in display order.
CREATE TABLE city_languages (
    city_id     INTEGER NOT NULL REFERENCES cities(id)    ON DELETE CASCADE,
    language_id INTEGER NOT NULL REFERENCES languages(id) ON DELETE RESTRICT,
    sort_order  INTEGER NOT NULL CHECK (sort_order >= 1),
    PRIMARY KEY (city_id, language_id),
    UNIQUE (city_id, sort_order)
);

-- Reverse lookup: which cities offer a given language (the composite PK only serves city-first lookups).
CREATE INDEX idx_city_languages_language ON city_languages(language_id);

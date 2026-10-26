-- Phase 3: supported language/CEFR combinations, age groups, learner profiles. Additive only.

-- Which CEFR levels can be learned in which language (the "supported combinations").
-- A language with no rows here is in the catalogue but cannot yet be chosen as a target language.
CREATE TABLE language_levels (
    language_id INTEGER NOT NULL REFERENCES languages(id)   ON DELETE CASCADE,
    cefr_code   TEXT    NOT NULL REFERENCES cefr_levels(code) ON DELETE RESTRICT,
    PRIMARY KEY (language_id, cefr_code)
);

-- Age bands as data. A learner's band is derived from date of birth at read time, never stored.
-- max_age NULL means open-ended. Bands must be contiguous and non-overlapping; that cannot be
-- expressed declaratively in SQLite, so it is enforced by tests and by the lookup's ordering.
CREATE TABLE age_groups (
    id      INTEGER PRIMARY KEY,
    code    TEXT NOT NULL UNIQUE,
    label   TEXT NOT NULL,
    min_age INTEGER NOT NULL UNIQUE CHECK (min_age >= 0),
    max_age INTEGER CHECK (max_age IS NULL OR max_age >= min_age)
);

-- One profile per user (user_id is both PK and FK). The composite FK makes the database itself
-- reject an unsupported (target language, level) pair.
CREATE TABLE learner_profiles (
    user_id            INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    native_language_id INTEGER NOT NULL REFERENCES languages(id) ON DELETE RESTRICT,
    target_language_id INTEGER NOT NULL,
    cefr_level         TEXT    NOT NULL,
    date_of_birth      TEXT    NOT NULL
        CHECK (date_of_birth GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(date_of_birth) IS date_of_birth),
    updated_at         TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (native_language_id <> target_language_id),
    FOREIGN KEY (target_language_id, cefr_level) REFERENCES language_levels(language_id, cefr_code) ON DELETE RESTRICT
);

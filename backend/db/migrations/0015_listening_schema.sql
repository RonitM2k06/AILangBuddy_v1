-- Phase 7A: listening activities, audio metadata and audio sessions. Additive only.
--
-- Design notes
--  * Listening reuses the existing vocabulary: an activity plays ONE vocabulary item (the thing the learner hears) and
--    offers options that are other vocabulary items. Nothing is copied. What an option shows (its meaning in the learner's
--    native language, or its text) is resolved at read time, so this works for any native language.
--  * Which option is correct is NOT stored as a flag: the correct option is the one whose item is the activity's item.
--    (There is no redundant is_correct column that could disagree with item_id.)
--  * Audio is metadata only: a path/URL, a MIME type, a duration. No audio bytes live in SQLite. When an item has no
--    playable asset the runtime falls back to browser speech synthesis, which needs no row at all.
--  * audio_sessions is the generic container for one audio interaction (kind listening now, speaking later), with its
--    own lifecycle status and duration; listening_attempts holds the listening-specific answer.

-- Playable sources for a vocabulary item. provider: a shipped file ('static'), a file produced by a TTS run ('generated')
-- or a hosted URL from an external TTS service ('external_tts'). Browser TTS is a runtime fallback, not a stored source.
CREATE TABLE audio_assets (
    id          INTEGER PRIMARY KEY,
    item_id     INTEGER NOT NULL,
    language_id INTEGER NOT NULL,
    provider    TEXT    NOT NULL CHECK (provider IN ('static', 'generated', 'external_tts')),
    locale      TEXT    NOT NULL CHECK (length(trim(locale)) > 0),
    voice       TEXT,
    -- a site-relative path or an https URL; no other scheme, no protocol-relative URLs, no path traversal
    source_url  TEXT    NOT NULL CHECK ((source_url LIKE '/%' AND source_url NOT LIKE '//%' OR source_url LIKE 'https://%')
                                        AND source_url NOT LIKE '%..%' AND source_url NOT LIKE '% %'),
    mime_type   TEXT    NOT NULL CHECK (mime_type IN ('audio/mpeg', 'audio/ogg', 'audio/wav', 'audio/mp4', 'audio/webm')),
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms > 0),
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at  TEXT    NOT NULL,
    FOREIGN KEY (item_id, language_id) REFERENCES vocabulary_items(id, language_id) ON DELETE CASCADE,
    UNIQUE (item_id, source_url)   -- its leading column also serves "assets of an item"
);

-- mode: choose_meaning (hear a phrase, pick what it means) or choose_phrase (hear a phrase, pick which phrase it was).
CREATE TABLE listening_activities (
    id          INTEGER PRIMARY KEY,
    language_id INTEGER NOT NULL,
    cefr_code   TEXT    NOT NULL,
    topic_id    INTEGER NOT NULL REFERENCES topics(id) ON DELETE RESTRICT,
    item_id     INTEGER NOT NULL,
    slug        TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    mode        TEXT    NOT NULL CHECK (mode IN ('choose_meaning', 'choose_phrase')),
    prompt      TEXT    NOT NULL CHECK (length(trim(prompt)) > 0),
    difficulty  INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
    sort_order  INTEGER NOT NULL CHECK (sort_order >= 1),
    status      TEXT    NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    FOREIGN KEY (language_id, cefr_code) REFERENCES language_levels(language_id, cefr_code) ON DELETE RESTRICT,
    FOREIGN KEY (item_id, language_id)   REFERENCES vocabulary_items(id, language_id)       ON DELETE RESTRICT,
    UNIQUE (language_id, slug),
    UNIQUE (language_id, cefr_code, sort_order),   -- also serves "activities of a language/level in order"
    UNIQUE (id, language_id)
);
CREATE INDEX idx_listening_activities_topic ON listening_activities(topic_id);  -- activities of a topic
CREATE INDEX idx_listening_activities_item  ON listening_activities(item_id);   -- activities playing an item

-- The choices offered for an activity. The correct one is the option whose item is the activity's item (see above).
CREATE TABLE listening_options (
    id          INTEGER PRIMARY KEY,
    activity_id INTEGER NOT NULL,
    language_id INTEGER NOT NULL,
    item_id     INTEGER NOT NULL,
    sort_order  INTEGER NOT NULL CHECK (sort_order >= 1),
    FOREIGN KEY (activity_id, language_id) REFERENCES listening_activities(id, language_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id, language_id)     REFERENCES vocabulary_items(id, language_id)     ON DELETE RESTRICT,
    UNIQUE (activity_id, sort_order),
    UNIQUE (activity_id, item_id),
    UNIQUE (id, activity_id)
);
CREATE INDEX idx_listening_options_item ON listening_options(item_id);  -- options using an item

-- One audio interaction by one learner. kind is listening now; speaking sessions (recording, transcript, score) reuse
-- this table later with their own detail table. status started <=> not yet ended.
CREATE TABLE audio_sessions (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    language_id INTEGER NOT NULL REFERENCES languages(id) ON DELETE RESTRICT,
    kind        TEXT    NOT NULL CHECK (kind IN ('listening', 'speaking')),
    status      TEXT    NOT NULL DEFAULT 'started' CHECK (status IN ('started', 'completed', 'abandoned', 'failed')),
    started_at  TEXT    NOT NULL,
    ended_at    TEXT,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    CHECK ((status = 'started') = (ended_at IS NULL)),
    CHECK (ended_at IS NULL OR ended_at >= started_at),
    UNIQUE (id, user_id)
);
CREATE INDEX idx_audio_sessions_user ON audio_sessions(user_id, kind, started_at);  -- a learner's recent sessions

-- One row per submitted listening answer. The session must belong to the same learner, and the chosen option to the
-- same activity (composite FKs). plays is the number of times the learner played the audio (client-reported, bounded).
CREATE TABLE listening_attempts (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id   INTEGER NOT NULL,
    activity_id  INTEGER NOT NULL REFERENCES listening_activities(id) ON DELETE CASCADE,
    option_id    INTEGER NOT NULL,
    is_correct   INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    plays        INTEGER NOT NULL DEFAULT 0 CHECK (plays BETWEEN 0 AND 99),
    attempted_at TEXT    NOT NULL,
    FOREIGN KEY (session_id, user_id)    REFERENCES audio_sessions(id, user_id)           ON DELETE CASCADE,
    FOREIGN KEY (option_id, activity_id) REFERENCES listening_options(id, activity_id)    ON DELETE RESTRICT,
    UNIQUE (session_id)
);
-- progress roll-ups and "has this learner got this activity right"
CREATE INDEX idx_listening_attempts_user_activity ON listening_attempts(user_id, activity_id, is_correct);
-- a learner's attempts, newest first
CREATE INDEX idx_listening_attempts_user_time ON listening_attempts(user_id, attempted_at);

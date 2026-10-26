-- Phase 7B: speaking sessions, speech-to-text runs and transcripts. Additive only.
--
-- Design notes
--  * No second session system: a speaking session IS an audio_sessions row (kind 'speaking'), extended by one detail row.
--    audio_sessions keeps its coarse lifecycle (started / completed / abandoned / failed); speaking_sessions.stage is the
--    finer pipeline state (created, recorded, processing, completed, failed, cancelled). The service keeps the two in step.
--  * The detail row's composite FK (session_id, user_id, kind) into audio_sessions makes the DATABASE enforce that a speaking
--    detail can only hang off a *speaking* session of the *same learner*.
--  * No audio bytes in SQLite: only a generated file reference (never a path), its MIME type, size, SHA-256 and duration.
--  * One STT *run* per transcription attempt (so provider failures are kept as history and a retry is a new run); the text it
--    produced lives in speaking_transcripts (a run can yield several hypotheses, ranked).

-- Lets speaking_sessions reference (id, user_id, kind) of audio_sessions.
CREATE UNIQUE INDEX uq_audio_sessions_owner_kind ON audio_sessions(id, user_id, kind);

CREATE TABLE speaking_sessions (
    session_id       INTEGER PRIMARY KEY,
    user_id          INTEGER NOT NULL,
    kind             TEXT    NOT NULL DEFAULT 'speaking' CHECK (kind = 'speaking'),
    language_id      INTEGER NOT NULL,
    item_id          INTEGER NOT NULL,            -- the phrase the learner was asked to say
    locale           TEXT    NOT NULL CHECK (length(trim(locale)) > 0),
    stage            TEXT    NOT NULL DEFAULT 'created'
                     CHECK (stage IN ('created', 'recorded', 'processing', 'completed', 'failed', 'cancelled')),
    -- recording metadata. audio_ref is a generated file name inside the recordings directory, never a path.
    audio_ref        TEXT    CHECK (audio_ref IS NULL OR (length(audio_ref) BETWEEN 5 AND 64 AND audio_ref NOT LIKE '%/%'
                                    AND audio_ref NOT LIKE '%\%' AND audio_ref NOT LIKE '%..%' AND audio_ref NOT LIKE '% %')),
    audio_mime       TEXT    CHECK (audio_mime IS NULL OR audio_mime IN ('audio/webm', 'audio/ogg', 'audio/mp4', 'audio/mpeg', 'audio/wav')),
    audio_bytes      INTEGER CHECK (audio_bytes IS NULL OR audio_bytes > 0),
    audio_sha256     TEXT    CHECK (audio_sha256 IS NULL OR (length(audio_sha256) = 64 AND audio_sha256 NOT GLOB '*[^0-9a-f]*')),
    recording_ms     INTEGER CHECK (recording_ms IS NULL OR recording_ms > 0),
    recorded_at      TEXT,
    audio_deleted_at TEXT,
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL,
    -- a recording is described completely or not at all (recording_ms is optional: the client may not report it)
    CHECK ((audio_mime IS NULL) = (audio_bytes IS NULL) AND (audio_mime IS NULL) = (audio_sha256 IS NULL)
           AND (audio_mime IS NULL) = (recorded_at IS NULL)),
    CHECK (audio_ref IS NULL OR audio_mime IS NOT NULL),
    CHECK (audio_deleted_at IS NULL OR (audio_mime IS NOT NULL AND audio_ref IS NULL)),
    CHECK (stage = 'cancelled' OR (stage = 'created') = (audio_mime IS NULL)),       -- created <=> nothing recorded yet
    CHECK (stage NOT IN ('recorded', 'processing') OR audio_ref IS NOT NULL),        -- the file must exist to be processed
    FOREIGN KEY (session_id, user_id, kind) REFERENCES audio_sessions(id, user_id, kind) ON DELETE CASCADE,
    FOREIGN KEY (item_id, language_id)      REFERENCES vocabulary_items(id, language_id) ON DELETE RESTRICT,
    UNIQUE (session_id, user_id)
);
CREATE INDEX idx_speaking_sessions_user_item ON speaking_sessions(user_id, item_id, stage);  -- prompts a learner has practised
CREATE INDEX idx_speaking_sessions_item ON speaking_sessions(item_id);                        -- FK restrict on vocabulary delete

-- One row per transcription attempt. status processing <=> not finished; failed <=> has an error_code.
CREATE TABLE stt_runs (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    provider    TEXT    NOT NULL CHECK (length(trim(provider)) > 0 AND length(provider) <= 40),
    locale      TEXT    NOT NULL CHECK (length(trim(locale)) > 0),
    status      TEXT    NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    error_code  TEXT    CHECK (error_code IS NULL OR error_code IN ('provider_unavailable', 'provider_timeout', 'provider_error',
                                                                     'no_speech', 'unsupported_language', 'unsupported_format',
                                                                     'recording_unavailable')),
    started_at  TEXT    NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    CHECK ((status = 'processing') = (finished_at IS NULL)),
    CHECK ((status = 'failed') = (error_code IS NOT NULL)),
    FOREIGN KEY (session_id, user_id) REFERENCES speaking_sessions(session_id, user_id) ON DELETE CASCADE,
    UNIQUE (id, session_id)
);
CREATE UNIQUE INDEX uq_stt_runs_one_in_flight  ON stt_runs(session_id) WHERE status = 'processing';  -- no concurrent runs
CREATE UNIQUE INDEX uq_stt_runs_one_completed  ON stt_runs(session_id) WHERE status = 'completed';   -- one result per session
CREATE INDEX idx_stt_runs_session ON stt_runs(session_id, started_at);                                -- run history

-- What a completed run heard. rank 1 is the best hypothesis; providers that return alternatives add ranks 2, 3, ...
CREATE TABLE speaking_transcripts (
    id         INTEGER PRIMARY KEY,
    run_id     INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    rank       INTEGER NOT NULL DEFAULT 1 CHECK (rank >= 1),
    text       TEXT    NOT NULL CHECK (length(trim(text)) > 0 AND length(text) <= 2000),
    confidence REAL    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),   -- only if the provider supplies one
    locale     TEXT    NOT NULL CHECK (length(trim(locale)) > 0),
    created_at TEXT    NOT NULL,
    FOREIGN KEY (run_id, session_id)  REFERENCES stt_runs(id, session_id)                        ON DELETE CASCADE,
    FOREIGN KEY (session_id, user_id) REFERENCES speaking_sessions(session_id, user_id)          ON DELETE CASCADE,
    UNIQUE (run_id, rank)
);
CREATE INDEX idx_speaking_transcripts_session ON speaking_transcripts(session_id);   -- a session's transcript

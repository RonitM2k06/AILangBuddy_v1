-- Phase 7C: pronunciation assessment. Additive only.
--
-- Design notes
--  * No new speaking-session system: an assessment hangs off an existing speaking session (composite FK on the owner) and
--    off the exact transcript it assessed.
--  * TWO different measurements are kept apart on purpose:
--      - content match (words_expected / words_matched): did the recogniser hear the phrase's words? Computed by us from
--        the transcript; it says nothing about how the phrase sounded;
--      - pronunciation (overall_score, components, word scores): supplied by a pronunciation PROVIDER. A good transcript
--        does not make this high, and a poor transcript does not make it low.
--  * `method` says what kind of measurement the numbers are: 'mock' (a controlled test signal, not a measurement),
--    'proxy' (an indirect measure, e.g. recogniser confidence) or 'model' (a real acoustic pronunciation model).
--  * Components and word scores are stored only when the provider supplied them. There is no phoneme table and no
--    phoneme-level data: nothing exists to store until a provider really reports it.
--  * Percentages and wording are never stored; they are derived. No audio and no file path is stored here.

-- Lets an assessment reference (transcript, session) so it cannot cite another session's transcript.
CREATE UNIQUE INDEX uq_speaking_transcripts_id_session ON speaking_transcripts(id, session_id);

CREATE TABLE pronunciation_assessments (
    id            INTEGER PRIMARY KEY,
    session_id    INTEGER NOT NULL,
    user_id       INTEGER NOT NULL,
    transcript_id INTEGER NOT NULL,
    provider      TEXT    NOT NULL CHECK (length(trim(provider)) > 0 AND length(provider) <= 40),
    method        TEXT    CHECK (method IS NULL OR method IN ('mock', 'proxy', 'model')),
    status        TEXT    NOT NULL CHECK (status IN ('completed', 'failed')),
    error_code    TEXT    CHECK (error_code IS NULL OR error_code IN ('provider_unavailable', 'provider_error', 'provider_timeout',
                                                                       'malformed_output', 'unsupported_language', 'no_signal',
                                                                       'recording_unavailable')),
    overall_score INTEGER CHECK (overall_score IS NULL OR overall_score BETWEEN 0 AND 100),
    words_expected INTEGER NOT NULL CHECK (words_expected >= 1),
    words_matched  INTEGER NOT NULL CHECK (words_matched >= 0 AND words_matched <= words_expected),
    locale        TEXT    NOT NULL CHECK (length(trim(locale)) > 0),
    created_at    TEXT    NOT NULL,
    CHECK ((status = 'completed') = (overall_score IS NOT NULL)),      -- a completed assessment has a score, a failed one never does
    CHECK ((status = 'failed') = (error_code IS NOT NULL)),
    CHECK (status = 'failed' OR method IS NOT NULL),                   -- a score always says what kind of measurement it is
    FOREIGN KEY (session_id, user_id)    REFERENCES speaking_sessions(session_id, user_id)       ON DELETE CASCADE,
    FOREIGN KEY (transcript_id, session_id) REFERENCES speaking_transcripts(id, session_id)      ON DELETE CASCADE
);
-- One completed assessment per session (a repeated request returns it); failed attempts stay as history.
CREATE UNIQUE INDEX uq_pron_one_completed ON pronunciation_assessments(session_id) WHERE status = 'completed';
CREATE INDEX idx_pron_session ON pronunciation_assessments(session_id, id);      -- a session's attempts
CREATE INDEX idx_pron_user_time ON pronunciation_assessments(user_id, created_at); -- a learner's history

-- Component scores, one row per component the provider actually reported.
CREATE TABLE pronunciation_components (
    assessment_id INTEGER NOT NULL REFERENCES pronunciation_assessments(id) ON DELETE CASCADE,
    component     TEXT    NOT NULL CHECK (component IN ('phoneme_accuracy', 'word_accuracy', 'fluency', 'prosody', 'confidence')),
    score         INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    PRIMARY KEY (assessment_id, component)
);

-- Word-level pronunciation scores, only if the provider reported them (position = place in the phrase).
CREATE TABLE pronunciation_word_scores (
    assessment_id INTEGER NOT NULL REFERENCES pronunciation_assessments(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL CHECK (position >= 1),
    word          TEXT    NOT NULL CHECK (length(trim(word)) > 0 AND length(word) <= 60),
    score         INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    PRIMARY KEY (assessment_id, position)
);

-- Evidence for future personalization, kept apart from exercise correctness: ONLY completed assessments by a real acoustic
-- model count. Mock and proxy scores never appear here, so they cannot silently drive recommendations. The Phase 6
-- views and rules are untouched and do not read this.
CREATE VIEW learner_pronunciation_evidence AS
SELECT a.user_id, ss.language_id, ss.item_id, a.session_id, a.id AS assessment_id, a.method, a.overall_score, a.created_at AS assessed_at
FROM pronunciation_assessments a JOIN speaking_sessions ss ON ss.session_id = a.session_id
WHERE a.status = 'completed' AND a.method = 'model';

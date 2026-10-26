-- Phase 5: learner progress through situations. Every row belongs to a user; the API only writes the session's user.
--
-- The current step and step counts are derived (first step without a correct attempt), not stored, so they
-- cannot disagree with the attempt history.

CREATE TABLE situation_progress (
    user_id      INTEGER NOT NULL REFERENCES users(id)      ON DELETE CASCADE,
    situation_id INTEGER NOT NULL REFERENCES situations(id) ON DELETE CASCADE,
    started_at   TEXT    NOT NULL,
    completed_at TEXT,
    PRIMARY KEY (user_id, situation_id),
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

-- One row per submission. answer_id for choose_response, submitted_text for typed steps, neither for
-- learn_phrase (an acknowledgement, always correct). A step passes once it has a correct attempt.
CREATE TABLE situation_step_attempts (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id)           ON DELETE CASCADE,
    step_id        INTEGER NOT NULL REFERENCES situation_steps(id) ON DELETE CASCADE,
    answer_id      INTEGER,
    submitted_text TEXT,
    is_correct     INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    attempted_at   TEXT    NOT NULL,
    CHECK (answer_id IS NULL OR submitted_text IS NULL),
    -- the chosen option must belong to this step
    FOREIGN KEY (answer_id, step_id) REFERENCES situation_step_answers(id, step_id) ON DELETE RESTRICT
);
-- "Has this learner passed this step" and per-situation roll-ups.
CREATE INDEX idx_step_attempts_user_step ON situation_step_attempts(user_id, step_id, is_correct);

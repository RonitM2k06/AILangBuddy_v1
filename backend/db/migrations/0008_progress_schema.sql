-- Phase 4: learner progress. Every row belongs to a user; the API only ever writes the session's user.

-- A row exists once the learner has attempted any exercise in the lesson; completed_at is set when
-- every exercise in it has at least one correct attempt. Status is derived, never stored.
CREATE TABLE lesson_progress (
    user_id      INTEGER NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    lesson_id    INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    started_at   TEXT    NOT NULL,
    completed_at TEXT,
    PRIMARY KEY (user_id, lesson_id),
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

-- One row per submission (history is kept). answer_id is set for multiple choice, submitted_text for typed answers.
CREATE TABLE exercise_attempts (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    exercise_id    INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    answer_id      INTEGER,
    submitted_text TEXT,
    is_correct     INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    attempted_at   TEXT    NOT NULL,
    CHECK (answer_id IS NOT NULL OR submitted_text IS NOT NULL),
    -- the chosen option must belong to this exercise
    FOREIGN KEY (answer_id, exercise_id) REFERENCES exercise_answers(id, exercise_id) ON DELETE RESTRICT
);

-- "Has this learner answered this exercise correctly" and per-lesson progress roll-ups.
CREATE INDEX idx_attempts_user_exercise ON exercise_attempts(user_id, exercise_id, is_correct);

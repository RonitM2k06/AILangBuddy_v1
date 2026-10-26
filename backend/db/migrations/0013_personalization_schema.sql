-- Phase 6: confidence, weaknesses, adaptive difficulty metadata, daily plan. Additive only.
--
-- Confidence is what the learner SAYS (self-reported); performance is what the attempts SHOW. They are stored
-- and exposed separately. Weaknesses and recommendations are derived from the attempt history by transparent rules:
-- weaknesses are stored (with their evidence) so they have a lifecycle; recommendations are derived on demand and
-- not stored (they are a pure function of data that is already stored).

-- Measurable skill dimensions for confidence, besides topics. Only skills the platform can serve today are seeded.
CREATE TABLE skills (
    id   INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

-- Difficulty metadata on exercises: a small controlled scale (1 easy, 2 medium, 3 hard).
ALTER TABLE exercises ADD COLUMN difficulty INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 3);

-- One row per self-report (history is kept; the latest row per dimension is the current confidence).
-- The dimension is a topic XOR a skill. language_id is the learner's target language when it was recorded.
CREATE TABLE confidence_scores (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    language_id  INTEGER NOT NULL REFERENCES languages(id) ON DELETE RESTRICT,
    topic_id     INTEGER REFERENCES topics(id)             ON DELETE RESTRICT,
    skill_id     INTEGER REFERENCES skills(id)             ON DELETE RESTRICT,
    score        INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    source       TEXT    NOT NULL CHECK (source IN ('self_report', 'lesson', 'situation')),
    lesson_id    INTEGER REFERENCES lessons(id)            ON DELETE SET NULL,
    situation_id INTEGER REFERENCES situations(id)         ON DELETE SET NULL,
    recorded_at  TEXT    NOT NULL,
    CHECK ((topic_id IS NULL) <> (skill_id IS NULL)),
    CHECK (lesson_id IS NULL OR situation_id IS NULL)
);
-- "Latest confidence per dimension" and confidence history.
CREATE INDEX idx_confidence_user_topic ON confidence_scores(user_id, language_id, topic_id, recorded_at);
CREATE INDEX idx_confidence_user_skill ON confidence_scores(user_id, language_id, skill_id, recorded_at);

-- A detected weakness with the evidence it was based on. The rule decides the subject:
--   low_topic_accuracy    -> topic_id   (recent accuracy in a topic is low)
--   repeated_item_errors  -> item_id    (the same vocabulary item was answered wrongly again and again)
-- Accuracy is derived from attempts/incorrect, not stored. A weakness that stops holding is kept as 'resolved'.
CREATE TABLE weaknesses (
    id               INTEGER PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    language_id      INTEGER NOT NULL REFERENCES languages(id) ON DELETE RESTRICT,
    rule             TEXT    NOT NULL CHECK (rule IN ('low_topic_accuracy', 'repeated_item_errors')),
    topic_id         INTEGER REFERENCES topics(id)             ON DELETE CASCADE,
    item_id          INTEGER REFERENCES vocabulary_items(id)   ON DELETE CASCADE,
    severity         TEXT    NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    attempts         INTEGER NOT NULL CHECK (attempts >= 1),
    incorrect        INTEGER NOT NULL CHECK (incorrect >= 1 AND incorrect <= attempts),
    last_evidence_at TEXT    NOT NULL,
    detected_at      TEXT    NOT NULL,
    status           TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'resolved')),
    resolved_at      TEXT,
    CHECK ((rule = 'low_topic_accuracy' AND topic_id IS NOT NULL AND item_id IS NULL)
        OR (rule = 'repeated_item_errors' AND item_id IS NOT NULL AND topic_id IS NULL)),
    CHECK ((status = 'resolved') = (resolved_at IS NOT NULL))
);
-- At most one weakness row per subject (NULLs are distinct in UNIQUE, hence one partial index per subject kind).
CREATE UNIQUE INDEX uq_weakness_topic ON weaknesses(user_id, language_id, topic_id) WHERE topic_id IS NOT NULL;
CREATE UNIQUE INDEX uq_weakness_item  ON weaknesses(user_id, language_id, item_id)  WHERE item_id  IS NOT NULL;
CREATE INDEX idx_weaknesses_user_status ON weaknesses(user_id, language_id, status);

-- A learner's daily plan: a few tasks per (day, language). The target is exactly one of a lesson, a situation
-- or a topic (a confidence check-in). source records which recommendation rule produced the task.
CREATE TABLE daily_tasks (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    language_id  INTEGER NOT NULL REFERENCES languages(id) ON DELETE RESTRICT,
    plan_date    TEXT    NOT NULL CHECK (plan_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(plan_date) IS plan_date),
    priority     INTEGER NOT NULL CHECK (priority >= 1),
    task_type    TEXT    NOT NULL CHECK (task_type IN ('study_lesson', 'practice_situation', 'confidence_checkin')),
    source       TEXT    NOT NULL CHECK (source IN ('review_topic', 'review_item', 'continue_lesson', 'continue_situation',
                                                     'low_confidence', 'confidence_checkin', 'next_lesson', 'next_situation')),
    lesson_id    INTEGER REFERENCES lessons(id)    ON DELETE CASCADE,
    situation_id INTEGER REFERENCES situations(id) ON DELETE CASCADE,
    topic_id     INTEGER REFERENCES topics(id)     ON DELETE CASCADE,
    status       TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'skipped')),
    created_at   TEXT    NOT NULL,
    completed_at TEXT,
    CHECK ((lesson_id IS NOT NULL) + (situation_id IS NOT NULL) + (topic_id IS NOT NULL) = 1),
    CHECK ((task_type = 'study_lesson'       AND lesson_id    IS NOT NULL)
        OR (task_type = 'practice_situation' AND situation_id IS NOT NULL)
        OR (task_type = 'confidence_checkin' AND topic_id     IS NOT NULL)),
    CHECK ((status = 'done') = (completed_at IS NOT NULL) OR status = 'skipped'),
    UNIQUE (user_id, language_id, plan_date, priority)
);
-- No duplicate task (same type and target) for the same learner and day.
CREATE UNIQUE INDEX uq_daily_task_target ON daily_tasks(user_id, language_id, plan_date, task_type,
                                                        COALESCE(lesson_id, 0), COALESCE(situation_id, 0), COALESCE(topic_id, 0));

-- One row per graded attempt, from both attempt tables, so rules and reports read one place.
-- Learn-phrase acknowledgements are not evidence of skill and are excluded. difficulty is only set for lesson exercises.
CREATE VIEW learner_attempts AS
SELECT 'lesson' AS source, ea.id AS attempt_id, ea.user_id, l.language_id, l.id AS unit_id, e.id AS task_id, e.kind,
       e.item_id, e.difficulty, ea.is_correct, ea.attempted_at
FROM exercise_attempts ea JOIN exercises e ON e.id = ea.exercise_id JOIN lessons l ON l.id = e.lesson_id
UNION ALL
SELECT 'situation', sa.id, sa.user_id, s.language_id, s.id, st.id, st.kind, st.item_id, NULL, sa.is_correct, sa.attempted_at
FROM situation_step_attempts sa JOIN situation_steps st ON st.id = sa.step_id JOIN situations s ON s.id = st.situation_id
WHERE st.kind <> 'learn_phrase';

-- The same attempts attributed to topics (a lesson can have several topics; a situation has one).
CREATE VIEW learner_attempt_topics AS
SELECT 'lesson' AS source, ea.id AS attempt_id, ea.user_id, l.language_id, lt.topic_id, ea.is_correct, ea.attempted_at
FROM exercise_attempts ea JOIN exercises e ON e.id = ea.exercise_id JOIN lessons l ON l.id = e.lesson_id
JOIN lesson_topics lt ON lt.lesson_id = l.id
UNION ALL
SELECT 'situation', sa.id, sa.user_id, s.language_id, s.topic_id, sa.is_correct, sa.attempted_at
FROM situation_step_attempts sa JOIN situation_steps st ON st.id = sa.step_id JOIN situations s ON s.id = st.situation_id
WHERE st.kind <> 'learn_phrase';

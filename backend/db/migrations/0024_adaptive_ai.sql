-- Phase 12: adaptive AI. Additive only (new tables and one extra index); no existing table or column changes.
--
-- Design notes
--  * AI is never the source of truth. Recommendations, insights and micro-lessons are DERIVED from stored learner evidence and
--    each one carries the evidence rows that justify it (ai_evidence). A model may rank, reword or draft, but only after the
--    server validated what it returned; invalid model output is never stored (only a short audit event with a reason code).
--  * Generated content lives apart from the canonical curriculum. A micro-lesson is anchored to one canonical vocabulary item
--    (composite FK), its answer is checked against that item, and it is shown only while validated and unexpired, to a learner
--    of the age group it was made for, in the language it was made for.
--  * Nothing here awards XP, changes a level, a streak or the CEFR level; those stay in their own systems.
--  * Ownership is enforced with composite (id, user_id) foreign keys, so a row can never point at another learner's row.

CREATE TABLE ai_recommendations (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    language_id INTEGER NOT NULL REFERENCES languages(id) ON DELETE RESTRICT,
    plan_date   TEXT    NOT NULL CHECK (plan_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(plan_date) IS plan_date),
    kind        TEXT    NOT NULL CHECK (kind IN ('review_topic', 'review_item', 'continue_lesson', 'continue_situation', 'low_confidence', 'confidence_checkin',
                                                 'next_lesson', 'next_situation', 'targeted_vocabulary', 'practice_easier', 'practice_harder', 'listening_practice',
                                                 'speaking_practice', 'roleplay_practice', 'remediation')),
    target_type TEXT    NOT NULL CHECK (target_type IN ('lesson', 'situation', 'topic', 'micro_lesson', 'listening_activity', 'speaking', 'roleplay')),
    target_id   INTEGER NOT NULL CHECK (target_id >= 0 AND (target_type = 'speaking' OR target_id > 0)),
    title       TEXT    NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 120),
    reason      TEXT    NOT NULL CHECK (length(trim(reason)) BETWEEN 1 AND 300),
    note        TEXT    CHECK (note IS NULL OR length(trim(note)) BETWEEN 1 AND 300),     -- the ranker's explanation, validated
    rank        INTEGER NOT NULL CHECK (rank BETWEEN 1 AND 20),
    source      TEXT    NOT NULL CHECK (source IN ('rules', 'mock', 'llm')),             -- who ranked and worded it
    mode        TEXT    NOT NULL CHECK (mode IN ('child', 'teen', 'adult')),
    status      TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'applied', 'expired')),
    created_at  TEXT    NOT NULL,
    applied_at  TEXT,
    CHECK ((status = 'applied') = (applied_at IS NOT NULL)),
    UNIQUE (user_id, plan_date, kind, target_type, target_id),                           -- generating twice cannot duplicate
    UNIQUE (id, user_id)
);
CREATE INDEX idx_ai_recommendations_user ON ai_recommendations(user_id, plan_date, rank);

CREATE TABLE ai_learning_insights (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    language_id INTEGER NOT NULL REFERENCES languages(id) ON DELETE RESTRICT,
    day         TEXT    NOT NULL CHECK (day GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(day) IS day),
    kind        TEXT    NOT NULL CHECK (kind IN ('accuracy_trend', 'repeat_weakness', 'confidence_gap', 'roleplay_progress', 'practice_gap')),
    subject     TEXT    NOT NULL DEFAULT '' CHECK (length(subject) <= 60),               -- e.g. the topic or source the claim is about
    text        TEXT    NOT NULL CHECK (length(trim(text)) BETWEEN 1 AND 300),
    source      TEXT    NOT NULL CHECK (source IN ('rules', 'mock', 'llm')),
    created_at  TEXT    NOT NULL,
    UNIQUE (user_id, day, kind, subject),
    UNIQUE (id, user_id)
);

-- Generated practice. NOT curriculum: separate tables, validated before use, expiring.
CREATE TABLE ai_micro_lessons (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    language_id     INTEGER NOT NULL,
    item_id         INTEGER NOT NULL,                                                  -- the canonical vocabulary item this practises
    kind            TEXT    NOT NULL CHECK (kind IN ('vocab_choice', 'phrase_choice', 'translation')),
    topic_id        INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    difficulty      INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
    mode            TEXT    NOT NULL CHECK (mode IN ('child', 'teen', 'adult')),       -- the age group it was made for
    question        TEXT    NOT NULL CHECK (length(trim(question)) BETWEEN 1 AND 300),
    generator       TEXT    NOT NULL CHECK (generator IN ('template', 'mock', 'llm')),
    status          TEXT    NOT NULL DEFAULT 'validated' CHECK (status IN ('validated', 'expired')),
    validation_note TEXT    NOT NULL CHECK (length(validation_note) BETWEEN 1 AND 200),
    day             TEXT    NOT NULL CHECK (day GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(day) IS day),
    created_at      TEXT    NOT NULL,
    expires_at      TEXT    NOT NULL,
    CHECK (expires_at > created_at),
    CHECK (mode <> 'child' OR generator = 'template'),                                  -- children only ever get deterministic template content
    FOREIGN KEY (item_id, language_id) REFERENCES vocabulary_items(id, language_id) ON DELETE RESTRICT,
    UNIQUE (user_id, day, item_id, kind),
    UNIQUE (id, user_id)
);
CREATE INDEX idx_ai_micro_lessons_user ON ai_micro_lessons(user_id, status, expires_at);

-- choice / typed options. For choice kinds exactly one is correct; for 'translation' every row is an accepted answer.
CREATE TABLE ai_micro_lesson_options (
    micro_lesson_id INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    ord             INTEGER NOT NULL CHECK (ord BETWEEN 1 AND 6),
    text            TEXT    NOT NULL CHECK (length(trim(text)) BETWEEN 1 AND 200),
    is_correct      INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    PRIMARY KEY (micro_lesson_id, ord),
    FOREIGN KEY (micro_lesson_id, user_id) REFERENCES ai_micro_lessons(id, user_id) ON DELETE CASCADE,
    UNIQUE (micro_lesson_id, text)
);

CREATE TABLE ai_micro_lesson_attempts (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    micro_lesson_id INTEGER NOT NULL,
    option_ord      INTEGER,
    submitted_text  TEXT    CHECK (submitted_text IS NULL OR length(submitted_text) BETWEEN 1 AND 500),
    is_correct      INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    attempted_at    TEXT    NOT NULL,
    CHECK ((option_ord IS NULL) <> (submitted_text IS NULL)),
    FOREIGN KEY (micro_lesson_id, user_id) REFERENCES ai_micro_lessons(id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (micro_lesson_id, option_ord) REFERENCES ai_micro_lesson_options(micro_lesson_id, ord) ON DELETE CASCADE
);
CREATE INDEX idx_ai_micro_attempts_lesson ON ai_micro_lesson_attempts(micro_lesson_id, user_id);

-- Provenance: the stored evidence behind every recommendation, insight and micro-lesson. Exactly one owner per row.
CREATE TABLE ai_evidence (
    id                INTEGER PRIMARY KEY,
    user_id           INTEGER NOT NULL,
    recommendation_id INTEGER,
    insight_id        INTEGER,
    micro_lesson_id   INTEGER,
    ord               INTEGER NOT NULL CHECK (ord BETWEEN 1 AND 8),
    kind              TEXT    NOT NULL CHECK (kind IN ('weakness', 'confidence', 'accuracy', 'difficulty', 'progress', 'roleplay', 'activity', 'speaking')),
    text              TEXT    NOT NULL CHECK (length(trim(text)) BETWEEN 1 AND 300),
    CHECK ((recommendation_id IS NOT NULL) + (insight_id IS NOT NULL) + (micro_lesson_id IS NOT NULL) = 1),
    FOREIGN KEY (recommendation_id, user_id) REFERENCES ai_recommendations(id, user_id)  ON DELETE CASCADE,
    FOREIGN KEY (insight_id, user_id)        REFERENCES ai_learning_insights(id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (micro_lesson_id, user_id)   REFERENCES ai_micro_lessons(id, user_id)     ON DELETE CASCADE,
    UNIQUE (recommendation_id, ord),
    UNIQUE (insight_id, ord),
    UNIQUE (micro_lesson_id, ord)
);

-- An audit trail of what the adaptive layer did (never learner content, never model output).
CREATE TABLE adaptive_learning_events (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type TEXT    NOT NULL CHECK (event_type IN ('recommendation_applied', 'micro_lesson_answered', 'micro_lesson_rejected', 'ranking_fallback',
                                                      'insight_fallback', 'grading_fallback', 'remediation_created')),
    ref_id     INTEGER,
    detail     TEXT    NOT NULL DEFAULT '' CHECK (length(detail) <= 200),
    created_at TEXT    NOT NULL
);
CREATE INDEX idx_adaptive_events_user ON adaptive_learning_events(user_id, created_at);

-- Roleplay (Phase 11) gains evidence-bearing grades. Each turn's grade says HOW the answer was judged, never what the answer key is.
CREATE UNIQUE INDEX uq_roleplay_turns_owner ON roleplay_turns(id, user_id);
CREATE TABLE roleplay_turn_grades (
    turn_id           INTEGER PRIMARY KEY,
    user_id           INTEGER NOT NULL,
    method            TEXT    NOT NULL CHECK (method IN ('exact', 'semantic', 'semantic_llm', 'none')),
    semantic_match    INTEGER NOT NULL CHECK (semantic_match IN (0, 1)),
    confidence        REAL    NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    explanation       TEXT    NOT NULL CHECK (length(explanation) <= 200),
    missing_objective TEXT    NOT NULL CHECK (length(missing_objective) <= 100),
    grammar_feedback  TEXT    NOT NULL CHECK (length(grammar_feedback) <= 200),
    provider          TEXT    NOT NULL CHECK (length(provider) BETWEEN 1 AND 32),
    CHECK (method <> 'exact' OR (semantic_match = 1 AND confidence = 1)),
    FOREIGN KEY (turn_id, user_id) REFERENCES roleplay_turns(id, user_id) ON DELETE CASCADE
);

-- Phase 5: situational learning content. Additive only.
--
-- A situation is a real-world scenario (ordering food, asking directions, ...) for one (language, CEFR level),
-- made of ordered steps. The optional persona columns (goal, setting, partner_*) describe who the learner is
-- talking to, so a later AI roleplay can be driven from the same row without a schema change.
-- Step meaning/answers follow the Phase 4 pattern: target-language vocabulary is referenced, never copied.

CREATE TABLE situations (
    id           INTEGER PRIMARY KEY,
    language_id  INTEGER NOT NULL,
    cefr_code    TEXT    NOT NULL,
    topic_id     INTEGER NOT NULL REFERENCES topics(id) ON DELETE RESTRICT,
    slug         TEXT    NOT NULL,
    title        TEXT    NOT NULL,
    description  TEXT    NOT NULL,
    goal         TEXT,
    setting      TEXT,
    partner_name TEXT,
    partner_role TEXT,
    difficulty   INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    sort_order   INTEGER NOT NULL CHECK (sort_order >= 1),
    status       TEXT    NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    CHECK ((partner_name IS NULL) = (partner_role IS NULL)),
    FOREIGN KEY (language_id, cefr_code) REFERENCES language_levels(language_id, cefr_code) ON DELETE RESTRICT,
    UNIQUE (language_id, slug),
    UNIQUE (language_id, cefr_code, sort_order),  -- also serves "situations of a language/level in order"
    UNIQUE (id, language_id)
);
CREATE INDEX idx_situations_topic ON situations(topic_id);  -- situations of a topic

-- kind = what the learner does at this step:
--   learn_phrase     study a vocabulary item (item_id required, no answer needed)
--   choose_response  pick the right reply from options (exactly one correct)
--   translate        type the target-language phrase for an English prompt
--   fill_blank       type the missing word
--   conversation     reply to the partner's line; the accepted replies are also offered as suggestions
-- prompt is what the learner reads (English instructions, or the partner's line in the target language
-- with prompt_meaning as its English gloss).
CREATE TABLE situation_steps (
    id             INTEGER PRIMARY KEY,
    situation_id   INTEGER NOT NULL,
    language_id    INTEGER NOT NULL,
    sort_order     INTEGER NOT NULL CHECK (sort_order >= 1),
    kind           TEXT    NOT NULL CHECK (kind IN ('learn_phrase', 'choose_response', 'translate', 'fill_blank', 'conversation')),
    prompt         TEXT,
    prompt_meaning TEXT,
    item_id        INTEGER,
    explanation    TEXT,
    CHECK (kind <> 'learn_phrase' OR item_id IS NOT NULL),
    CHECK (kind = 'learn_phrase' OR (prompt IS NOT NULL AND length(trim(prompt)) > 0)),
    UNIQUE (situation_id, sort_order),
    UNIQUE (id, situation_id),
    FOREIGN KEY (situation_id, language_id) REFERENCES situations(id, language_id)          ON DELETE CASCADE,
    FOREIGN KEY (item_id, language_id)      REFERENCES vocabulary_items(id, language_id)    ON DELETE RESTRICT
);
CREATE INDEX idx_situation_steps_item ON situation_steps(item_id);  -- steps using a vocabulary item

-- choose_response: the options (one is_correct). translate/fill_blank/conversation: the accepted answers (all correct).
CREATE TABLE situation_step_answers (
    id          INTEGER PRIMARY KEY,
    step_id     INTEGER NOT NULL REFERENCES situation_steps(id) ON DELETE CASCADE,
    answer_text TEXT    NOT NULL CHECK (length(trim(answer_text)) > 0),
    is_correct  INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    sort_order  INTEGER NOT NULL CHECK (sort_order >= 1),
    UNIQUE (step_id, sort_order),
    UNIQUE (step_id, answer_text),
    UNIQUE (id, step_id)
);

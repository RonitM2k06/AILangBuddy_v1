-- Phase 4: structured learning content. Additive only.
--
-- Design notes
--  * Target-language content (lessons, vocabulary, grammar) each belong to one (language, CEFR level)
--    that must be a supported combination: a composite FK to language_levels enforces it.
--  * Native-language text (meanings, grammar explanations) lives in *_translations / *_texts tables keyed by
--    language, so a learner's native language can change without duplicating target-language data.
--  * Junction tables that link two language-bound rows carry language_id too, with composite FKs into both
--    parents (which expose UNIQUE (id, language_id)). This is deliberate redundancy: it lets the database
--    itself reject, say, a Spanish word inside a Hindi lesson.

CREATE TABLE topics (
    id   INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    icon TEXT NOT NULL
);

CREATE TABLE lessons (
    id          INTEGER PRIMARY KEY,
    language_id INTEGER NOT NULL,
    cefr_code   TEXT    NOT NULL,
    slug        TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL,
    situation   TEXT,
    tip         TEXT,
    sort_order  INTEGER NOT NULL CHECK (sort_order >= 1),
    status      TEXT    NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    FOREIGN KEY (language_id, cefr_code) REFERENCES language_levels(language_id, cefr_code) ON DELETE RESTRICT,
    UNIQUE (language_id, slug),
    UNIQUE (language_id, cefr_code, sort_order),  -- also serves "lessons of a language/level in order"
    UNIQUE (id, language_id)
);

CREATE TABLE lesson_topics (
    lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    topic_id  INTEGER NOT NULL REFERENCES topics(id)  ON DELETE RESTRICT,
    PRIMARY KEY (lesson_id, topic_id)
);
CREATE INDEX idx_lesson_topics_topic ON lesson_topics(topic_id);  -- lessons for a topic

-- Words and phrases in the target language. 'pronunciation' is a romanised guide (NULL when not applicable).
CREATE TABLE vocabulary_items (
    id            INTEGER PRIMARY KEY,
    language_id   INTEGER NOT NULL,
    cefr_code     TEXT    NOT NULL,
    kind          TEXT    NOT NULL CHECK (kind IN ('word', 'phrase')),
    text          TEXT    NOT NULL CHECK (length(trim(text)) > 0),
    pronunciation TEXT,
    FOREIGN KEY (language_id, cefr_code) REFERENCES language_levels(language_id, cefr_code) ON DELETE RESTRICT,
    UNIQUE (language_id, text),
    UNIQUE (id, language_id)
);

-- What an item means in a given native language. 'meaning' is the plain meaning (or literal rendering),
-- 'natural' the idiomatic rendering when it differs.
CREATE TABLE vocabulary_translations (
    item_id     INTEGER NOT NULL REFERENCES vocabulary_items(id) ON DELETE CASCADE,
    language_id INTEGER NOT NULL REFERENCES languages(id)        ON DELETE RESTRICT,
    meaning     TEXT    NOT NULL CHECK (length(trim(meaning)) > 0),
    natural     TEXT,
    PRIMARY KEY (item_id, language_id)
);

-- An example of a word is another vocabulary item (a phrase), so examples are never duplicated.
CREATE TABLE vocabulary_examples (
    item_id         INTEGER NOT NULL,
    example_item_id INTEGER NOT NULL,
    language_id     INTEGER NOT NULL,
    PRIMARY KEY (item_id, example_item_id),
    CHECK (item_id <> example_item_id),
    FOREIGN KEY (item_id, language_id)         REFERENCES vocabulary_items(id, language_id) ON DELETE CASCADE,
    FOREIGN KEY (example_item_id, language_id) REFERENCES vocabulary_items(id, language_id) ON DELETE CASCADE
);

CREATE TABLE lesson_vocabulary (
    lesson_id   INTEGER NOT NULL,
    item_id     INTEGER NOT NULL,
    language_id INTEGER NOT NULL,
    sort_order  INTEGER NOT NULL CHECK (sort_order >= 1),
    PRIMARY KEY (lesson_id, item_id),
    UNIQUE (lesson_id, sort_order),
    FOREIGN KEY (lesson_id, language_id) REFERENCES lessons(id, language_id)          ON DELETE CASCADE,
    FOREIGN KEY (item_id, language_id)   REFERENCES vocabulary_items(id, language_id) ON DELETE RESTRICT
);
CREATE INDEX idx_lesson_vocabulary_item ON lesson_vocabulary(item_id);  -- lessons using an item

CREATE TABLE grammar_topics (
    id          INTEGER PRIMARY KEY,
    language_id INTEGER NOT NULL,
    cefr_code   TEXT    NOT NULL,
    slug        TEXT    NOT NULL,
    sort_order  INTEGER NOT NULL CHECK (sort_order >= 1),
    FOREIGN KEY (language_id, cefr_code) REFERENCES language_levels(language_id, cefr_code) ON DELETE RESTRICT,
    UNIQUE (language_id, slug),
    UNIQUE (id, language_id)
);

-- Title and explanation in the language the learner reads (native language).
CREATE TABLE grammar_topic_texts (
    grammar_topic_id INTEGER NOT NULL REFERENCES grammar_topics(id) ON DELETE CASCADE,
    language_id      INTEGER NOT NULL REFERENCES languages(id)      ON DELETE RESTRICT,
    title            TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    explanation      TEXT    NOT NULL CHECK (length(trim(explanation)) > 0),
    PRIMARY KEY (grammar_topic_id, language_id)
);

CREATE TABLE grammar_examples (
    grammar_topic_id INTEGER NOT NULL,
    item_id          INTEGER NOT NULL,
    language_id      INTEGER NOT NULL,
    sort_order       INTEGER NOT NULL CHECK (sort_order >= 1),
    PRIMARY KEY (grammar_topic_id, item_id),
    UNIQUE (grammar_topic_id, sort_order),
    FOREIGN KEY (grammar_topic_id, language_id) REFERENCES grammar_topics(id, language_id)    ON DELETE CASCADE,
    FOREIGN KEY (item_id, language_id)          REFERENCES vocabulary_items(id, language_id) ON DELETE RESTRICT
);

CREATE TABLE lesson_grammar (
    lesson_id        INTEGER NOT NULL,
    grammar_topic_id INTEGER NOT NULL,
    language_id      INTEGER NOT NULL,
    PRIMARY KEY (lesson_id, grammar_topic_id),
    FOREIGN KEY (lesson_id, language_id)        REFERENCES lessons(id, language_id)         ON DELETE CASCADE,
    FOREIGN KEY (grammar_topic_id, language_id) REFERENCES grammar_topics(id, language_id)  ON DELETE RESTRICT
);

-- kind is the answer format. The subject (vocabulary vs grammar question) is given by which optional
-- link is set, so a new subject or format is a data change, not a new table.
CREATE TABLE exercises (
    id               INTEGER PRIMARY KEY,
    lesson_id        INTEGER NOT NULL,
    language_id      INTEGER NOT NULL,
    kind             TEXT    NOT NULL CHECK (kind IN ('multiple_choice', 'translation', 'fill_blank')),
    prompt           TEXT    NOT NULL CHECK (length(trim(prompt)) > 0),
    item_id          INTEGER,
    grammar_topic_id INTEGER,
    explanation      TEXT,
    sort_order       INTEGER NOT NULL CHECK (sort_order >= 1),
    UNIQUE (lesson_id, sort_order),
    FOREIGN KEY (lesson_id, language_id)        REFERENCES lessons(id, language_id)          ON DELETE CASCADE,
    FOREIGN KEY (item_id, language_id)          REFERENCES vocabulary_items(id, language_id) ON DELETE RESTRICT,
    FOREIGN KEY (grammar_topic_id, language_id) REFERENCES grammar_topics(id, language_id)   ON DELETE RESTRICT
);

-- multiple_choice: the options (exactly one is_correct, checked by the service/tests).
-- translation / fill_blank: the accepted answers (all is_correct = 1).
CREATE TABLE exercise_answers (
    id          INTEGER PRIMARY KEY,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    answer_text TEXT    NOT NULL CHECK (length(trim(answer_text)) > 0),
    is_correct  INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    sort_order  INTEGER NOT NULL CHECK (sort_order >= 1),
    UNIQUE (exercise_id, sort_order),
    UNIQUE (exercise_id, answer_text),
    UNIQUE (id, exercise_id)
);

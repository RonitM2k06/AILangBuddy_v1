-- Phase 11: AI tutor conversations and roleplay. Additive only; no existing table or column changes.
--
-- Design notes
--  * Everything is normalised: a message is a row, a roleplay turn is a row, what the model was told about the learner is a
--    set of fact rows. Nothing is a JSON blob.
--  * Ownership is enforced by the database where it can be: messages reference (conversation_id, user_id) so a message can
--    never sit in someone else's conversation; roleplay turns reference (session_id, user_id, situation_id) and the step must
--    belong to the same situation (composite FK into situation_steps).
--  * Roleplay is built ON Phase 5: a session points at an existing situation and walks its existing steps; the situation
--    content is not copied. The answer key stays in situation_steps / situation_step_answers / vocabulary_items.
--  * Writes that the learner repeats (a message, a turn) can carry a client_id, unique per conversation/session, so a replay
--    returns the stored result instead of creating a second one.

CREATE TABLE tutor_conversations (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    language_id    INTEGER NOT NULL REFERENCES languages(id) ON DELETE RESTRICT,
    cefr_code      TEXT    NOT NULL,
    mode           TEXT    NOT NULL CHECK (mode IN ('child', 'teen', 'adult')),       -- the age group when it was started
    topic_id       INTEGER REFERENCES topics(id)     ON DELETE SET NULL,
    lesson_id      INTEGER REFERENCES lessons(id)    ON DELETE SET NULL,
    situation_id   INTEGER REFERENCES situations(id) ON DELETE SET NULL,
    title          TEXT    NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 80),
    status         TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    message_count  INTEGER NOT NULL DEFAULT 0 CHECK (message_count BETWEEN 0 AND 200),
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL,
    CHECK ((topic_id IS NOT NULL) + (lesson_id IS NOT NULL) + (situation_id IS NOT NULL) <= 1),
    UNIQUE (id, user_id)
);
CREATE INDEX idx_tutor_conversations_user ON tutor_conversations(user_id, updated_at);

CREATE TABLE tutor_messages (
    id              INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    seq             INTEGER NOT NULL CHECK (seq >= 1),
    role            TEXT    NOT NULL CHECK (role IN ('learner', 'tutor')),
    content         TEXT    NOT NULL CHECK (length(trim(content)) BETWEEN 1 AND 2000),
    quick_prompt    TEXT    CHECK (quick_prompt IS NULL OR (role = 'learner' AND length(quick_prompt) BETWEEN 1 AND 40)),   -- child mode: the helper question chosen
    client_id       TEXT    CHECK (client_id IS NULL OR (role = 'learner' AND length(client_id) BETWEEN 1 AND 64)),
    provider        TEXT    CHECK (provider IS NULL OR length(provider) BETWEEN 1 AND 32),                                   -- who wrote a tutor message
    created_at      TEXT    NOT NULL,
    CHECK ((role = 'tutor') = (provider IS NOT NULL)),
    FOREIGN KEY (conversation_id, user_id) REFERENCES tutor_conversations(id, user_id) ON DELETE CASCADE,
    UNIQUE (conversation_id, seq)
);
CREATE UNIQUE INDEX uq_tutor_messages_client ON tutor_messages(conversation_id, client_id) WHERE client_id IS NOT NULL;   -- a replay is not a new message

-- What the tutor was told about the learner for one reply: stored facts, kept so the answer can be audited and shown apart
-- from the generated advice. At most 8 per reply.
CREATE TABLE tutor_message_facts (
    message_id INTEGER NOT NULL REFERENCES tutor_messages(id) ON DELETE CASCADE,
    ord        INTEGER NOT NULL CHECK (ord BETWEEN 1 AND 8),
    kind       TEXT    NOT NULL CHECK (kind IN ('context', 'weakness', 'confidence', 'mistake', 'activity')),
    text       TEXT    NOT NULL CHECK (length(trim(text)) BETWEEN 1 AND 300),
    PRIMARY KEY (message_id, ord)
);

CREATE TABLE roleplay_sessions (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    situation_id INTEGER NOT NULL,
    language_id  INTEGER NOT NULL,
    cefr_code    TEXT    NOT NULL,
    mode         TEXT    NOT NULL CHECK (mode IN ('child', 'teen', 'adult')),
    status       TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed')),
    steps_total  INTEGER NOT NULL CHECK (steps_total BETWEEN 1 AND 30),
    steps_correct INTEGER CHECK (steps_correct IS NULL OR steps_correct BETWEEN 0 AND 30),     -- set when the session is completed
    steps_missed  INTEGER CHECK (steps_missed IS NULL OR steps_missed BETWEEN 0 AND 30),
    created_at   TEXT    NOT NULL,
    completed_at TEXT,
    CHECK ((status = 'completed') = (completed_at IS NOT NULL)),
    CHECK ((status = 'completed') = (steps_correct IS NOT NULL)),
    CHECK ((steps_correct IS NULL) = (steps_missed IS NULL)),
    CHECK (steps_correct IS NULL OR steps_correct + steps_missed = steps_total),
    FOREIGN KEY (situation_id, language_id) REFERENCES situations(id, language_id) ON DELETE CASCADE,
    UNIQUE (id, user_id),
    UNIQUE (id, user_id, situation_id)
);
CREATE UNIQUE INDEX uq_roleplay_one_active ON roleplay_sessions(user_id, situation_id) WHERE status = 'active';   -- starting again resumes
CREATE INDEX idx_roleplay_sessions_user ON roleplay_sessions(user_id, created_at);

-- One row per learner attempt at the current step. verdict is decided by the server from the stored answers. A step is
-- resolved when it is answered correctly, or after 3 tries (then it counts as missed and the model answer is shown).
CREATE TABLE roleplay_turns (
    id                  INTEGER PRIMARY KEY,
    session_id          INTEGER NOT NULL,
    user_id             INTEGER NOT NULL,
    situation_id        INTEGER NOT NULL,
    step_id             INTEGER NOT NULL,
    turn_no             INTEGER NOT NULL CHECK (turn_no >= 1),
    attempt_no          INTEGER NOT NULL CHECK (attempt_no BETWEEN 1 AND 3),
    learner_text        TEXT    NOT NULL CHECK (length(trim(learner_text)) BETWEEN 1 AND 500),
    input_mode          TEXT    NOT NULL DEFAULT 'text' CHECK (input_mode IN ('text', 'voice')),
    speaking_session_id INTEGER,
    verdict             TEXT    NOT NULL CHECK (verdict IN ('correct', 'incorrect')),
    resolved            TEXT    NOT NULL CHECK (resolved IN ('no', 'correct', 'missed')),
    hint                TEXT,
    character_reply     TEXT    NOT NULL CHECK (length(trim(character_reply)) BETWEEN 1 AND 1000),
    provider            TEXT    NOT NULL CHECK (length(provider) BETWEEN 1 AND 32),
    client_id           TEXT    CHECK (client_id IS NULL OR length(client_id) BETWEEN 1 AND 64),
    created_at          TEXT    NOT NULL,
    CHECK ((verdict = 'correct') = (resolved = 'correct')),
    CHECK (resolved <> 'missed' OR (verdict = 'incorrect' AND attempt_no = 3)),
    CHECK ((input_mode = 'voice') = (speaking_session_id IS NOT NULL)),
    FOREIGN KEY (session_id, user_id, situation_id) REFERENCES roleplay_sessions(id, user_id, situation_id) ON DELETE CASCADE,
    FOREIGN KEY (step_id, situation_id) REFERENCES situation_steps(id, situation_id) ON DELETE CASCADE,
    FOREIGN KEY (speaking_session_id, user_id) REFERENCES speaking_sessions(session_id, user_id) DEFERRABLE INITIALLY DEFERRED,
    UNIQUE (session_id, turn_no)
);
CREATE UNIQUE INDEX uq_roleplay_turn_client ON roleplay_turns(session_id, client_id) WHERE client_id IS NOT NULL;      -- replay-safe
CREATE UNIQUE INDEX uq_roleplay_turn_speech ON roleplay_turns(speaking_session_id) WHERE speaking_session_id IS NOT NULL;   -- a spoken answer is used once
CREATE INDEX idx_roleplay_turns_step ON roleplay_turns(session_id, step_id);

-- The end-of-roleplay feedback: counts that come from the turns, and short texts. Pronunciation is only ever "not analysed"
-- here (a roleplay is checked on what was said, not on how it sounded); no score exists to fabricate.
CREATE TABLE roleplay_feedback (
    session_id          INTEGER PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    steps_total         INTEGER NOT NULL CHECK (steps_total >= 1),
    steps_correct       INTEGER NOT NULL CHECK (steps_correct >= 0),
    steps_missed        INTEGER NOT NULL CHECK (steps_missed >= 0),
    first_try_correct   INTEGER NOT NULL CHECK (first_try_correct >= 0),
    voice_turns         INTEGER NOT NULL CHECK (voice_turns >= 0),
    correctness_text    TEXT    NOT NULL CHECK (length(trim(correctness_text)) > 0),
    vocabulary_feedback TEXT    NOT NULL,
    grammar_feedback    TEXT    NOT NULL,
    hint                TEXT    NOT NULL,
    encouragement       TEXT    NOT NULL,
    next_step           TEXT    NOT NULL,
    pronunciation_note  TEXT    NOT NULL,
    provider            TEXT    NOT NULL CHECK (length(provider) BETWEEN 1 AND 32),
    created_at          TEXT    NOT NULL,
    CHECK (steps_correct + steps_missed = steps_total),
    CHECK (first_try_correct <= steps_correct),
    FOREIGN KEY (session_id, user_id) REFERENCES roleplay_sessions(id, user_id) ON DELETE CASCADE
);

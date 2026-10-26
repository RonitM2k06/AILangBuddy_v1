-- Phase 8: age-aware content and the child game state. Additive only.
--
-- Design notes
--  * Age targeting is a set of per-content junction tables. A content row with NO rows here is open to every age group
--    (so everything that existed before this migration, and anything added later without a target, stays universal). A row
--    with entries is shown only to those age groups. Real foreign keys, one table per content type (no polymorphic ids).
--  * The learner's age group is never stored: it is derived from the date of birth when needed (Phase 3).
--  * Child game state is only what cannot be derived: how many lives, and since when. Level progress and "completed" are
--    derived from the learner's existing listening attempts; nothing is duplicated.
--  * A lost life is recorded against the WRONG attempt that cost it. The composite FK (attempt_id, user_id, attempt_correct)
--    into listening_attempts, with attempt_correct fixed at 0, makes the database itself refuse a life loss for a correct
--    answer or for someone else's attempt, and the unique attempt_id means one attempt can cost at most one life.

-- Targets for the three kinds of content a learner browses.
CREATE TABLE lesson_age_groups (
    lesson_id    INTEGER NOT NULL REFERENCES lessons(id)    ON DELETE CASCADE,
    age_group_id INTEGER NOT NULL REFERENCES age_groups(id) ON DELETE RESTRICT,
    PRIMARY KEY (lesson_id, age_group_id)
);
CREATE INDEX idx_lesson_age_groups_group ON lesson_age_groups(age_group_id);

CREATE TABLE situation_age_groups (
    situation_id INTEGER NOT NULL REFERENCES situations(id) ON DELETE CASCADE,
    age_group_id INTEGER NOT NULL REFERENCES age_groups(id) ON DELETE RESTRICT,
    PRIMARY KEY (situation_id, age_group_id)
);
CREATE INDEX idx_situation_age_groups_group ON situation_age_groups(age_group_id);

CREATE TABLE listening_activity_age_groups (
    activity_id  INTEGER NOT NULL REFERENCES listening_activities(id) ON DELETE CASCADE,
    age_group_id INTEGER NOT NULL REFERENCES age_groups(id)           ON DELETE RESTRICT,
    PRIMARY KEY (activity_id, age_group_id)
);
CREATE INDEX idx_listening_activity_age_groups_group ON listening_activity_age_groups(age_group_id);

-- One row per child learner who has played. lives is bounded 0..5 by the database. lives_updated_at is when `lives` was last
-- brought up to date; lives regenerate with time, and the server works the current value out from these two columns (the
-- client never sends or stores lives).
CREATE TABLE child_game_state (
    user_id          INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    lives            INTEGER NOT NULL CHECK (lives BETWEEN 0 AND 5),
    lives_updated_at TEXT    NOT NULL,
    created_at       TEXT    NOT NULL
);

-- Lets child_life_losses reference an attempt together with its owner and its correctness.
CREATE UNIQUE INDEX uq_listening_attempts_owner_result ON listening_attempts(id, user_id, is_correct);

CREATE TABLE child_life_losses (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES child_game_state(user_id) ON DELETE CASCADE,
    attempt_id      INTEGER NOT NULL UNIQUE,
    attempt_correct INTEGER NOT NULL DEFAULT 0 CHECK (attempt_correct = 0),
    lives_after     INTEGER NOT NULL CHECK (lives_after BETWEEN 0 AND 4),
    lost_at         TEXT    NOT NULL,
    FOREIGN KEY (attempt_id, user_id, attempt_correct) REFERENCES listening_attempts(id, user_id, is_correct) ON DELETE CASCADE
);
CREATE INDEX idx_child_life_losses_user ON child_life_losses(user_id, lost_at);   -- a child's recent losses

-- Editorial seed: the existing "College & Work" content (a campus-life scenario) is aimed at teens and adults. Nothing else
-- is restricted, and adults and teens still see every lesson, situation and activity they saw before.
INSERT INTO lesson_age_groups(lesson_id, age_group_id)
SELECT l.id, g.id FROM lessons l, age_groups g WHERE l.slug = 'college' AND g.code IN ('teen', 'adult');
INSERT INTO situation_age_groups(situation_id, age_group_id)
SELECT s.id, g.id FROM situations s, age_groups g WHERE s.slug = 'college' AND g.code IN ('teen', 'adult');
INSERT INTO listening_activity_age_groups(activity_id, age_group_id)
SELECT a.id, g.id FROM listening_activities a, age_groups g WHERE a.slug IN ('college-meaning', 'college-phrase') AND g.code IN ('teen', 'adult');

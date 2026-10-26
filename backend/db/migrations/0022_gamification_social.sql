-- Phase 10: gamification and a minimal social layer. Additive only; no existing table or column changes.
--
-- Design notes
--  * Nothing here replaces or competes with an existing progress system. XP is a LEDGER of rewards for things the learner has
--    already done in the existing tables (exercise/lesson/situation/listening/speaking/daily-task rows); the server credits
--    them, once each (UNIQUE (user_id, kind, source_id)), and a client can neither send nor change an amount. "Local
--    Confidence" (Phase 6) is untouched and stays the learning metric.
--  * Total XP, level, streak length, freeze balance and challenge progress are DERIVED from these ledgers, never stored.
--  * xp_events.source_id deliberately has no foreign key (it points into one of several tables chosen by `kind`): the ledger
--    must survive content being edited or removed.
--  * Social is friends only, by one-time-style friend codes (no search, no listing of strangers), and the server refuses it
--    for the child age group.

-- Per-learner settings. timezone decides which calendar day an activity belongs to; friend_code is created on first use.
CREATE TABLE learner_gamification (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    timezone    TEXT    NOT NULL DEFAULT 'UTC' CHECK (length(timezone) BETWEEN 1 AND 64),
    friend_code TEXT    UNIQUE CHECK (friend_code IS NULL OR length(friend_code) = 10),
    created_at  TEXT    NOT NULL
);

-- The XP ledger (append only: rows can be created and cascade-deleted with the learner, never edited).
CREATE TABLE xp_events (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind       TEXT    NOT NULL CHECK (kind IN ('exercise', 'lesson', 'situation', 'listening', 'speaking', 'daily_task', 'challenge')),
    source_id  INTEGER NOT NULL CHECK (source_id > 0),
    xp         INTEGER NOT NULL CHECK (xp BETWEEN 0 AND 100),         -- 0 = recognised but over the daily cap
    earned_at  TEXT    NOT NULL,                                      -- when the underlying activity happened (UTC)
    day        TEXT    NOT NULL CHECK (day GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(day) IS day),   -- the learner's local date
    created_at TEXT    NOT NULL,
    UNIQUE (user_id, kind, source_id)                                 -- one reward per thing done: replays cannot pay twice
);
CREATE INDEX idx_xp_events_user_day ON xp_events(user_id, day);
CREATE TRIGGER xp_events_append_only BEFORE UPDATE ON xp_events BEGIN SELECT RAISE(ABORT, 'xp events cannot be changed'); END;

-- One row per local day on which the learner did something meaningful (an XP-earning activity). A day counts once however
-- often it is repeated.
CREATE TABLE streak_days (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day     TEXT    NOT NULL CHECK (day GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(day) IS day),
    PRIMARY KEY (user_id, day)
);

-- The streak-freeze ledger. 'earned' rows are credits (dated by the day they were earned), 'used' rows are the missed day the
-- freeze protected. UNIQUE (user_id, kind, day) means one freeze per missed day and one credit per day. Balance = earned - used,
-- and the triggers keep it between 0 and 2 whatever the application does (the 2 is tied to settings by a test).
CREATE TABLE streak_freezes (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind       TEXT    NOT NULL CHECK (kind IN ('earned', 'used')),
    day        TEXT    NOT NULL CHECK (day GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(day) IS day),
    created_at TEXT    NOT NULL,
    UNIQUE (user_id, kind, day)
);
CREATE TRIGGER streak_freezes_no_overdraw BEFORE INSERT ON streak_freezes
WHEN NEW.kind = 'used' AND (SELECT COUNT(*) FROM streak_freezes WHERE user_id = NEW.user_id AND kind = 'earned')
                         - (SELECT COUNT(*) FROM streak_freezes WHERE user_id = NEW.user_id AND kind = 'used') < 1
BEGIN SELECT RAISE(ABORT, 'no streak freeze available'); END;
CREATE TRIGGER streak_freezes_cap BEFORE INSERT ON streak_freezes
WHEN NEW.kind = 'earned' AND (SELECT COUNT(*) FROM streak_freezes WHERE user_id = NEW.user_id AND kind = 'earned')
                           - (SELECT COUNT(*) FROM streak_freezes WHERE user_id = NEW.user_id AND kind = 'used') >= 2
BEGIN SELECT RAISE(ABORT, 'streak freeze limit reached'); END;
CREATE TRIGGER streak_freezes_append_only BEFORE UPDATE ON streak_freezes BEGIN SELECT RAISE(ABORT, 'streak freezes cannot be changed'); END;

-- Achievements are data: a metric the server can compute and a threshold. Few, on purpose.
CREATE TABLE achievements (
    id          INTEGER PRIMARY KEY,
    code        TEXT    NOT NULL UNIQUE CHECK (length(trim(code)) > 0),
    title       TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    description TEXT    NOT NULL,
    metric      TEXT    NOT NULL CHECK (metric IN ('lessons_completed', 'situations_completed', 'listening_correct', 'speaking_completed',
                                                   'longest_streak', 'challenges_claimed', 'total_xp')),
    threshold   INTEGER NOT NULL CHECK (threshold > 0),
    sort_order  INTEGER NOT NULL,
    UNIQUE (metric, threshold)
);
CREATE TABLE learner_achievements (
    user_id        INTEGER NOT NULL REFERENCES users(id)        ON DELETE CASCADE,
    achievement_id INTEGER NOT NULL REFERENCES achievements(id) ON DELETE RESTRICT,
    unlocked_at    TEXT    NOT NULL,
    PRIMARY KEY (user_id, achievement_id)                       -- unlocked once; there is no way to unlock twice
);
CREATE INDEX idx_learner_achievements_achievement ON learner_achievements(achievement_id);

-- Challenges: definitions, and one instance per learner per period. Progress is derived from the XP ledger (and the streak),
-- not stored; claimed_at is the only state, and a guarded UPDATE plus UNIQUE xp_events row make the reward payable once.
CREATE TABLE challenges (
    id         INTEGER PRIMARY KEY,
    code       TEXT    NOT NULL UNIQUE CHECK (length(trim(code)) > 0),
    title      TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    period     TEXT    NOT NULL CHECK (period IN ('daily', 'weekly')),
    metric     TEXT    NOT NULL CHECK (metric IN ('exercises', 'listening', 'lessons', 'xp', 'streak')),
    target     INTEGER NOT NULL CHECK (target > 0),
    reward_xp  INTEGER NOT NULL CHECK (reward_xp BETWEEN 1 AND 100),
    active     INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    sort_order INTEGER NOT NULL
);
CREATE TABLE learner_challenges (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id)      ON DELETE CASCADE,
    challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE RESTRICT,
    period_start TEXT    NOT NULL CHECK (period_start GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(period_start) IS period_start),
    period_end   TEXT    NOT NULL CHECK (period_end   GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(period_end) IS period_end),
    claimed_at   TEXT,
    CHECK (period_end >= period_start),
    UNIQUE (user_id, challenge_id, period_start)
);
CREATE INDEX idx_learner_challenges_user ON learner_challenges(user_id, period_start);

-- Friends. A request is between two different learners; only one pending request may exist for a pair, in either direction.
CREATE TABLE friend_requests (
    id           INTEGER PRIMARY KEY,
    requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    addressee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status       TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    created_at   TEXT    NOT NULL,
    responded_at TEXT,
    CHECK (requester_id <> addressee_id),
    CHECK ((status = 'pending') = (responded_at IS NULL))
);
CREATE UNIQUE INDEX uq_friend_request_pending_pair ON friend_requests (MIN(requester_id, addressee_id), MAX(requester_id, addressee_id)) WHERE status = 'pending';
CREATE INDEX idx_friend_requests_addressee ON friend_requests(addressee_id, status);
CREATE INDEX idx_friend_requests_requester ON friend_requests(requester_id, status);

-- A friendship is stored once per pair, smaller id first, so (a, b) and (b, a) are the same row.
CREATE TABLE friendships (
    id         INTEGER PRIMARY KEY,
    user_low   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_high  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL,
    CHECK (user_low < user_high),
    UNIQUE (user_low, user_high)
);
CREATE INDEX idx_friendships_high ON friendships(user_high);

-- Seed: a handful of achievements and challenges (editable data, not code).
INSERT INTO achievements(code, title, description, metric, threshold, sort_order) VALUES
  ('first_lesson',    'First lesson',       'Complete your first lesson.',            'lessons_completed',    1,   1),
  ('first_situation', 'First situation',    'Complete your first real-life situation.', 'situations_completed', 1,   2),
  ('listening_10',    'Good listener',      'Get 10 listening activities right.',     'listening_correct',    10,  3),
  ('speaking_5',      'Finding your voice', 'Complete 5 speaking practices.',         'speaking_completed',   5,   4),
  ('streak_3',        'Three in a row',     'Learn on 3 days in a row.',              'longest_streak',       3,   5),
  ('streak_7',        'A full week',        'Learn on 7 days in a row.',              'longest_streak',       7,   6),
  ('challenge_1',     'Challenge accepted', 'Claim your first challenge reward.',     'challenges_claimed',   1,   7),
  ('xp_100',          '100 XP',             'Earn 100 XP.',                           'total_xp',             100, 8),
  ('xp_500',          '500 XP',             'Earn 500 XP.',                           'total_xp',             500, 9);

INSERT INTO challenges(code, title, period, metric, target, reward_xp, sort_order) VALUES
  ('daily_exercises', 'Answer 5 exercises correctly',  'daily',  'exercises', 5,   15, 1),
  ('daily_listening', 'Get 3 listening activities right', 'daily', 'listening', 3, 15, 2),
  ('daily_xp',        'Earn 30 XP today',              'daily',  'xp',        30,  10, 3),
  ('weekly_lessons',  'Complete 2 lessons this week',  'weekly', 'lessons',   2,   40, 4),
  ('weekly_xp',       'Earn 200 XP this week',         'weekly', 'xp',        200, 50, 5),
  ('weekly_streak',   'Keep a 5-day streak',           'weekly', 'streak',    5,   40, 6);

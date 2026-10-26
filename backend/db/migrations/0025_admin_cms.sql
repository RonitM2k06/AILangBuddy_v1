-- Phase 13: admin CMS + analytics. Additive only: one new table, publish metadata on the three content tables that already have a lifecycle,
-- database-level protection against deleting content that learner evidence hangs off, and a few time-window indexes.
-- Nothing here rewrites learner evidence, and there are no analytics tables (every metric is derived from the evidence that already exists).

-- ---------- admin audit log (append-only) ----------
-- Who changed which content, when, and with what outcome. The actor is always the authenticated session, never the request body.
-- meta_json only ever holds an allow-list of safe keys (see backend/admin/audit.py): never answer text, learner content or secrets.
-- action has no 'delete': the CMS has no delete. 'config_change' and 'login_denied' are reserved (Phase 13 has no admin config to change).
CREATE TABLE admin_audit_log (
    id            INTEGER PRIMARY KEY,
    occurred_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    actor_label   TEXT    NOT NULL CHECK (length(trim(actor_label)) BETWEEN 1 AND 64),     -- the actor's handle at the time, so the log still reads after the account is gone
    action        TEXT    NOT NULL CHECK (action IN ('create', 'update', 'publish', 'unpublish', 'archive', 'restore', 'validation_failed', 'config_change', 'login_denied')),
    entity_type   TEXT    NOT NULL CHECK (entity_type IN ('lesson', 'exercise', 'lesson_vocabulary', 'situation', 'situation_step', 'listening_activity', 'listening_option',
                                                         'vocabulary', 'vocabulary_translation', 'topic', 'admin_access', 'config')),
    entity_id     INTEGER,
    entity_key    TEXT    CHECK (entity_key IS NULL OR length(entity_key) <= 120),         -- a slug / code snapshot
    outcome       TEXT    NOT NULL CHECK (outcome IN ('ok', 'rejected')),
    meta_json     TEXT    NOT NULL DEFAULT '{}' CHECK (json_valid(meta_json) AND length(CAST(meta_json AS BLOB)) <= 4096),
    request_id    TEXT    CHECK (request_id IS NULL OR length(request_id) <= 64)
);
CREATE INDEX idx_admin_audit_time   ON admin_audit_log(occurred_at);
CREATE INDEX idx_admin_audit_entity ON admin_audit_log(entity_type, entity_id, occurred_at);
CREATE INDEX idx_admin_audit_actor  ON admin_audit_log(actor_user_id, occurred_at);

-- Immutable, like the XP ledger. The single allowed change is the foreign key's own ON DELETE SET NULL (an account removed later): the
-- trigger lets actor_user_id go from a value to NULL provided every other column is untouched. actor_label keeps the who.
CREATE TRIGGER admin_audit_log_no_update BEFORE UPDATE ON admin_audit_log
WHEN NOT (OLD.actor_user_id IS NOT NULL AND NEW.actor_user_id IS NULL
          AND NEW.id IS OLD.id AND NEW.occurred_at IS OLD.occurred_at AND NEW.actor_label IS OLD.actor_label AND NEW.action IS OLD.action
          AND NEW.entity_type IS OLD.entity_type AND NEW.entity_id IS OLD.entity_id AND NEW.entity_key IS OLD.entity_key
          AND NEW.outcome IS OLD.outcome AND NEW.meta_json IS OLD.meta_json AND NEW.request_id IS OLD.request_id)
BEGIN SELECT RAISE(ABORT, 'admin audit events cannot be changed'); END;
CREATE TRIGGER admin_audit_log_no_delete BEFORE DELETE ON admin_audit_log
BEGIN SELECT RAISE(ABORT, 'admin audit events cannot be deleted'); END;

-- ---------- publish metadata on the lifecycle-bearing content ----------
-- revision is the optimistic-concurrency token: every admin edit increments it and a stale one is refused (409).
-- (ADD COLUMN cannot take a non-constant default, so the timestamps are nullable and are set by the admin service and backfilled here.)
ALTER TABLE lessons ADD COLUMN published_at TEXT;
ALTER TABLE lessons ADD COLUMN archived_at  TEXT;
ALTER TABLE lessons ADD COLUMN updated_at   TEXT;
ALTER TABLE lessons ADD COLUMN revision     INTEGER NOT NULL DEFAULT 1;
ALTER TABLE situations ADD COLUMN published_at TEXT;
ALTER TABLE situations ADD COLUMN archived_at  TEXT;
ALTER TABLE situations ADD COLUMN updated_at   TEXT;
ALTER TABLE situations ADD COLUMN revision     INTEGER NOT NULL DEFAULT 1;
ALTER TABLE listening_activities ADD COLUMN published_at TEXT;
ALTER TABLE listening_activities ADD COLUMN archived_at  TEXT;
ALTER TABLE listening_activities ADD COLUMN updated_at   TEXT;
ALTER TABLE listening_activities ADD COLUMN revision     INTEGER NOT NULL DEFAULT 1;

-- Existing rows keep their status (published stays published); only the new metadata is filled in.
UPDATE lessons SET updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now'),
    published_at = CASE WHEN status = 'published' THEN strftime('%Y-%m-%d %H:%M:%S', 'now') END,
    archived_at  = CASE WHEN status = 'archived'  THEN strftime('%Y-%m-%d %H:%M:%S', 'now') END;
UPDATE situations SET updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now'),
    published_at = CASE WHEN status = 'published' THEN strftime('%Y-%m-%d %H:%M:%S', 'now') END,
    archived_at  = CASE WHEN status = 'archived'  THEN strftime('%Y-%m-%d %H:%M:%S', 'now') END;
UPDATE listening_activities SET updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now'),
    published_at = CASE WHEN status = 'published' THEN strftime('%Y-%m-%d %H:%M:%S', 'now') END,
    archived_at  = CASE WHEN status = 'archived'  THEN strftime('%Y-%m-%d %H:%M:%S', 'now') END;

-- ---------- archive integrity: an archived row always says when ----------
-- A CHECK cannot be added to an existing table, so triggers carry it. They STAMP rather than refuse: the earlier phases' own tests archive content with a bare
-- UPDATE ... SET status = 'archived', and that must keep working, but the invariant still holds because the row gets its archive time in the same statement.
-- (The admin service sets archived_at itself, to the same instant it sets the status. Leaving the archive clears it, because then NEW.status is not 'archived'.)
CREATE TRIGGER lessons_archived_stamp_insert AFTER INSERT ON lessons
WHEN NEW.status = 'archived' AND NEW.archived_at IS NULL
BEGIN UPDATE lessons SET archived_at = strftime('%Y-%m-%d %H:%M:%S', 'now') WHERE id = NEW.id; END;
CREATE TRIGGER lessons_archived_stamp_update AFTER UPDATE ON lessons
WHEN NEW.status = 'archived' AND NEW.archived_at IS NULL
BEGIN UPDATE lessons SET archived_at = strftime('%Y-%m-%d %H:%M:%S', 'now') WHERE id = NEW.id; END;
CREATE TRIGGER situations_archived_stamp_insert AFTER INSERT ON situations
WHEN NEW.status = 'archived' AND NEW.archived_at IS NULL
BEGIN UPDATE situations SET archived_at = strftime('%Y-%m-%d %H:%M:%S', 'now') WHERE id = NEW.id; END;
CREATE TRIGGER situations_archived_stamp_update AFTER UPDATE ON situations
WHEN NEW.status = 'archived' AND NEW.archived_at IS NULL
BEGIN UPDATE situations SET archived_at = strftime('%Y-%m-%d %H:%M:%S', 'now') WHERE id = NEW.id; END;
CREATE TRIGGER listening_activities_archived_stamp_insert AFTER INSERT ON listening_activities
WHEN NEW.status = 'archived' AND NEW.archived_at IS NULL
BEGIN UPDATE listening_activities SET archived_at = strftime('%Y-%m-%d %H:%M:%S', 'now') WHERE id = NEW.id; END;
CREATE TRIGGER listening_activities_archived_stamp_update AFTER UPDATE ON listening_activities
WHEN NEW.status = 'archived' AND NEW.archived_at IS NULL
BEGIN UPDATE listening_activities SET archived_at = strftime('%Y-%m-%d %H:%M:%S', 'now') WHERE id = NEW.id; END;

-- ---------- delete protection: content that learner evidence depends on cannot be deleted ----------
-- Derived from PRAGMA foreign_key_list on the 0024 schema (tests/test_admin_migration.py re-derives it and fails if a new cascade appears
-- that no trigger covers). Only references that would DESTROY evidence are guarded:
--   lessons              <- lesson_progress, exercise_attempts (via exercises), completed/skipped daily_tasks
--   situations           <- situation_progress, situation_step_attempts (via steps), roleplay_sessions (turns, grades, feedback), completed/skipped daily_tasks
--   listening_activities <- listening_attempts
--   exercises            <- exercise_attempts
--   situation_steps      <- situation_step_attempts, roleplay_turns
--   vocabulary_items     <- weaknesses (item)
--   topics               <- weaknesses (topic), completed/skipped daily_tasks
-- Deliberately NOT guarded, because the earlier phases document and test them as intended: a PENDING daily task is a plan row (it cascades with
-- its lesson/situation/topic), and SET NULL references (confidence_scores / tutor_conversations context links) keep the learner's own row.
-- References that are RESTRICT already refuse the delete (e.g. attempts -> answers/options, evidence -> vocabulary).
CREATE TRIGGER lessons_protect_evidence BEFORE DELETE ON lessons
WHEN EXISTS (SELECT 1 FROM lesson_progress WHERE lesson_id = OLD.id)
  OR EXISTS (SELECT 1 FROM exercise_attempts ea JOIN exercises e ON e.id = ea.exercise_id WHERE e.lesson_id = OLD.id)
  OR EXISTS (SELECT 1 FROM daily_tasks WHERE lesson_id = OLD.id AND status <> 'pending')
BEGIN SELECT RAISE(ABORT, 'a lesson with learner evidence cannot be deleted: archive it'); END;

CREATE TRIGGER situations_protect_evidence BEFORE DELETE ON situations
WHEN EXISTS (SELECT 1 FROM situation_progress WHERE situation_id = OLD.id)
  OR EXISTS (SELECT 1 FROM situation_step_attempts sa JOIN situation_steps st ON st.id = sa.step_id WHERE st.situation_id = OLD.id)
  OR EXISTS (SELECT 1 FROM roleplay_sessions WHERE situation_id = OLD.id)
  OR EXISTS (SELECT 1 FROM daily_tasks WHERE situation_id = OLD.id AND status <> 'pending')
BEGIN SELECT RAISE(ABORT, 'a situation with learner evidence cannot be deleted: archive it'); END;

CREATE TRIGGER listening_activities_protect_evidence BEFORE DELETE ON listening_activities
WHEN EXISTS (SELECT 1 FROM listening_attempts WHERE activity_id = OLD.id)
BEGIN SELECT RAISE(ABORT, 'a listening activity with learner evidence cannot be deleted: archive it'); END;

CREATE TRIGGER exercises_protect_evidence BEFORE DELETE ON exercises
WHEN EXISTS (SELECT 1 FROM exercise_attempts WHERE exercise_id = OLD.id)
BEGIN SELECT RAISE(ABORT, 'an exercise with learner attempts cannot be deleted'); END;

CREATE TRIGGER situation_steps_protect_evidence BEFORE DELETE ON situation_steps
WHEN EXISTS (SELECT 1 FROM situation_step_attempts WHERE step_id = OLD.id)
  OR EXISTS (SELECT 1 FROM roleplay_turns WHERE step_id = OLD.id)
BEGIN SELECT RAISE(ABORT, 'a situation step with learner evidence cannot be deleted'); END;

CREATE TRIGGER vocabulary_items_protect_evidence BEFORE DELETE ON vocabulary_items
WHEN EXISTS (SELECT 1 FROM weaknesses WHERE item_id = OLD.id)
BEGIN SELECT RAISE(ABORT, 'vocabulary with learner weakness evidence cannot be deleted'); END;

CREATE TRIGGER topics_protect_evidence BEFORE DELETE ON topics
WHEN EXISTS (SELECT 1 FROM weaknesses WHERE topic_id = OLD.id)
  OR EXISTS (SELECT 1 FROM daily_tasks WHERE topic_id = OLD.id AND status <> 'pending')
BEGIN SELECT RAISE(ABORT, 'a topic with learner evidence cannot be deleted'); END;

-- ---------- time-window indexes for cross-learner analytics ----------
-- DAU/WAU/MAU and every windowed rate read "which learners did X between t0 and t1" across ALL learners. The 0001-0024 indexes all lead with
-- user_id, so these queries scanned the whole table (EXPLAIN QUERY PLAN: SCAN). Each index leads with the timestamp and carries user_id, so the
-- window is a SEARCH on a covering index (tests/test_admin_migration.py asserts the plan for each one).
CREATE INDEX idx_exercise_attempts_time       ON exercise_attempts(attempted_at, user_id);
CREATE INDEX idx_situation_step_attempts_time ON situation_step_attempts(attempted_at, user_id);
CREATE INDEX idx_listening_attempts_time      ON listening_attempts(attempted_at, user_id);
CREATE INDEX idx_speaking_sessions_time       ON speaking_sessions(created_at, user_id);
CREATE INDEX idx_pronunciation_time           ON pronunciation_assessments(created_at, user_id);
CREATE INDEX idx_roleplay_turns_time          ON roleplay_turns(created_at, user_id);
CREATE INDEX idx_ai_micro_attempts_time       ON ai_micro_lesson_attempts(attempted_at, user_id);
CREATE INDEX idx_xp_events_time               ON xp_events(earned_at, user_id);

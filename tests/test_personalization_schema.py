import sqlite3

import pytest

from backend.db import connect

from .pers import ts


def one(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def fails(db_path, sql, *args):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute(sql, args)


DEMO = "(SELECT id FROM users WHERE handle='demo-alex')"
HI = "(SELECT id FROM languages WHERE code='hi')"
FOOD = "(SELECT id FROM topics WHERE slug='food')"
SHOP = "(SELECT id FROM topics WHERE slug='shopping')"
SKILL = "(SELECT id FROM skills WHERE code='vocabulary')"


# ---------- skills and exercise difficulty ----------
def test_skills_seeded_and_unique(db_path):
    with connect(db_path) as conn:
        assert [r[0] for r in conn.execute("SELECT code FROM skills ORDER BY id")] == ["vocabulary", "grammar", "conversation"]
    fails(db_path, "INSERT INTO skills(code, name) VALUES ('vocabulary', 'dup')")


def test_exercise_difficulty_scale_and_seeded_mapping(db_path):
    with connect(db_path) as conn:
        got = {r["kind"]: r["d"] for r in conn.execute("SELECT kind, MIN(difficulty) AS d FROM exercises GROUP BY kind")}
        assert got == {"multiple_choice": 1, "fill_blank": 2, "translation": 3}
        assert one(conn, "SELECT COUNT(*) FROM exercises WHERE difficulty NOT BETWEEN 1 AND 3") == 0
        assert one(conn, "SELECT COUNT(*) FROM (SELECT kind FROM exercises GROUP BY kind HAVING MIN(difficulty) <> MAX(difficulty))") == 0
    fails(db_path, "UPDATE exercises SET difficulty = 0 WHERE id = 1")
    fails(db_path, "UPDATE exercises SET difficulty = 4 WHERE id = 1")
    fails(db_path, "UPDATE exercises SET difficulty = NULL WHERE id = 1")


def test_new_exercises_default_to_the_easiest_level(db_path):
    with connect(db_path) as conn:
        conn.execute(f"INSERT INTO exercises(lesson_id, language_id, kind, prompt, sort_order) VALUES ((SELECT id FROM lessons WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')), {HI}, 'fill_blank', 'p', 50)")
        assert one(conn, "SELECT difficulty FROM exercises WHERE sort_order = 50") == 1


def test_seeded_exercise_content_is_untouched(db_path):
    """Phase 6 adds metadata only: the Phase 4 content (19 exercises, 41 answers, 14+5 prompts/answers) is unchanged."""
    with connect(db_path) as conn:
        assert one(conn, "SELECT COUNT(*) FROM exercises WHERE language_id = (SELECT id FROM languages WHERE code='hi')") == 19                   # the Hindi seed (Marathi's come from 0031)
        assert one(conn, "SELECT COUNT(*), SUM(is_correct) FROM exercise_answers a JOIN exercises e ON e.id = a.exercise_id WHERE e.language_id = (SELECT id FROM languages WHERE code='hi')") == 41
        assert one(conn, "SELECT prompt FROM exercises WHERE kind='multiple_choice' ORDER BY id LIMIT 1") == "What does “Namaste” mean?"
        assert one(conn, "SELECT answer_text FROM exercise_answers WHERE exercise_id=1 AND is_correct=1") == "A respectful hello"


# ---------- confidence_scores ----------
CONF = "INSERT INTO confidence_scores(user_id, language_id, topic_id, skill_id, score, source, lesson_id, situation_id, recorded_at) VALUES "


@pytest.mark.parametrize("values", [
    f"({DEMO}, {HI}, NULL, NULL, 50, 'self_report', NULL, NULL, '2026-01-01 00:00:00')",          # no dimension
    f"({DEMO}, {HI}, {FOOD}, {SKILL}, 50, 'self_report', NULL, NULL, '2026-01-01 00:00:00')",      # both dimensions
    f"({DEMO}, {HI}, {FOOD}, NULL, -1, 'self_report', NULL, NULL, '2026-01-01 00:00:00')",         # score range
    f"({DEMO}, {HI}, {FOOD}, NULL, 101, 'self_report', NULL, NULL, '2026-01-01 00:00:00')",
    f"({DEMO}, {HI}, {FOOD}, NULL, 50, 'guess', NULL, NULL, '2026-01-01 00:00:00')",               # source vocabulary
    f"({DEMO}, {HI}, {FOOD}, NULL, 50, 'lesson', 1, 1, '2026-01-01 00:00:00')",                    # lesson and situation together
    f"(999, {HI}, {FOOD}, NULL, 50, 'self_report', NULL, NULL, '2026-01-01 00:00:00')",            # unknown user
    f"({DEMO}, {HI}, (SELECT 999), NULL, 50, 'self_report', NULL, NULL, '2026-01-01 00:00:00')",   # unknown topic
    f"({DEMO}, {HI}, {FOOD}, NULL, NULL, 'self_report', NULL, NULL, '2026-01-01 00:00:00')",       # score required
])
def test_confidence_constraints(db_path, values):
    fails(db_path, CONF + values)


def test_confidence_accepts_topic_or_skill_and_keeps_history(db_path):
    with connect(db_path) as conn:
        conn.execute(CONF + f"({DEMO}, {HI}, {FOOD}, NULL, 40, 'self_report', NULL, NULL, '2026-01-01 00:00:00')")
        conn.execute(CONF + f"({DEMO}, {HI}, {FOOD}, NULL, 70, 'lesson', (SELECT id FROM lessons WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')), NULL, '2026-01-02 00:00:00')")
        conn.execute(CONF + f"({DEMO}, {HI}, NULL, {SKILL}, 60, 'situation', NULL, (SELECT id FROM situations WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')), '2026-01-03 00:00:00')")
        assert one(conn, "SELECT COUNT(*) FROM confidence_scores") == 3                # every report is kept


def test_confidence_cascades_and_context_survives_content_deletion(db_path):
    with connect(db_path) as conn:
        conn.execute(CONF + f"({DEMO}, {HI}, {FOOD}, NULL, 70, 'lesson', (SELECT id FROM lessons WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')), NULL, '2026-01-02 00:00:00')")
        conn.execute("DELETE FROM lessons WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')")                          # the rating outlives the lesson it followed
        assert one(conn, "SELECT COUNT(*) FROM confidence_scores") == 1
        assert one(conn, "SELECT lesson_id FROM confidence_scores") is None
        conn.execute("DELETE FROM users WHERE handle='demo-alex'")
        assert one(conn, "SELECT COUNT(*) FROM confidence_scores") == 0


# ---------- weaknesses ----------
WK = "INSERT INTO weaknesses(user_id, language_id, rule, topic_id, item_id, severity, attempts, incorrect, last_evidence_at, detected_at, status, resolved_at) VALUES "
ITEM = "(SELECT id FROM vocabulary_items WHERE pronunciation='Paani milega?')"
OK_TOPIC = f"({DEMO}, {HI}, 'low_topic_accuracy', {FOOD}, NULL, 'low', 6, 3, '2026-01-01 00:00:00', '2026-01-01 00:00:00', 'active', NULL)"


@pytest.mark.parametrize("values", [
    f"({DEMO}, {HI}, 'low_topic_accuracy', NULL, {ITEM}, 'low', 6, 3, 'a', 'b', 'active', NULL)",        # rule/subject mismatch
    f"({DEMO}, {HI}, 'repeated_item_errors', {FOOD}, NULL, 'low', 6, 3, 'a', 'b', 'active', NULL)",
    f"({DEMO}, {HI}, 'low_topic_accuracy', {FOOD}, {ITEM}, 'low', 6, 3, 'a', 'b', 'active', NULL)",      # two subjects
    f"({DEMO}, {HI}, 'low_topic_accuracy', NULL, NULL, 'low', 6, 3, 'a', 'b', 'active', NULL)",          # no subject
    f"({DEMO}, {HI}, 'mystery', {FOOD}, NULL, 'low', 6, 3, 'a', 'b', 'active', NULL)",                   # rule vocabulary
    f"({DEMO}, {HI}, 'low_topic_accuracy', {FOOD}, NULL, 'critical', 6, 3, 'a', 'b', 'active', NULL)",   # severity vocabulary
    f"({DEMO}, {HI}, 'low_topic_accuracy', {FOOD}, NULL, 'low', 6, 7, 'a', 'b', 'active', NULL)",        # incorrect > attempts
    f"({DEMO}, {HI}, 'low_topic_accuracy', {FOOD}, NULL, 'low', 6, 0, 'a', 'b', 'active', NULL)",        # a weakness has at least one mistake
    f"({DEMO}, {HI}, 'low_topic_accuracy', {FOOD}, NULL, 'low', 0, 0, 'a', 'b', 'active', NULL)",
    f"({DEMO}, {HI}, 'low_topic_accuracy', {FOOD}, NULL, 'low', 6, 3, 'a', 'b', 'resolved', NULL)",      # resolved needs a time
    f"({DEMO}, {HI}, 'low_topic_accuracy', {FOOD}, NULL, 'low', 6, 3, 'a', 'b', 'active', 'c')",         # active must not have one
    f"({DEMO}, {HI}, 'low_topic_accuracy', {FOOD}, NULL, 'low', 6, 3, 'a', 'b', 'snoozed', NULL)",
])
def test_weakness_constraints(db_path, values):
    fails(db_path, WK + values)


def test_one_weakness_row_per_subject(db_path):
    with connect(db_path) as conn:
        conn.execute(WK + OK_TOPIC)
        conn.execute(WK + f"({DEMO}, {HI}, 'low_topic_accuracy', {SHOP}, NULL, 'low', 6, 3, 'a', 'b', 'active', NULL)")             # other topic
        conn.execute(WK + f"({DEMO}, (SELECT id FROM languages WHERE code='hinglish'), 'low_topic_accuracy', {FOOD}, NULL, 'low', 6, 3, 'a', 'b', 'active', NULL)")  # other language
        conn.execute(WK + f"({DEMO}, {HI}, 'repeated_item_errors', NULL, {ITEM}, 'low', 3, 3, 'a', 'b', 'active', NULL)")
    fails(db_path, WK + OK_TOPIC)
    fails(db_path, WK + f"({DEMO}, {HI}, 'repeated_item_errors', NULL, {ITEM}, 'high', 9, 9, 'a', 'b', 'active', NULL)")


def test_weakness_rows_are_per_user_and_cascade(db_path):
    with connect(db_path) as conn:
        conn.execute("INSERT INTO users(handle, display_name) VALUES ('other', 'Other')")
        conn.execute(WK + OK_TOPIC)
        conn.execute(WK + OK_TOPIC.replace(DEMO, "(SELECT id FROM users WHERE handle='other')"))   # same subject, different learner
        assert one(conn, "SELECT COUNT(*) FROM weaknesses") == 2
        conn.execute("DELETE FROM users WHERE handle='demo-alex'")
        assert one(conn, "SELECT COUNT(*) FROM weaknesses") == 1


# ---------- daily_tasks ----------
TASK = "INSERT INTO daily_tasks(user_id, language_id, plan_date, priority, task_type, source, lesson_id, situation_id, topic_id, status, created_at, completed_at) VALUES "
LESSON = "(SELECT id FROM lessons WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi'))"
SIT = "(SELECT id FROM situations WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi'))"
T1 = f"({DEMO}, {HI}, '2026-09-30', 1, 'study_lesson', 'next_lesson', {LESSON}, NULL, NULL, 'pending', '2026-09-30 08:00:00', NULL)"


@pytest.mark.parametrize("values", [
    f"({DEMO}, {HI}, '2026-09-30', 2, 'study_lesson', 'next_lesson', NULL, NULL, NULL, 'pending', 'c', NULL)",                 # no target
    f"({DEMO}, {HI}, '2026-09-30', 2, 'study_lesson', 'next_lesson', {LESSON}, {SIT}, NULL, 'pending', 'c', NULL)",            # two targets
    f"({DEMO}, {HI}, '2026-09-30', 2, 'study_lesson', 'next_lesson', NULL, {SIT}, NULL, 'pending', 'c', NULL)",                # type/target mismatch
    f"({DEMO}, {HI}, '2026-09-30', 2, 'practice_situation', 'next_lesson', {LESSON}, NULL, NULL, 'pending', 'c', NULL)",
    f"({DEMO}, {HI}, '2026-09-30', 2, 'confidence_checkin', 'confidence_checkin', {LESSON}, NULL, NULL, 'pending', 'c', NULL)",
    f"({DEMO}, {HI}, '2026-09-30', 2, 'homework', 'next_lesson', {LESSON}, NULL, NULL, 'pending', 'c', NULL)",               # task_type vocabulary
    f"({DEMO}, {HI}, '2026-09-30', 2, 'study_lesson', 'magic', {LESSON}, NULL, NULL, 'pending', 'c', NULL)",                   # source vocabulary
    f"({DEMO}, {HI}, '2026-09-30', 0, 'study_lesson', 'next_lesson', {LESSON}, NULL, NULL, 'pending', 'c', NULL)",            # priority >= 1
    f"({DEMO}, {HI}, '2026-13-45', 2, 'study_lesson', 'next_lesson', {LESSON}, NULL, NULL, 'pending', 'c', NULL)",            # not a date
    f"({DEMO}, {HI}, '30/09/2026', 2, 'study_lesson', 'next_lesson', {LESSON}, NULL, NULL, 'pending', 'c', NULL)",
    f"({DEMO}, {HI}, '2026-09-30', 2, 'study_lesson', 'next_lesson', {LESSON}, NULL, NULL, 'done', 'c', NULL)",               # done needs completed_at
    f"({DEMO}, {HI}, '2026-09-30', 2, 'study_lesson', 'next_lesson', {LESSON}, NULL, NULL, 'pending', 'c', 'd')",             # pending must not have it
    f"({DEMO}, {HI}, '2026-09-30', 2, 'study_lesson', 'next_lesson', {LESSON}, NULL, NULL, 'later', 'c', NULL)",
    f"(999, {HI}, '2026-09-30', 2, 'study_lesson', 'next_lesson', {LESSON}, NULL, NULL, 'pending', 'c', NULL)",                # unknown user
])
def test_daily_task_constraints(db_path, values):
    fails(db_path, TASK + values)


def test_no_duplicate_tasks_for_the_same_learner_and_day(db_path):
    with connect(db_path) as conn:
        conn.execute(TASK + T1)
    fails(db_path, TASK + T1.replace("1, 'study_lesson'", "2, 'study_lesson'"))                        # same target, same day (other priority)
    fails(db_path, TASK + T1.replace("'study_lesson', 'next_lesson', " + LESSON, "'practice_situation', 'next_situation', NULL").replace("NULL, NULL, 'pending'", f"{SIT}, NULL, 'pending'").replace("1, 'practice", "1, 'practice"))  # same priority slot
    with connect(db_path) as conn:
        conn.execute(TASK + T1.replace("2026-09-30", "2026-10-01"))                                     # same task on another day is fine
        conn.execute(TASK + f"({DEMO}, {HI}, '2026-09-30', 2, 'practice_situation', 'next_situation', NULL, {SIT}, NULL, 'pending', 'c', NULL)")
        conn.execute(TASK + f"({DEMO}, {HI}, '2026-09-30', 3, 'confidence_checkin', 'confidence_checkin', NULL, NULL, {FOOD}, 'pending', 'c', NULL)")
        assert one(conn, "SELECT COUNT(*) FROM daily_tasks") == 4


def test_insert_or_ignore_makes_repeated_generation_a_noop(db_path):
    with connect(db_path) as conn:
        conn.execute(TASK.replace("INSERT", "INSERT OR IGNORE") + T1)
        conn.execute(TASK.replace("INSERT", "INSERT OR IGNORE") + T1)
        assert one(conn, "SELECT COUNT(*) FROM daily_tasks") == 1


def test_done_and_skipped_status_rules(db_path):
    with connect(db_path) as conn:
        conn.execute(TASK + T1.replace("'pending', '2026-09-30 08:00:00', NULL", "'done', '2026-09-30 08:00:00', '2026-09-30 09:00:00'"))
        conn.execute(TASK + f"({DEMO}, {HI}, '2026-09-30', 2, 'practice_situation', 'next_situation', NULL, {SIT}, NULL, 'skipped', 'c', NULL)")
        assert one(conn, "SELECT COUNT(*) FROM daily_tasks") == 2


def test_task_cascades_with_content_and_user(db_path):
    with connect(db_path) as conn:
        conn.execute(TASK + T1)
        conn.execute("DELETE FROM lessons WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')")
        assert one(conn, "SELECT COUNT(*) FROM daily_tasks") == 0
        conn.execute(TASK + f"({DEMO}, {HI}, '2026-09-30', 1, 'confidence_checkin', 'confidence_checkin', NULL, NULL, {FOOD}, 'pending', 'c', NULL)")
        conn.execute("DELETE FROM users WHERE handle='demo-alex'")
        assert one(conn, "SELECT COUNT(*) FROM daily_tasks") == 0


# ---------- views ----------
def test_learner_attempts_view_unifies_both_attempt_tables(db_path):
    with connect(db_path) as conn:
        u = one(conn, "SELECT id FROM users WHERE handle='demo-alex'")
        ex = conn.execute("SELECT id, item_id, difficulty FROM exercises WHERE kind='translation' LIMIT 1").fetchone()
        learn = one(conn, "SELECT st.id FROM situation_steps st WHERE st.kind='learn_phrase' LIMIT 1")
        choose = conn.execute("SELECT id, situation_id FROM situation_steps WHERE kind='choose_response' LIMIT 1").fetchone()
        conn.execute("INSERT INTO exercise_attempts(user_id, exercise_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, 'x', 0, ?)", (u, ex["id"], ts(1)))
        conn.execute("INSERT INTO situation_step_attempts(user_id, step_id, is_correct, attempted_at) VALUES (?, ?, 1, ?)", (u, learn, ts(2)))   # acknowledgement
        conn.execute("INSERT INTO situation_step_attempts(user_id, step_id, is_correct, attempted_at) VALUES (?, ?, 0, ?)", (u, choose["id"], ts(3)))
        rows = [dict(r) for r in conn.execute("SELECT source, task_id, kind, item_id, difficulty, is_correct FROM learner_attempts ORDER BY attempted_at")]
    assert rows == [
        {"source": "lesson", "task_id": ex["id"], "kind": "translation", "item_id": ex["item_id"], "difficulty": 3, "is_correct": 0},
        {"source": "situation", "task_id": choose["id"], "kind": "choose_response", "item_id": None, "difficulty": None, "is_correct": 0},
    ]   # the learn_phrase acknowledgement is not evidence of skill


def test_learner_attempt_topics_attributes_to_every_topic_of_a_lesson(db_path):
    with connect(db_path) as conn:
        u = one(conn, "SELECT id FROM users WHERE handle='demo-alex'")
        ex = one(conn, "SELECT e.id FROM exercises e JOIN lessons l ON l.id=e.lesson_id WHERE l.slug='food' AND l.language_id = (SELECT id FROM languages WHERE code='hi') LIMIT 1")
        conn.execute("INSERT INTO lesson_topics(lesson_id, topic_id) SELECT l.id, t.id FROM lessons l, topics t WHERE l.slug='food' AND l.language_id = (SELECT id FROM languages WHERE code='hi') AND t.slug='shopping'")
        conn.execute("INSERT INTO exercise_attempts(user_id, exercise_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, 'x', 1, ?)", (u, ex, ts(1)))
        st = one(conn, "SELECT st.id FROM situation_steps st JOIN situations s ON s.id=st.situation_id WHERE s.slug='transport' AND s.language_id = (SELECT id FROM languages WHERE code='hi') AND st.kind='conversation'")
        conn.execute("INSERT INTO situation_step_attempts(user_id, step_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, 'y', 0, ?)", (u, st, ts(2)))
        topics = sorted(r[0] for r in conn.execute("SELECT t.slug FROM learner_attempt_topics v JOIN topics t ON t.id=v.topic_id"))
        assert topics == ["food", "shopping", "transport"]            # the lesson counts for both its topics; the situation for its one
        assert one(conn, "SELECT COUNT(*) FROM learner_attempts") == 2  # ...but it is still one attempt in the per-attempt view


def test_expected_indexes_exist(db_path):
    with connect(db_path) as conn:
        names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"idx_confidence_user_topic", "idx_confidence_user_skill", "uq_weakness_topic", "uq_weakness_item", "idx_weaknesses_user_status", "uq_daily_task_target"} <= names

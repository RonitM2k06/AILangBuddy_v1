"""Helpers for personalization tests: seed synthetic attempts with controlled timestamps, straight into the tables
the real services write (so the rules are exercised on the same data shape)."""
from datetime import datetime, timedelta

from backend import main
from backend.db import connect

BASE = datetime(2026, 9, 1, 9, 0, 0)


def ts(n):
    """Timestamp n minutes after a fixed base (monotonic, so 'recent' is unambiguous)."""
    return (BASE + timedelta(minutes=n)).strftime("%Y-%m-%d %H:%M:%S")


def db():
    return connect(main.DB_PATH)


def uid(email):
    with db() as conn:
        return conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]


def exercise_ids(slug, kind=None, language="hi"):
    """A seeded lesson's exercises. Slugs are unique per language (Hindi and Marathi both have a "food" lesson): Hindi unless asked."""
    with db() as conn:
        sql = ("SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = ? AND l.language_id = (SELECT id FROM languages WHERE code = ?)"
               + (" AND e.kind = ?" if kind else "") + " ORDER BY e.sort_order")
        return [r[0] for r in conn.execute(sql, (slug, language, kind) if kind else (slug, language))]


def step_ids(slug, kind=None, language="hi"):
    """A seeded situation's steps. Slugs are unique per language (Hindi and Marathi share them): Hindi unless asked."""
    with db() as conn:
        sql = ("SELECT st.id FROM situation_steps st JOIN situations s ON s.id = st.situation_id WHERE s.slug = ? AND s.language_id = (SELECT id FROM languages WHERE code = ?)"
               + (" AND st.kind = ?" if kind else "") + " ORDER BY st.sort_order")
        return [r[0] for r in conn.execute(sql, (slug, language, kind) if kind else (slug, language))]


def add_exercise_attempts(user_id, exercise_id, results, start=0):
    """results: iterable of 0/1 (or bool); attempt i is stamped ts(start + i). Returns the next free minute."""
    with db() as conn:
        for i, ok in enumerate(results):
            conn.execute("INSERT INTO exercise_attempts(user_id, exercise_id, answer_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, NULL, 'x', ?, ?)",
                         (user_id, exercise_id, 1 if ok else 0, ts(start + i)))
    return start + len(list(results))


def add_step_attempts(user_id, step_id, results, start=0):
    with db() as conn:
        for i, ok in enumerate(results):
            conn.execute("INSERT INTO situation_step_attempts(user_id, step_id, answer_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, NULL, 'x', ?, ?)",
                         (user_id, step_id, 1 if ok else 0, ts(start + i)))
    return start + len(list(results))


def cycle_attempts(user_id, slug, results, start=0):
    """Spread results over the lesson's exercises round-robin (so several exercises/items are involved)."""
    ids = exercise_ids(slug)
    with db() as conn:
        for i, ok in enumerate(results):
            conn.execute("INSERT INTO exercise_attempts(user_id, exercise_id, answer_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, NULL, 'x', ?, ?)",
                         (user_id, ids[i % len(ids)], 1 if ok else 0, ts(start + i)))
    return start + len(results)


def complete_lesson(client, slug):
    """Finish every exercise of a lesson through the real API (answer keys read from the database)."""
    lesson = next(l for l in client.get("/api/lessons").json()["lessons"] if l["slug"] == slug)
    for ex in client.get(f"/api/lessons/{lesson['id']}").json()["lesson"]["exercises"]:
        with db() as conn:
            key = conn.execute("SELECT id, answer_text FROM exercise_answers WHERE exercise_id=? AND is_correct=1 ORDER BY sort_order", (ex["id"],)).fetchone()
        body = {"answer_id": key["id"]} if ex["kind"] == "multiple_choice" else {"text": key["answer_text"]}
        assert client.post(f"/api/exercises/{ex['id']}/attempts", json=body).json()["correct"]
    return lesson["id"]


def complete_situation(client, slug):
    sit = next(s for s in client.get("/api/situations").json()["situations"] if s["slug"] == slug)
    for step in client.get(f"/api/situations/{sit['id']}").json()["situation"]["steps"]:
        with db() as conn:
            key = conn.execute("SELECT id, answer_text FROM situation_step_answers WHERE step_id=? AND is_correct=1 ORDER BY sort_order", (step["id"],)).fetchone()
        body = {} if step["kind"] == "learn_phrase" else {"answer_id": key["id"]} if step["kind"] == "choose_response" else {"text": key["answer_text"]}
        assert client.post(f"/api/situations/{sit['id']}/steps/{step['id']}/responses", json=body).json()["correct"]
    return sit["id"]

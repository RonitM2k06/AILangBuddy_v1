"""Helpers for Phase 8 tests. DOBs are computed from the real date so a learner is the intended age whenever the suite runs."""
from datetime import date, timedelta

from backend import main
from backend.db import connect
from backend.personalization import clock

from .conftest import register


def dob_for_age(years, extra_days=30):
    t = date.today()
    try:
        d = t.replace(year=t.year - years)
    except ValueError:
        d = t.replace(year=t.year - years, day=28)
    return (d - timedelta(days=extra_days)).isoformat()


def profile(age, cefr="A1"):
    return {"native_language": "en", "target_language": "hi", "cefr_level": cefr, "date_of_birth": dob_for_age(age)}


def make_learner(client, email, age, cefr="A1"):
    register(client, email)
    assert client.put("/api/profile", json=profile(age, cefr)).status_code == 200
    return client


def db():
    return connect(main.DB_PATH)


def uid(email):
    with db() as conn:
        return conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]


def answer_key(path=None):
    """{level_number: [(question_number, correct_choice, wrong_choice)]} read from the database (never from an API response),
    in the same order the adventure uses: the child's activities grouped by topic."""
    with (connect(path) if path else db()) as conn:
        rows = conn.execute(
            """SELECT a.id, t.slug FROM listening_activities a JOIN topics t ON t.id = a.topic_id JOIN cefr_levels c ON c.code = a.cefr_code
               WHERE a.status = 'published' AND a.language_id = (SELECT id FROM languages WHERE code='hi') AND c.rank <= 1
                 AND (NOT EXISTS (SELECT 1 FROM listening_activity_age_groups x WHERE x.activity_id = a.id)
                      OR a.id IN (SELECT activity_id FROM listening_activity_age_groups WHERE age_group_id = (SELECT id FROM age_groups WHERE code='child')))
               ORDER BY c.rank, a.sort_order""").fetchall()
        levels = {}
        for r in rows:
            levels.setdefault(r["slug"], []).append(r["id"])
        out = {}
        for n, ids in enumerate(levels.values(), start=1):
            qs = []
            for k, aid in enumerate(ids, start=1):
                opts = conn.execute("SELECT o.id, o.item_id = a.item_id AS ok FROM listening_options o JOIN listening_activities a ON a.id = o.activity_id "
                                    "WHERE a.id = ? ORDER BY o.sort_order", (aid,)).fetchall()
                right = next(j for j, o in enumerate(opts, start=1) if o["ok"])
                wrong = next(j for j, o in enumerate(opts, start=1) if not o["ok"])
                qs.append((k, right, wrong))
            out[n] = qs
    return out


def play(client, level, question, choice):
    return client.post(f"/api/kids/levels/{level}/answers", json={"question": question, "choice": choice})


def clear_level(client, level, key=None):
    key = key or answer_key()
    for q, right, _ in key[level]:
        assert play(client, level, q, right).status_code == 200


def freeze_clock(monkeypatch, start="2026-09-01 09:00:00"):
    """Returns a function to move the clock: tick(seconds)."""
    from datetime import datetime, timedelta
    state = {"t": datetime.strptime(start, "%Y-%m-%d %H:%M:%S")}
    monkeypatch.setattr(clock, "now", lambda: state["t"].strftime("%Y-%m-%d %H:%M:%S"))
    monkeypatch.setattr(clock, "today", lambda: state["t"].strftime("%Y-%m-%d"))

    def tick(seconds):
        state["t"] += timedelta(seconds=seconds)
    return tick

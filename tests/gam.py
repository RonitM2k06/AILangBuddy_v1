"""Helpers for Phase 10 tests."""
from backend import main
from backend.db import connect

from .lis import activities, answer, correct_option, wrong_options


def db():
    return connect(main.DB_PATH)


def uid(email):
    with db() as conn:
        return conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]


def summary(c):
    r = c.get("/api/gamification")
    assert r.status_code == 200, r.text
    return r.json()


def total_xp(c):
    return summary(c)["xp"]["total"]


def listen_right(c, n=1, skip=0):
    """n correct answers to distinct listening activities (each worth 5 XP once). Returns how many were answered."""
    done = 0
    for a in activities(c)[skip:skip + n]:
        assert answer(c, a["id"], correct_option(a["id"])).status_code == 200
        done += 1
    return done


def listen_wrong(c, n=1):
    for a in activities(c)[:n]:
        answer(c, a["id"], wrong_options(a["id"])[0])


def events(user_id):
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT kind, source_id, xp, day, earned_at FROM xp_events WHERE user_id = ? ORDER BY id", (user_id,))]


def seed_event(user_id, kind, source_id, xp, day, earned_at=None):
    with db() as conn:
        conn.execute("INSERT INTO xp_events(user_id, kind, source_id, xp, earned_at, day, created_at) VALUES (?, ?, ?, ?, ?, ?, 't')",
                     (user_id, kind, source_id, xp, earned_at or day + " 12:00:00", day))

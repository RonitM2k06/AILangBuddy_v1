"""The life rules (pure), the schema bounds and the repository guards."""
import re
import sqlite3
from datetime import datetime, timedelta

import pytest

from backend import settings
from backend.db import connect
from backend.kids import lives
from backend.repositories import kids as repo

T0 = datetime(2026, 9, 1, 9, 0, 0)


def eff(n, secs):
    return lives.effective(n, T0, T0 + timedelta(seconds=secs))


def test_constants():
    assert settings.MAX_LIVES == 5 and settings.LIFE_REGEN_SECONDS == 600


def test_max_lives_matches_schema_check(db_path):
    with connect(db_path) as conn:
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='child_game_state'").fetchone()[0]
    assert f"BETWEEN 0 AND {settings.MAX_LIVES}" in sql


def test_full_lives_stay_full():
    assert eff(5, 0) == (5, T0, None)
    assert eff(5, 99999)[0] == 5


def test_no_regeneration_before_interval():
    n, anchor, wait = eff(2, 599)
    assert (n, anchor, wait) == (2, T0, 1)


def test_one_life_per_interval():
    assert eff(2, 600)[0] == 3 and eff(2, 1199)[0] == 3 and eff(2, 1200)[0] == 4


def test_remainder_is_preserved():
    n, anchor, wait = eff(0, 1000)         # one life gained, 400 s into the next interval
    assert n == 1 and anchor == T0 + timedelta(seconds=600) and wait == 200


def test_caps_at_max_and_resets_anchor():
    n, anchor, wait = eff(3, 10 ** 7)
    assert (n, wait) == (5, None) and anchor == T0 + timedelta(seconds=10 ** 7)


def test_clock_going_backwards_gives_no_lives():
    assert eff(1, -5000)[0] == 1


@pytest.mark.parametrize("bad,expected", [(-3, 0), (99, 5)])
def test_out_of_range_input_is_clamped(bad, expected):
    assert lives.effective(bad, T0, T0)[0] == expected


def test_repeated_checks_do_not_change_regeneration():
    n, anchor, _ = eff(0, 700)
    again = lives.effective(n, anchor, T0 + timedelta(seconds=1300))
    direct = eff(0, 1300)
    assert again[0] == direct[0] and again[1] == direct[1]


# ---------- database bounds ----------
def add_user(conn, email):
    cols = {r[1]: r for r in conn.execute("PRAGMA table_info(users)")}
    values = {"email": email, "display_name": "K", "password_hash": "x", "handle": email}
    names = [c for c in cols if c in values]
    return conn.execute(f"INSERT INTO users({','.join(names)}) VALUES ({','.join('?' * len(names))})", [values[n] for n in names]).lastrowid


@pytest.mark.parametrize("n", [-1, 6, 100])
def test_lives_out_of_range_refused_by_database(db_path, n):
    with connect(db_path) as conn:
        u = add_user(conn, "a@example.com")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO child_game_state VALUES (?, ?, 't', 't')", (u, n))


def test_lose_life_is_guarded_at_zero(db_path):
    with connect(db_path) as conn:
        u = add_user(conn, "a@example.com")
        repo.create_state(conn, u, 1, "2026-09-01 09:00:00")
        assert repo.lose_life(conn, u, "2026-09-01 09:00:00", 5) == 0
        assert repo.lose_life(conn, u, "2026-09-01 09:00:00", 5) is None      # nothing to take: no negative lives
        assert repo.get_state(conn, u)["lives"] == 0


def test_lose_life_keeps_anchor_unless_full(db_path):
    with connect(db_path) as conn:
        u = add_user(conn, "a@example.com")
        repo.create_state(conn, u, 5, "2026-09-01 09:00:00")
        repo.lose_life(conn, u, "2026-09-01 10:00:00", 5)                     # from full: regeneration starts now
        assert repo.get_state(conn, u) == {"lives": 4, "lives_updated_at": "2026-09-01 10:00:00"}
        repo.lose_life(conn, u, "2026-09-01 10:05:00", 5)                     # already regenerating: anchor untouched
        assert repo.get_state(conn, u) == {"lives": 3, "lives_updated_at": "2026-09-01 10:00:00"}


def test_state_is_created_once(db_path):
    with connect(db_path) as conn:
        u = add_user(conn, "a@example.com")
        repo.create_state(conn, u, 5, "t")
        repo.create_state(conn, u, 2, "t2")
        assert repo.get_state(conn, u)["lives"] == 5


def _attempt(conn, user, correct):
    hi = conn.execute("SELECT id FROM languages WHERE code='hi'").fetchone()[0]
    act = conn.execute("SELECT id FROM listening_activities LIMIT 1").fetchone()[0]
    opt = conn.execute("SELECT id FROM listening_options WHERE activity_id=?", (act,)).fetchone()[0]
    sid = conn.execute("INSERT INTO audio_sessions(user_id, language_id, kind, status, started_at, ended_at, duration_ms) VALUES (?, ?, 'listening', 'completed', 't', 't', 1)", (user, hi)).lastrowid
    return conn.execute("INSERT INTO listening_attempts(user_id, session_id, activity_id, option_id, is_correct, plays, attempted_at) VALUES (?, ?, ?, ?, ?, 0, 't')",
                        (user, sid, act, opt, correct)).lastrowid


def test_life_loss_needs_a_wrong_attempt_of_the_same_learner_once(db_path):
    with connect(db_path) as conn:
        a, b = add_user(conn, "a@example.com"), add_user(conn, "b@example.com")
        repo.create_state(conn, a, 5, "t")
        repo.create_state(conn, b, 5, "t")
        wrong, right, others = _attempt(conn, a, 0), _attempt(conn, a, 1), _attempt(conn, b, 0)
        with pytest.raises(sqlite3.IntegrityError):
            repo.record_loss(conn, a, right, 4, "t")             # a correct answer cannot cost a life
        with pytest.raises(sqlite3.IntegrityError):
            repo.record_loss(conn, a, others, 4, "t")            # nor can someone else's answer
        with pytest.raises(sqlite3.IntegrityError):
            repo.record_loss(conn, a, 99999, 4, "t")             # nor a missing one
        repo.record_loss(conn, a, wrong, 4, "t")
        with pytest.raises(sqlite3.IntegrityError):
            repo.record_loss(conn, a, wrong, 3, "t")             # one attempt, one life at most
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO child_life_losses(user_id, attempt_id, attempt_correct, lives_after, lost_at) VALUES (?, ?, 1, 0, 't')", (b, others))
        with pytest.raises(sqlite3.IntegrityError):               # even a row that truthfully says "this attempt was correct"
            conn.execute("INSERT INTO child_life_losses(user_id, attempt_id, attempt_correct, lives_after, lost_at) VALUES (?, ?, 1, 0, 't')", (a, right))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO child_life_losses(user_id, attempt_id, attempt_correct, lives_after, lost_at) VALUES (?, ?, 0, 5, 't')", (b, others))


def test_losses_cascade_with_the_learner(db_path):
    with connect(db_path) as conn:
        a = add_user(conn, "a@example.com")
        repo.create_state(conn, a, 5, "t")
        repo.record_loss(conn, a, _attempt(conn, a, 0), 4, "t")
        conn.execute("DELETE FROM listening_attempts WHERE user_id = ?", (a,))
        assert repo.losses(conn, a) == []


def test_repository_queries_are_scoped_by_user(db_path):
    with connect(db_path) as conn:
        a, b = add_user(conn, "a@example.com"), add_user(conn, "b@example.com")
        repo.create_state(conn, a, 3, "t")
        assert repo.get_state(conn, b) is None
        repo.record_loss(conn, a, _attempt(conn, a, 0), 2, "t")
        assert repo.losses(conn, b) == [] and len(repo.losses(conn, a)) == 1

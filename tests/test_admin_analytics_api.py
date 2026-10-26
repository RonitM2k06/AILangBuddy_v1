"""Phase 13F: every analytics metric, against fixtures whose expected figures are worked out by hand here (never by calling the code under test)."""
from datetime import datetime, timezone

import pytest

from backend import main
from backend.admin import analytics
from backend.db import connect
from backend.repositories import sessions as session_repo

from . import adm
from .adm import Api, admin, demo_browser, learners, ok, register_browser  # noqa: F401

A = "/api/admin/analytics"
TODAY = "2026-03-15"


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    """The whole module runs at 2026-03-15 12:00 UTC: '30d' is 2026-02-14..2026-03-15 and '7d' is 2026-03-09..2026-03-15."""
    monkeypatch.setattr(analytics, "utcnow", lambda: datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc))


def get(api, url, status=200):
    r = api.get(url)
    assert r.status_code == status, r.text
    return r.json()


def exercise_ids(conn, slug="food"):
    return [r[0] for r in conn.execute("SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = ? AND l.language_id = 10 ORDER BY e.sort_order", (slug,))]   # Hindi's (slugs repeat across languages)


def attempt(conn, uid, at, correct=1, slug="food"):
    adm.exercise_attempt(conn, uid, exercise_ids(conn, slug)[0], correct=correct, at=at)


def ok_count(v):
    return (v["value"], v["status"])


# =====================================================================================================================
# learners
# =====================================================================================================================
def test_an_empty_system_reports_zeros_not_errors(admin):
    d = get(admin, "/api/admin/dashboard")
    assert ok_count(d["learners"]["total"]) == (0, "ok") and ok_count(d["learners"]["active"]) == (0, "ok") and d["learning"]["lesson_completion"]["status"] == "no_data"
    assert d["learning"]["exercise_accuracy"] == {"numerator": 0, "denominator": 0, "rate": None, "status": "no_data"}
    assert d["distributions"]["language"] == {"total": {"value": 0, "status": "ok"}, "buckets": []}
    assert d["window"] == {"from": "2026-02-14", "to": "2026-03-15", "days": 30} and d["timezone"] == "UTC" and d["window_name"] == "30d"


def test_total_learners_counts_learners_only(admin):
    with connect(main.DB_PATH) as conn:
        learners(conn, 6)
        learners(conn, 1, profile=False)
        adm.add_user(conn, "admin")
        adm.add_user(conn, "parent")
        both = adm.add_user(conn, "learner")
        conn.execute("INSERT INTO user_roles(user_id, role_id) SELECT ?, id FROM roles WHERE name = 'admin'", (both,))      # an admin who also holds the learner role is staff
        attempt(conn, both, "2026-03-15 10:00:00")
    d = get(admin, "/api/admin/dashboard")
    assert ok_count(d["learners"]["total"]) == (7, "ok")                       # 6 + the one without a profile; not the admins, the parent, or the demo account
    assert ok_count(d["learners"]["active"]) == (0, "ok")


def test_a_handful_of_learners_is_suppressed_not_reported(admin):
    with connect(main.DB_PATH) as conn:
        learners(conn, 4)
    d = get(admin, "/api/admin/dashboard")
    assert d["learners"]["total"] == {"value": None, "status": "suppressed"}
    with connect(main.DB_PATH) as conn:
        learners(conn, 1)
    assert get(admin, "/api/admin/dashboard")["learners"]["total"] == {"value": 5, "status": "ok"}


def test_new_learners_use_the_window_boundaries_at_midnight_utc(admin):
    with connect(main.DB_PATH) as conn:
        learners(conn, 5, created="2026-02-14 00:00:00")       # first second of the 30d window: in
        learners(conn, 5, created="2026-02-13 23:59:59")       # one second earlier: out
        learners(conn, 5, created="2026-03-15 23:59:59")       # last second of today: in
        learners(conn, 5, created="2026-03-16 00:00:00")       # first second of tomorrow: out
    assert ok_count(get(admin, "/api/admin/dashboard?window=30d")["learners"]["new"]) == (10, "ok")
    assert ok_count(get(admin, "/api/admin/dashboard?window=7d")["learners"]["new"]) == (5, "ok")
    d90 = get(admin, "/api/admin/dashboard?window=90d")
    assert ok_count(d90["learners"]["new"]) == (15, "ok")                       # everything except the group created tomorrow
    assert ok_count(d90["learners"]["total"]) == (20, "ok")


def test_new_learners_exclude_the_demo_account_and_staff(admin):
    with connect(main.DB_PATH) as conn:
        learners(conn, 5, created="2026-03-10 00:00:00")
        conn.execute("UPDATE users SET created_at = '2026-03-10 00:00:00' WHERE handle = 'demo-alex'")
        a = adm.add_user(conn, "admin")
        conn.execute("UPDATE users SET created_at = '2026-03-10 00:00:00' WHERE id = ?", (a,))
    assert ok_count(get(admin, "/api/admin/dashboard")["learners"]["new"]) == (5, "ok")


# =====================================================================================================================
# activity: DAU / WAU / MAU
# =====================================================================================================================
def activity_world(conn):
    a, b, c, dd = learners(conn, 6), learners(conn, 2), learners(conn, 5), learners(conn, 5)
    for u in a:
        attempt(conn, u, "2026-03-15 08:00:00")
    for u in a[:3] + b:
        attempt(conn, u, "2026-03-14 09:00:00")
    for u in c:
        attempt(conn, u, "2026-03-10 10:00:00", correct=0)
    for u in dd:
        attempt(conn, u, "2026-02-20 10:00:00")
    return a, b, c, dd


def test_dau_wau_mau_active_as_of_today(admin):
    with connect(main.DB_PATH) as conn:
        activity_world(conn)
    d = get(admin, "/api/admin/dashboard")
    assert d["activity"]["as_of"] == TODAY
    assert [ok_count(d["activity"][k]) for k in ("dau", "wau", "mau")] == [(6, "ok"), (13, "ok"), (18, "ok")]
    assert ok_count(d["learners"]["active"]) == (18, "ok")
    d7 = get(admin, "/api/admin/dashboard?window=7d")
    assert ok_count(d7["learners"]["active"]) == (13, "ok") and ok_count(d7["activity"]["mau"]) == (18, "ok")          # MAU looks back 30 days whatever the window


def test_the_daily_series_has_a_point_per_day_with_trailing_windows(admin):
    with connect(main.DB_PATH) as conn:
        activity_world(conn)
    s = get(admin, f"{A}/activity?from=2026-03-09&to=2026-03-15")
    assert s["grain"] == "day" and [p["date"] for p in s["points"]] == [f"2026-03-{d:02d}" for d in range(9, 16)]
    by = {p["date"]: p for p in s["points"]}
    assert [ok_count(by[d]["dau"]) for d in ("2026-03-09", "2026-03-10", "2026-03-11", "2026-03-13", "2026-03-14", "2026-03-15")] == [(0, "ok"), (5, "ok"), (0, "ok"), (0, "ok"), (5, "ok"), (6, "ok")]
    assert ok_count(by["2026-03-10"]["wau"]) == (5, "ok") and ok_count(by["2026-03-14"]["wau"]) == (10, "ok") and ok_count(by["2026-03-15"]["wau"]) == (13, "ok")
    assert ok_count(by["2026-03-15"]["mau"]) == (18, "ok") and ok_count(by["2026-03-10"]["mau"]) == (10, "ok")                    # 03-10's month holds only the 03-10 and 02-20 groups
    assert all(p["active_learners"] is None for p in s["points"])


def test_the_weekly_series_buckets_from_the_start_date(admin):
    with connect(main.DB_PATH) as conn:
        activity_world(conn)
    s = get(admin, f"{A}/activity?from=2026-02-14&to=2026-03-15&grain=week")
    assert [(p["date"], p["days"], ok_count(p["active_learners"])) for p in s["points"]] == [
        ("2026-02-14", 7, (5, "ok")), ("2026-02-21", 7, (0, "ok")), ("2026-02-28", 7, (0, "ok")), ("2026-03-07", 7, (5, "ok")), ("2026-03-14", 2, (8, "ok"))]
    assert all(p["dau"] is None for p in s["points"])


def test_small_daily_counts_are_suppressed_in_the_series(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 3):
            attempt(conn, u, "2026-03-15 08:00:00")
        for u in learners(conn, 5):
            attempt(conn, u, "2026-03-14 08:00:00")
    s = get(admin, f"{A}/activity?window=7d")
    by = {p["date"]: p for p in s["points"]}
    assert by["2026-03-15"]["dau"] == {"value": None, "status": "suppressed"} and ok_count(by["2026-03-14"]["dau"]) == (5, "ok") and ok_count(by["2026-03-13"]["dau"]) == (0, "ok")
    assert ok_count(by["2026-03-15"]["wau"]) == (8, "ok")


def test_every_kind_of_learning_evidence_makes_a_learner_active(admin):
    """Eight kinds of evidence, five different learners each: all forty are active, and the response says which evidence kinds were present."""
    with connect(main.DB_PATH) as conn:
        at = "2026-03-12 10:00:00"
        for u in learners(conn, 5):
            attempt(conn, u, at)
        for u in learners(conn, 5):
            adm.step_attempt(conn, u, adm.first_step(conn, adm.situation_id(conn)), at=at)
        for u in learners(conn, 5):
            aid = adm.activity_id(conn)
            adm.listening_attempt(conn, u, aid, adm.wrong_option(conn, aid), at=at)
        for u in learners(conn, 5):
            adm.speaking_attempt(conn, u, at)
        for u in learners(conn, 5):
            adm.pronunciation(conn, u, at)
        for u in learners(conn, 5):
            sid = adm.situation_id(conn)
            adm.roleplay_turn(conn, u, adm.roleplay_session(conn, u, sid, at=at), sid, adm.first_step(conn, sid), at=at)
        for u in learners(conn, 5):
            adm.micro_lesson(conn, u, at, attempts=[(at, True)])
        for n, u in enumerate(learners(conn, 5)):
            adm.xp(conn, u, 900 + n, earned=at)
    s = get(admin, f"{A}/activity?window=7d")
    assert s["evidence_kinds"] == sorted(["exercise_attempts", "situation_step_attempts", "listening_attempts", "speaking_sessions", "pronunciation_assessments", "roleplay_turns",
                                          "ai_micro_lesson_attempts", "xp_events"])
    assert ok_count(get(admin, "/api/admin/dashboard")["learners"]["active"]) == (40, "ok")


@pytest.mark.parametrize("kind", ["exercise", "step", "listening", "speaking", "pronunciation", "roleplay", "micro", "xp"])
def test_each_evidence_kind_on_its_own_counts_five_active_learners(admin, kind):
    at = "2026-03-12 10:00:00"
    with connect(main.DB_PATH) as conn:
        for n, u in enumerate(learners(conn, 5)):
            sid = adm.situation_id(conn)
            if kind == "exercise":
                attempt(conn, u, at)
            elif kind == "step":
                adm.step_attempt(conn, u, adm.first_step(conn, sid), at=at)
            elif kind == "listening":
                aid = adm.activity_id(conn)
                adm.listening_attempt(conn, u, aid, adm.wrong_option(conn, aid), at=at)
            elif kind == "speaking":
                adm.speaking_attempt(conn, u, at)
            elif kind == "pronunciation":
                adm.pronunciation(conn, u, at, status="failed" if n % 2 else "completed")
            elif kind == "roleplay":
                adm.roleplay_turn(conn, u, adm.roleplay_session(conn, u, sid, at=at), sid, adm.first_step(conn, sid), at=at)
            elif kind == "micro":
                adm.micro_lesson(conn, u, at, attempts=[(at, False)])
            else:
                adm.xp(conn, u, 700 + n, earned=at)
    d = get(admin, "/api/admin/dashboard")
    assert ok_count(d["learners"]["active"]) == (5, "ok") and ok_count(d["activity"]["wau"]) == (5, "ok")


def test_logins_are_not_learning_activity(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 8):
            session_repo.create(conn, u, f"hash-{u}", "2026-03-15 09:00:00", "2099-01-01 00:00:00")
    d = get(admin, "/api/admin/dashboard")
    assert ok_count(d["learners"]["active"]) == (0, "ok") and ok_count(d["activity"]["dau"]) == (0, "ok")


def test_a_speaking_session_with_nothing_recorded_is_not_an_attempt(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 5):
            adm.speaking_attempt(conn, u, "2026-03-12 10:00:00", stage="created")
        for u in learners(conn, 5):
            adm.speaking_attempt(conn, u, "2026-03-12 10:00:00", stage="cancelled")
    assert ok_count(get(admin, "/api/admin/dashboard")["learners"]["active"]) == (0, "ok")


def test_the_demo_account_and_staff_never_count_as_active(admin):
    with connect(main.DB_PATH) as conn:
        demo = conn.execute("SELECT id FROM users WHERE handle = 'demo-alex'").fetchone()[0]
        parent, staff = adm.add_user(conn, "parent"), adm.add_user(conn, "admin")
        for u in [demo, parent, staff]:
            attempt(conn, u, "2026-03-15 08:00:00")
            adm.xp(conn, u, 300 + u, earned="2026-03-15 08:00:00")
        for u in learners(conn, 5):
            attempt(conn, u, "2026-03-15 08:00:00")
    d = get(admin, "/api/admin/dashboard")
    assert ok_count(d["learners"]["active"]) == (5, "ok") and ok_count(d["activity"]["dau"]) == (5, "ok")


@pytest.mark.parametrize("at,counted_in_30d", [("2026-02-14 00:00:00", True), ("2026-02-13 23:59:59", False), ("2026-03-15 23:59:59", True), ("2026-03-16 00:00:00", False),
                                               ("2026-03-15 00:00:00", True), ("2026-02-14 23:59:59", True)])
def test_activity_windows_include_the_first_second_and_exclude_the_next_midnight(admin, at, counted_in_30d):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 5):
            attempt(conn, u, at)
    assert ok_count(get(admin, "/api/admin/dashboard")["learners"]["active"]) == ((5 if counted_in_30d else 0), "ok")


def test_the_activity_window_uses_the_utc_date_not_a_local_one(admin):
    """23:30 UTC on the 14th is the 14th, whatever offset a browser has."""
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 5):
            attempt(conn, u, "2026-03-14 23:30:00")
    s = get(admin, f"{A}/activity?from=2026-03-14&to=2026-03-15")
    assert [(p["date"], ok_count(p["dau"])) for p in s["points"]] == [("2026-03-14", (5, "ok")), ("2026-03-15", (0, "ok"))]


# =====================================================================================================================
# distributions
# =====================================================================================================================
def test_language_cefr_and_age_distributions_with_folding(admin):
    with connect(main.DB_PATH) as conn:
        learners(conn, 4, target="hi", level="A1", dob="1990-01-01")
        learners(conn, 2, target="hi", level="A2", dob="1990-01-01")
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (2, 'A1') ON CONFLICT DO NOTHING")
        learners(conn, 3, target="es", level="A1", dob="2012-06-01")
        learners(conn, 2, profile=False)
    d = get(admin, "/api/admin/dashboard")["distributions"]
    assert ok_count(d["language"]["total"]) == (11, "ok")
    assert [(b["key"], b["count"], b["status"]) for b in d["language"]["buckets"]] == [("hi", 6, "ok"), ("other", 5, "ok")]               # es (3) + none (2) folded
    assert ok_count(d["cefr"]["total"]) == (9, "ok")                                                                                       # the two without a profile have no level
    assert [(b["key"], b["count"], b["status"]) for b in d["cefr"]["buckets"]] == [("other", 9, "ok")]                                   # A2 (2) is too small, so A1 (7) joins it
    assert ok_count(d["age_group"]["total"]) == (9, "ok")
    assert [(b["key"], b["count"], b["status"]) for b in d["age_group"]["buckets"]] == [("other", 9, "ok")]                              # teen (3) is too small, so adult (6) joins it


def test_age_groups_are_bands_derived_from_the_date_of_birth_at_the_window_end(admin):
    with connect(main.DB_PATH) as conn:
        learners(conn, 5, dob="2016-03-15")      # turns 10 today: teen
        learners(conn, 5, dob="2016-03-16")      # turns 10 tomorrow: still 9, child
        learners(conn, 6, dob="2008-03-15")      # turns 18 today: adult
        learners(conn, 7, dob="2008-03-16")      # still 17: teen
    d = get(admin, "/api/admin/dashboard")["distributions"]["age_group"]
    assert [(b["key"], b["count"]) for b in d["buckets"]] == [("child", 5), ("teen", 12), ("adult", 6)] and ok_count(d["total"]) == (23, "ok")


def test_a_distribution_never_contains_a_date_of_birth_or_an_exact_age(admin):
    with connect(main.DB_PATH) as conn:
        learners(conn, 6, dob="2001-07-09")
    text = admin.get("/api/admin/dashboard").text
    assert "2001" not in text and "07-09" not in text and "date_of_birth" not in text and '"age"' not in text and '"dob"' not in text


def test_the_language_distribution_names_the_target_language_not_the_native_one(admin):
    with connect(main.DB_PATH) as conn:
        learners(conn, 6, target="hi")
    b = get(admin, "/api/admin/dashboard")["distributions"]["language"]["buckets"]
    assert [(x["key"], x["label"]) for x in b] == [("hi", "Hindi")] and all(x["key"] != "en" for x in b)


# =====================================================================================================================
# learning
# =====================================================================================================================
def test_lesson_completion_is_completed_over_started_in_the_window(admin):
    with connect(main.DB_PATH) as conn:
        lid = adm.lesson_id(conn)
        ls = learners(conn, 14)
        for u in ls[:10]:
            adm.lesson_progress(conn, u, lid, started="2026-03-01 09:00:00", completed="2026-03-02 09:00:00" if u in ls[:6] else None)
        adm.lesson_progress(conn, ls[10], lid, started="2026-02-13 23:59:59", completed="2026-03-01 00:00:00")       # started before the window: not in the cohort
        adm.lesson_progress(conn, ls[11], lid, started="2026-03-16 00:00:00")                                         # starts tomorrow: not in the cohort
        demo = conn.execute("SELECT id FROM users WHERE handle = 'demo-alex'").fetchone()[0]
        adm.lesson_progress(conn, demo, lid, started="2026-03-01 09:00:00", completed="2026-03-02 09:00:00")           # excluded
    r = get(admin, f"{A}/learning")["lesson_completion"]
    assert r == {"numerator": 6, "denominator": 10, "rate": 0.6, "status": "ok"}


def test_a_lesson_completion_rate_with_a_handful_of_completers_is_suppressed(admin):
    with connect(main.DB_PATH) as conn:
        lid = adm.lesson_id(conn)
        ls = learners(conn, 10)
        for i, u in enumerate(ls):
            adm.lesson_progress(conn, u, lid, started="2026-03-01 09:00:00", completed="2026-03-02 09:00:00" if i < 3 else None)
    assert get(admin, f"{A}/learning")["lesson_completion"] == {"numerator": None, "denominator": None, "rate": None, "status": "suppressed"}


def test_exercise_accuracy_counts_attempts_by_learners_in_the_window_only(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 7)
        for i in range(20):
            attempt(conn, ls[i % 7], "2026-03-05 10:00:00", correct=1 if i < 15 else 0)
        attempt(conn, ls[0], "2026-02-13 23:59:59", correct=0)                       # before the window
        attempt(conn, ls[0], "2026-03-16 00:00:00", correct=0)                       # after it
        aid = adm.activity_id(conn)
        adm.listening_attempt(conn, ls[1], aid, adm.wrong_option(conn, aid), at="2026-03-05 10:00:00")        # not an exercise
        demo = conn.execute("SELECT id FROM users WHERE handle = 'demo-alex'").fetchone()[0]
        attempt(conn, demo, "2026-03-05 10:00:00", correct=0)
    assert get(admin, f"{A}/learning")["exercise_accuracy"] == {"numerator": 15, "denominator": 20, "rate": 0.75, "status": "ok"}


def test_accuracy_over_four_learners_is_suppressed_whatever_the_attempt_count(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 4)
        for i in range(40):
            attempt(conn, ls[i % 4], "2026-03-05 10:00:00", correct=1)
    assert get(admin, f"{A}/learning")["exercise_accuracy"] == {"numerator": None, "denominator": None, "rate": None, "status": "suppressed"}
    with connect(main.DB_PATH) as conn:
        attempt(conn, learners(conn, 1)[0], "2026-03-05 10:00:00", correct=0)
    assert get(admin, f"{A}/learning")["exercise_accuracy"] == {"numerator": 40, "denominator": 41, "rate": 0.9756, "status": "ok"}


def test_situation_completion_and_the_numerator_rule(admin):
    with connect(main.DB_PATH) as conn:
        sid = adm.situation_id(conn)
        ls = learners(conn, 6)
        for i, u in enumerate(ls):
            adm.situation_progress(conn, u, sid, started="2026-03-03 09:00:00", completed="2026-03-04 09:00:00" if i < 5 else None)
    assert get(admin, f"{A}/learning")["situation_completion"] == {"numerator": 5, "denominator": 6, "rate": 0.8333, "status": "ok"}
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE situation_progress SET completed_at = NULL WHERE user_id IN (SELECT user_id FROM situation_progress ORDER BY user_id LIMIT 3)")
    assert get(admin, f"{A}/learning")["situation_completion"]["status"] == "suppressed"                 # only 2 learners completed


def test_listening_accuracy(admin):
    with connect(main.DB_PATH) as conn:
        aid = adm.activity_id(conn)
        ls = learners(conn, 6)
        for i in range(12):
            u = ls[i % 6]
            adm.listening_attempt(conn, u, aid, adm.right_option(conn, aid) if i < 9 else adm.wrong_option(conn, aid), correct=1 if i < 9 else 0, at="2026-03-07 10:00:00")
        attempt(conn, ls[0], "2026-03-07 10:00:00", correct=0)                                           # an exercise attempt is not a listening attempt
    assert get(admin, f"{A}/learning")["listening_accuracy"] == {"numerator": 9, "denominator": 12, "rate": 0.75, "status": "ok"}


def test_the_learning_block_follows_the_requested_window(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 6)
        for u in ls:
            attempt(conn, u, "2026-03-14 10:00:00", correct=1)
            attempt(conn, u, "2026-03-01 10:00:00", correct=0)
    assert get(admin, f"{A}/learning?window=7d")["exercise_accuracy"]["rate"] == 1.0
    assert get(admin, f"{A}/learning?window=30d")["exercise_accuracy"]["rate"] == 0.5
    assert get(admin, f"{A}/learning?from=2026-03-01&to=2026-03-01")["exercise_accuracy"]["rate"] == 0.0
    assert get(admin, f"{A}/learning?from=2026-03-02&to=2026-03-13")["exercise_accuracy"]["status"] == "no_data"


# =====================================================================================================================
# speaking, pronunciation, roleplay
# =====================================================================================================================
def test_speaking_participation_is_speakers_over_active_learners(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 6):
            adm.speaking_attempt(conn, u, "2026-03-10 10:00:00")
        for u in learners(conn, 4):
            attempt(conn, u, "2026-03-10 10:00:00")                       # active, but never spoke
        for u in learners(conn, 3):
            adm.speaking_attempt(conn, u, "2026-03-10 10:00:00", stage="cancelled")       # not an attempt, not activity
        for u in learners(conn, 5):
            adm.speaking_attempt(conn, u, "2026-02-01 10:00:00")          # spoke before the window
    assert get(admin, f"{A}/speaking")["speaking_participation"] == {"numerator": 6, "denominator": 10, "rate": 0.6, "status": "ok"}


def test_speaking_participation_is_suppressed_when_few_spoke_or_few_were_active(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 3):
            adm.speaking_attempt(conn, u, "2026-03-10 10:00:00")
        for u in learners(conn, 20):
            attempt(conn, u, "2026-03-10 10:00:00")
    assert get(admin, f"{A}/speaking")["speaking_participation"]["status"] == "suppressed"          # 3 speakers among 23 active learners
    with connect(main.DB_PATH) as conn:
        conn.execute("DELETE FROM exercise_attempts")
        conn.execute("DELETE FROM xp_events")
    assert get(admin, f"{A}/speaking")["speaking_participation"]["status"] == "suppressed"          # 3 active learners in all


def test_pronunciation_usage_counts_attempts_of_any_outcome(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 5):
            adm.pronunciation(conn, u, "2026-03-10 10:00:00")
            adm.pronunciation(conn, u, "2026-03-11 10:00:00", status="failed")
        adm.pronunciation(conn, learners(conn, 1)[0], "2026-01-01 10:00:00")                        # outside the window
    u = get(admin, f"{A}/speaking")["pronunciation_usage"]
    assert (ok_count(u["attempts"]), ok_count(u["learners"])) == ((10, "ok"), (5, "ok"))


def test_pronunciation_usage_is_suppressed_for_a_small_group_and_never_reports_a_score(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 4):
            for day in range(1, 6):
                adm.pronunciation(conn, u, f"2026-03-0{day} 10:00:00")
    r = admin.get(f"{A}/speaking")
    assert r.json()["pronunciation_usage"] == {"attempts": {"value": None, "status": "suppressed"}, "learners": {"value": None, "status": "suppressed"}}
    assert "score" not in r.text and "quality" not in r.text and "accuracy" not in r.json()["pronunciation_usage"]


def roleplay_world(conn, completed, clean, started_only=0):
    sid = adm.situation_id(conn)
    for i, u in enumerate(learners(conn, completed)):
        adm.roleplay_session(conn, u, sid, status="completed", correct=3 if i < clean else 2, missed=0 if i < clean else 1, at="2026-03-10 10:00:00")
    for u in learners(conn, started_only):
        adm.roleplay_session(conn, u, sid, status="active", at="2026-03-12 10:00:00")


def test_roleplay_success_is_clean_sessions_over_completed_sessions(admin):
    with connect(main.DB_PATH) as conn:
        roleplay_world(conn, completed=8, clean=6, started_only=2)
    r = get(admin, f"{A}/speaking")["roleplay"]
    assert (ok_count(r["started"]), ok_count(r["completed"])) == ((10, "ok"), (8, "ok"))
    assert r["success"] == {"numerator": 6, "denominator": 8, "rate": 0.75, "status": "ok"}


def test_roleplay_success_is_suppressed_when_few_sessions_were_clean(admin):
    with connect(main.DB_PATH) as conn:
        roleplay_world(conn, completed=8, clean=2)
    assert get(admin, f"{A}/speaking")["roleplay"]["success"]["status"] == "suppressed"
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE roleplay_sessions SET steps_correct = steps_total, steps_missed = 0")
    assert get(admin, f"{A}/speaking")["roleplay"]["success"] == {"numerator": 8, "denominator": 8, "rate": 1.0, "status": "ok"}


def test_roleplay_counts_use_the_window_and_never_read_turn_text(admin):
    with connect(main.DB_PATH) as conn:
        roleplay_world(conn, completed=6, clean=6)
        sid = adm.situation_id(conn)
        old = learners(conn, 5)
        for u in old:
            adm.roleplay_session(conn, u, sid, status="completed", correct=3, missed=0, at="2026-01-10 10:00:00")
        u = learners(conn, 1)[0]
        adm.roleplay_turn(conn, u, adm.roleplay_session(conn, u, sid, at="2026-03-12 10:00:00"), sid, adm.first_step(conn, sid), at="2026-03-12 10:00:00", text="CANARY roleplay words")
    r = admin.get(f"{A}/speaking")
    assert r.json()["roleplay"]["completed"] == {"value": 6, "status": "ok"} and "CANARY" not in r.text


# =====================================================================================================================
# confidence vs measured performance, and weaknesses
# =====================================================================================================================
def confidence_world(conn):
    ls = learners(conn, 8)
    ex = exercise_ids(conn)
    plan = [(90, [1, 1, 1, 1]), (80, [1, 1, 1, 0]), (70, [1, 1, 0, 0]), (60, [1, 1, 0, 0]), (50, [1, 0, 0, 0]), (40, [0, 0, 0, 0])]
    for u, (score, results) in zip(ls, plan):
        adm.self_report(conn, u, "food", score, "2026-03-01 10:00:00")
        for k, r in enumerate(results):
            adm.exercise_attempt(conn, u, ex[k % len(ex)], correct=r, at="2026-03-10 10:00:00")
    adm.self_report(conn, ls[6], "food", 99, "2026-03-01 10:00:00")                       # rated but did nothing in the window: not counted
    attempt(conn, ls[7], "2026-03-10 10:00:00")                                           # practised but never rated: not counted
    return ls


def food_row(r):
    return next(t for t in r["confidence_vs_performance"] if t["topic"]["slug"] == "food")


def test_confidence_versus_measured_accuracy_per_topic(admin):
    with connect(main.DB_PATH) as conn:
        confidence_world(conn)
    row = food_row(get(admin, f"{A}/confidence-weakness"))
    # confidence 90,80,70,60,50,40 -> 65.0; accuracy 100,75,50,50,25,0 -> 50.0 (per-learner accuracy, each learner once)
    assert row == {"topic": {"slug": "food", "name": "Food"}, "learners": 6, "mean_confidence": 65.0, "mean_accuracy": 50.0, "gap": 15.0, "status": "ok"}


def test_the_latest_self_report_before_the_window_ends_is_the_one_used(admin):
    with connect(main.DB_PATH) as conn:
        ls = confidence_world(conn)
        adm.self_report(conn, ls[0], "food", 10, "2026-02-01 10:00:00")                  # older than the 90: ignored
        adm.self_report(conn, ls[1], "food", 100, "2026-03-16 00:00:00")                 # after the window ends: ignored
        conn.execute("INSERT INTO confidence_scores(user_id, language_id, topic_id, score, source, recorded_at) "
                     "VALUES (?, 10, (SELECT id FROM topics WHERE slug = 'food'), 0, 'lesson', '2026-03-09 10:00:00')", (ls[2],))   # measured by the system, not self-reported: ignored
    assert food_row(get(admin, f"{A}/confidence-weakness"))["mean_confidence"] == 65.0
    with connect(main.DB_PATH) as conn:
        adm.self_report(conn, ls[0], "food", 100, "2026-03-05 10:00:00")                 # a newer self-report replaces the 90
    assert food_row(get(admin, f"{A}/confidence-weakness"))["mean_confidence"] == 66.7


def test_confidence_for_a_small_group_is_suppressed_and_hides_its_numbers(admin):
    with connect(main.DB_PATH) as conn:
        ex = exercise_ids(conn)
        for u in learners(conn, 4):
            adm.self_report(conn, u, "food", 80, "2026-03-01 10:00:00")
            adm.exercise_attempt(conn, u, ex[0], correct=0, at="2026-03-10 10:00:00")
    row = food_row(get(admin, f"{A}/confidence-weakness"))
    assert row == {"topic": {"slug": "food", "name": "Food"}, "learners": None, "mean_confidence": None, "mean_accuracy": None, "gap": None, "status": "suppressed"}


def test_confidence_ignores_the_demo_account_and_attempts_outside_the_window(admin):
    with connect(main.DB_PATH) as conn:
        confidence_world(conn)
        demo = conn.execute("SELECT id FROM users WHERE handle = 'demo-alex'").fetchone()[0]
        adm.self_report(conn, demo, "food", 0, "2026-03-01 10:00:00")
        adm.exercise_attempt(conn, demo, exercise_ids(conn)[0], correct=1, at="2026-03-10 10:00:00")
        ls = learners(conn, 6)
        for u in ls:
            adm.self_report(conn, u, "food", 10, "2026-03-01 10:00:00")
            adm.exercise_attempt(conn, u, exercise_ids(conn)[0], correct=1, at="2026-01-10 10:00:00")        # attempts long before the window
    assert food_row(get(admin, f"{A}/confidence-weakness"))["learners"] == 6


def test_a_topic_without_both_a_rating_and_practice_has_no_row(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 6):
            adm.self_report(conn, u, "transport", 50, "2026-03-01 10:00:00")
    assert get(admin, f"{A}/confidence-weakness")["confidence_vs_performance"] == []


def weakness_world(conn):
    food, greetings = learners(conn, 8), learners(conn, 6)
    for u in food:
        adm.weakness(conn, u, "food")
    for u in greetings:
        adm.weakness(conn, u, "greetings")
    x, y = learners(conn, 2)
    adm.weakness(conn, x, "transport")
    adm.weakness(conn, x, "shopping")             # one learner, two small topics
    adm.weakness(conn, y, "transport")
    resolved = learners(conn, 6)
    for u in resolved:
        adm.weakness(conn, u, "directions", status="resolved")                # resolved: not active
    adm.item_weakness(conn, learners(conn, 1)[0], adm.usable_items(conn, 1)[0])
    return food, greetings, x, y


def test_weakness_distribution_by_rule_and_by_topic_with_set_based_folding(admin):
    with connect(main.DB_PATH) as conn:
        weakness_world(conn)
    w = get(admin, f"{A}/confidence-weakness")["weaknesses"]
    assert w["as_of"] == "now"
    by_rule = {b["rule"]: b for b in w["by_rule"]}
    assert by_rule["low_topic_accuracy"] == {"rule": "low_topic_accuracy", "weaknesses": 8 + 6 + 3, "learners": 8 + 6 + 2, "status": "ok"}      # x counts once as a learner
    assert by_rule["repeated_item_errors"] == {"rule": "repeated_item_errors", "weaknesses": None, "learners": None, "status": "suppressed"}     # one learner
    # transport (2 learners) + shopping (1) are small; they hold 3 weaknesses and only 2 DISTINCT learners (x has both), still too few,
    # so the smallest visible topic (greetings, 6) joins: 5 weaknesses of x,y + 6 = 9 weaknesses, 8 learners
    assert [(b["key"], b["count"], b["learners"], b["status"]) for b in w["by_topic"]] == [("food", 8, 8, "ok"), ("other", 9, 8, "ok")]


def test_the_folded_bucket_counts_a_learner_once_even_across_topics(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 5):
            adm.weakness(conn, u, "food")
        ys = learners(conn, 5)
        for t in ("transport", "shopping", "directions", "college"):
            for u in ys[:2]:
                adm.weakness(conn, u, t)                  # 4 small topics, each with the same 2 learners
    w = get(admin, f"{A}/confidence-weakness")["weaknesses"]["by_topic"]
    assert [(b["key"], b["count"], b["learners"], b["status"]) for b in w] == [("other", 13, 7, "ok")] or [(b["key"], b["status"]) for b in w] == [("other", "ok")]
    other = next(b for b in w if b["key"] == "other")
    assert other["learners"] == 7 and other["count"] == 13                                         # 8 weaknesses by 2 learners + food's 5 learners joined to reach 5 learners


def test_a_small_weakness_group_alone_is_suppressed_without_inventing_numbers(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 3):
            adm.weakness(conn, u, "food")
    w = get(admin, f"{A}/confidence-weakness")["weaknesses"]
    assert w["by_rule"] == [{"rule": "low_topic_accuracy", "weaknesses": None, "learners": None, "status": "suppressed"}]
    assert w["by_topic"] == [{"key": "other", "label": "Other", "count": None, "learners": None, "status": "suppressed"}]


def test_weaknesses_never_name_a_learner_or_an_item_text(admin):
    with connect(main.DB_PATH) as conn:
        weakness_world(conn)
    text = admin.get(f"{A}/confidence-weakness").text
    assert not any(word in text for word in ("user_id", "item_id", "handle", "email", "@", "display_name", "password"))


# =====================================================================================================================
# engagement
# =====================================================================================================================
def test_xp_streak_achievement_and_challenge_activity(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 7)
        for n, u in enumerate(ls[:6]):
            adm.xp(conn, u, 100 + n, amount=10, earned="2026-03-10 10:00:00")
        adm.xp(conn, ls[0], 200, kind="lesson", amount=0, earned="2026-03-10 11:00:00")         # recognised but over the daily cap: an event, no xp
        adm.xp(conn, ls[6], 300, amount=50, earned="2026-01-10 10:00:00")                       # outside the window
        for u in ls[:5]:
            adm.streak_day(conn, u, "2026-03-10")
            adm.streak_day(conn, u, "2026-03-11")
        adm.streak_day(conn, ls[5], "2026-02-13")                                                # the day before the window
        for u in ls[:6]:
            adm.achievement(conn, u, 0, "2026-03-09 10:00:00")
        for u in ls[:5]:
            adm.achievement(conn, u, 1, "2026-03-09 11:00:00")
        adm.achievement(conn, ls[0], 2, "2026-03-09 12:00:00")
        for i, u in enumerate(ls):
            adm.challenge(conn, u, "2026-03-09", claimed=i < 5)
    e = get(admin, f"{A}/engagement")
    assert (ok_count(e["xp"]["events"]), ok_count(e["xp"]["xp_awarded"]), ok_count(e["xp"]["learners_earning"])) == ((7, "ok"), (60, "ok"), (6, "ok"))
    assert (ok_count(e["streak"]["streak_days"]), ok_count(e["streak"]["learners"])) == ((10, "ok"), (5, "ok"))
    assert (ok_count(e["achievements"]["unlocks"]), ok_count(e["achievements"]["learners"])) == ((12, "ok"), (6, "ok"))
    by = {b["key"]: (b["count"], b["learners"], b["status"]) for b in e["achievements"]["by_achievement"]}
    assert len(by) == 3 or "other" in by
    assert ok_count(e["challenges"]["started"]) == (7, "ok") and e["challenges"]["claim_rate"] == {"numerator": 5, "denominator": 7, "rate": 0.7143, "status": "ok"}


def test_achievement_buckets_fold_small_unlock_groups(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 6)
        for u in ls:
            adm.achievement(conn, u, 0, "2026-03-09 10:00:00")
        for u in ls[:2]:
            adm.achievement(conn, u, 1, "2026-03-09 10:00:00")
        adm.achievement(conn, ls[0], 2, "2026-03-09 10:00:00")
        codes = [r[0] for r in conn.execute("SELECT code FROM achievements ORDER BY sort_order LIMIT 3")]
    b = get(admin, f"{A}/engagement")["achievements"]["by_achievement"]
    # achievements 1 and 2 are small (2 and 1 learners, 2 DISTINCT in all) so the first (6 learners) joins them
    assert [(x["key"], x["count"], x["learners"], x["status"]) for x in b] == [("other", 9, 6, "ok")]
    assert codes[0] not in [x["key"] for x in b]


def test_small_engagement_groups_are_suppressed(admin):
    with connect(main.DB_PATH) as conn:
        for n, u in enumerate(learners(conn, 4)):
            adm.xp(conn, u, 500 + n, amount=10, earned="2026-03-10 10:00:00")
            adm.streak_day(conn, u, "2026-03-10")
            adm.challenge(conn, u, "2026-03-09", claimed=True)
    e = get(admin, f"{A}/engagement")
    sup = {"value": None, "status": "suppressed"}
    assert e["xp"] == {"events": sup, "xp_awarded": sup, "learners_earning": sup} and e["streak"] == {"streak_days": sup, "learners": sup}
    assert e["challenges"]["started"] == sup and e["challenges"]["claim_rate"]["status"] == "suppressed"


def test_engagement_excludes_the_demo_account_and_uses_the_window(admin):
    with connect(main.DB_PATH) as conn:
        for n, u in enumerate(learners(conn, 5)):
            adm.xp(conn, u, 600 + n, amount=10, earned="2026-03-10 10:00:00")
        demo = conn.execute("SELECT id FROM users WHERE handle = 'demo-alex'").fetchone()[0]
        adm.xp(conn, demo, 650, amount=99, earned="2026-03-10 10:00:00")
    assert ok_count(get(admin, f"{A}/engagement")["xp"]["xp_awarded"]) == (50, "ok")
    assert ok_count(get(admin, f"{A}/engagement?from=2026-03-11&to=2026-03-15")["xp"]["xp_awarded"]) == (0, "ok")


# =====================================================================================================================
# adaptive learning
# =====================================================================================================================
def test_recommendation_and_micro_lesson_usage(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 8)
        for i, u in enumerate(ls):
            adm.recommendation(conn, u, "2026-03-10 09:00:00", status="applied" if i < 5 else "active")
            adm.recommendation(conn, u, "2026-03-11 09:00:00", status="expired")
        adm.recommendation(conn, ls[0], "2026-01-10 09:00:00", status="applied")                   # outside the window
        for i, u in enumerate(ls[:6]):
            adm.micro_lesson(conn, u, "2026-03-10 09:00:00", attempts=[("2026-03-10 09:05:00", True), ("2026-03-10 09:06:00", i % 2 == 0)] if i < 5 else [])
        adm.micro_lesson(conn, ls[7], "2026-03-10 09:00:00")
    a = get(admin, f"{A}/adaptive")
    assert (ok_count(a["recommendations"]["shown"]), ok_count(a["recommendations"]["learners"])) == ((16, "ok"), (8, "ok"))
    assert a["recommendations"]["applied_rate"] == {"numerator": 5, "denominator": 16, "rate": 0.3125, "status": "ok"}
    ml = a["micro_lessons"]
    assert (ok_count(ml["generated"]), ok_count(ml["attempted"]), ok_count(ml["attempts"])) == ((7, "ok"), (5, "ok"), (10, "ok"))
    assert ml["attempt_accuracy"] == {"numerator": 8, "denominator": 10, "rate": 0.8, "status": "ok"}


def test_adaptive_usage_with_few_learners_or_few_applied_is_suppressed(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 8)
        for i, u in enumerate(ls):
            adm.recommendation(conn, u, "2026-03-10 09:00:00", status="applied" if i < 2 else "active")
    a = get(admin, f"{A}/adaptive")
    assert ok_count(a["recommendations"]["shown"]) == (8, "ok") and a["recommendations"]["applied_rate"]["status"] == "suppressed"          # only 2 learners applied any
    assert a["micro_lessons"]["generated"] == {"value": 0, "status": "ok"} and a["micro_lessons"]["attempt_accuracy"]["status"] == "no_data"


def test_the_adaptive_block_never_returns_recommendation_text(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 6):
            adm.recommendation(conn, u, "2026-03-10 09:00:00")
            adm.micro_lesson(conn, u, "2026-03-10 09:00:00", attempts=[("2026-03-10 09:05:00", True)])
    text = admin.get(f"{A}/adaptive").text
    assert "q?" not in text and "reason" not in text and "title" not in text and "question" not in text


# =====================================================================================================================
# content performance
# =====================================================================================================================
def test_content_performance_per_lesson_with_review_candidates(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 6)
        for i in range(36):                                                     # 36 attempts by 6 learners, 2 correct: accuracy 0.0556
            attempt(conn, ls[i % 6], "2026-03-05 10:00:00", correct=1 if i < 2 else 0, slug="food")
        for i in range(36):                                                     # 36 attempts, all correct: above 0.98
            attempt(conn, ls[i % 6], "2026-03-05 10:00:00", correct=1, slug="greetings")
        for i in range(12):                                                     # only 12 attempts: too few to flag
            attempt(conn, ls[i % 6], "2026-03-05 10:00:00", correct=0, slug="transport")
        for i in range(40):                                                     # a middling lesson
            attempt(conn, ls[i % 6], "2026-03-05 10:00:00", correct=i % 2, slug="shopping")
        small = learners(conn, 3)
        for u in small:
            attempt(conn, u, "2026-03-05 10:00:00", correct=0, slug="college")                # 3 learners: suppressed
        adm.lesson_progress(conn, ls[0], adm.lesson_id(conn, "food"), started="2026-03-04 10:00:00")
    r = get(admin, f"{A}/content-performance?kind=lesson")
    items = {i["slug"]: i for i in r["items"]}
    assert r["kind"] == "lesson" and r["total"] == 5 and set(items) == {"food", "greetings", "transport", "shopping", "college"}
    assert (items["food"]["attempts"], items["food"]["learners"], items["food"]["accuracy"], items["food"]["review_candidate"]) == (36, 6, 0.0556, True)
    assert (items["greetings"]["accuracy"], items["greetings"]["review_candidate"]) == (1.0, True)
    assert (items["transport"]["attempts"], items["transport"]["accuracy"], items["transport"]["review_candidate"]) == (12, 0.0, False)
    assert (items["shopping"]["accuracy"], items["shopping"]["review_candidate"]) == (0.5, False)
    assert items["college"] == {"id": items["college"]["id"], "slug": "college", "title": items["college"]["title"], "status": "published", "cell": "suppressed", "attempts": None,
                                "learners": None, "accuracy": None, "completion": None, "review_candidate": False}
    assert items["food"]["completion"] == {"numerator": None, "denominator": None, "rate": None, "status": "suppressed"}        # only one learner started it: that cohort is small too


def test_the_review_thresholds_are_exact(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 6)
        for i in range(30):                                                     # exactly 30 attempts, accuracy exactly 0.2: not below 0.2
            attempt(conn, ls[i % 6], "2026-03-05 10:00:00", correct=1 if i < 6 else 0, slug="food")
        for i in range(30):                                                     # 30 attempts, accuracy 0.1999.. is impossible, so use 29 vs 30 attempts at 0.0
            attempt(conn, ls[i % 6], "2026-03-05 10:00:00", correct=0, slug="greetings")
        for i in range(29):
            attempt(conn, ls[i % 6], "2026-03-05 10:00:00", correct=0, slug="transport")
        for i in range(100):                                                    # 100 attempts, 98 right: accuracy exactly 0.98, not above 0.98
            attempt(conn, ls[i % 6], "2026-03-05 10:00:00", correct=1 if i < 98 else 0, slug="shopping")
    items = {i["slug"]: i for i in get(admin, f"{A}/content-performance?kind=lesson")["items"]}
    assert (items["food"]["accuracy"], items["food"]["review_candidate"]) == (0.2, False)
    assert (items["greetings"]["attempts"], items["greetings"]["review_candidate"]) == (30, True)
    assert (items["transport"]["attempts"], items["transport"]["review_candidate"]) == (29, False)
    assert (items["shopping"]["accuracy"], items["shopping"]["review_candidate"]) == (0.98, False)


def test_content_performance_reports_archived_content_that_was_used_and_other_kinds(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 6)
        lid = adm.lesson_id(conn)
        for u in ls:
            attempt(conn, u, "2026-03-05 10:00:00")
        conn.execute("UPDATE lessons SET status = 'archived', archived_at = '2026-03-06 00:00:00' WHERE id = ?", (lid,))
        sid, step = adm.situation_id(conn), None
        step = adm.first_step(conn, sid)
        aid = adm.activity_id(conn)
        for u in ls:
            adm.step_attempt(conn, u, step, correct=1, at="2026-03-05 10:00:00")
            adm.situation_progress(conn, u, sid, started="2026-03-05 10:00:00", completed="2026-03-05 11:00:00")
            adm.listening_attempt(conn, u, aid, adm.right_option(conn, aid), correct=1, at="2026-03-05 10:00:00")
    lessons = get(admin, f"{A}/content-performance?kind=lesson")["items"]
    assert [(i["slug"], i["status"], i["learners"]) for i in lessons] == [("food", "archived", 6)]
    situations = get(admin, f"{A}/content-performance?kind=situation")["items"]
    assert len(situations) == 1 and situations[0]["completion"] == {"numerator": 6, "denominator": 6, "rate": 1.0, "status": "ok"} and situations[0]["attempts"] == 6
    listening = get(admin, f"{A}/content-performance?kind=listening")["items"]
    assert len(listening) == 1 and listening[0]["completion"] is None and listening[0]["accuracy"] == 1.0


def test_content_performance_paginates_and_validates(admin):
    with connect(main.DB_PATH) as conn:
        ls = learners(conn, 5)
        for slug in ("food", "greetings", "transport", "shopping"):
            for u in ls:
                attempt(conn, u, "2026-03-05 10:00:00", slug=slug)
    page = get(admin, f"{A}/content-performance?kind=lesson&limit=3&offset=0")
    assert (page["total"], page["limit"], page["offset"], len(page["items"])) == (4, 3, 0, 3) and len(get(admin, f"{A}/content-performance?limit=3&offset=3")["items"]) == 1
    assert get(admin, f"{A}/content-performance?offset=10")["items"] == []
    for q in ("kind=quiz", "limit=0", "limit=101", "offset=-1"):
        assert admin.get(f"{A}/content-performance?{q}").status_code == 422


# =====================================================================================================================
# windows over HTTP, access
# =====================================================================================================================
ANALYTICS = ["activity", "learning", "speaking", "confidence-weakness", "engagement", "adaptive", "content-performance"]


@pytest.mark.parametrize("name", ANALYTICS)
def test_every_analytics_endpoint_validates_its_window(admin, name):
    url = f"{A}/{name}"
    assert admin.get(url).status_code == 200 and admin.get(url + "?window=7d").status_code == 200 and admin.get(url + "?from=2026-03-01&to=2026-03-15").status_code == 200
    for bad in ("window=1y", "window=7d&from=2026-03-01", "from=2026-03-15&to=2026-03-01", "from=2026-13-01", "from=nonsense", "to=15-03-2026", "from=2025-03-15&to=2026-03-15", "from=2020-01-01"):
        assert admin.get(f"{url}?{bad}").status_code == 422, bad
    assert admin.get(url + "?from=2025-03-16&to=2026-03-15").status_code == 200                      # exactly 365 days


def test_the_dashboard_window_is_a_choice_of_three(admin):
    for w in ("7d", "30d", "90d"):
        assert get(admin, f"/api/admin/dashboard?window={w}")["window"]["days"] == int(w[:-1])
    for bad in ("1y", "365d", "0d", "", "30"):
        assert admin.get(f"/api/admin/dashboard?window={bad}").status_code == 422
    assert get(admin, "/api/admin/dashboard")["window_name"] == "30d"


def test_the_activity_grain_is_day_or_week(admin):
    assert admin.get(f"{A}/activity?grain=month").status_code == 422
    assert get(admin, f"{A}/activity?grain=week")["grain"] == "week" and get(admin, f"{A}/activity")["grain"] == "day"


@pytest.mark.parametrize("url", ["/api/admin/dashboard"] + [f"{A}/{n}" for n in ANALYTICS])
def test_analytics_refuse_everyone_but_admins(client, admin, url):
    for who in (Api(), register_browser("learner", "l@example.com"), register_browser("parent", "p@example.com"), demo_browser()):
        assert who.get(url).status_code in (401, 403)


# =====================================================================================================================
# the indexes this phase added are what make the windowed queries searches, not scans
# =====================================================================================================================
def test_every_windowed_query_uses_a_time_index(db_path):
    from backend.repositories import admin_analytics
    expected = {"exercise_attempts": "idx_exercise_attempts_time", "situation_step_attempts": "idx_situation_step_attempts_time", "listening_attempts": "idx_listening_attempts_time",
                "speaking_sessions": "idx_speaking_sessions_time", "pronunciation_assessments": "idx_pronunciation_time", "roleplay_turns": "idx_roleplay_turns_time",
                "ai_micro_lesson_attempts": "idx_ai_micro_attempts_time", "xp_events": "idx_xp_events_time"}
    assert set(admin_analytics.ACTIVITY) == set(expected)
    with connect(db_path) as conn:
        for name, sql in admin_analytics.ACTIVITY.items():
            plan = " ".join(r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + sql, {"start": "2026-01-01 00:00:00", "end": "2026-02-01 00:00:00"}))
            assert f"SEARCH {name} USING" in plan and expected[name] in plan and "SCAN" not in plan, (name, plan)


@pytest.mark.parametrize("day,in_wau,in_mau", [("2026-03-09", True, True), ("2026-03-08", False, True), ("2026-02-14", False, True), ("2026-02-13", False, False)])
def test_wau_reaches_back_six_days_and_mau_twenty_nine(admin, day, in_wau, in_mau):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 5):
            attempt(conn, u, f"{day} 12:00:00")
    a = get(admin, "/api/admin/dashboard")["activity"]
    assert ok_count(a["wau"]) == ((5 if in_wau else 0), "ok") and ok_count(a["mau"]) == ((5 if in_mau else 0), "ok")


def test_the_daily_series_wau_and_mau_reach_back_six_and_twenty_nine_days(admin):
    with connect(main.DB_PATH) as conn:
        for u in learners(conn, 5):
            attempt(conn, u, "2026-03-09 12:00:00")                  # six days before the 15th: inside its WAU, and its MAU
        for u in learners(conn, 5):
            attempt(conn, u, "2026-03-08 12:00:00")                  # seven days before: outside the WAU, inside the MAU
    pts = {p["date"]: p for p in get(admin, f"{A}/activity?from=2026-03-15&to=2026-03-15")["points"]}
    assert ok_count(pts["2026-03-15"]["wau"]) == (5, "ok") and ok_count(pts["2026-03-15"]["mau"]) == (10, "ok")

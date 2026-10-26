"""XP, levels, streaks, freezes, achievements and challenges over HTTP: rewards come only from real activity, once; nothing a
client sends can change XP, a level, a streak, a freeze, an achievement or a challenge."""
import json
import sqlite3

import pytest

from backend.gamification import rules

from .agekids import freeze_clock, make_learner
from .conftest import PASSWORD, register
from .gam import db, events, listen_right, listen_wrong, seed_event, summary, total_xp, uid
from .lis import activities, answer, correct_option, wrong_options


@pytest.fixture
def teen(client):
    return make_learner(client, "teen@example.com", 14)


def ids_of(user):
    return uid(user)


# ---------- access ----------
ENDPOINTS = [("get", "/api/gamification", None), ("put", "/api/gamification/settings", {"timezone": "UTC"}), ("get", "/api/gamification/achievements", None),
             ("get", "/api/gamification/challenges", None), ("post", "/api/gamification/challenges/1/claim", None)]


def call(c, method, path, body=None):
    return getattr(c, method)(path, **({"json": body} if body is not None else {}))


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_unauthenticated_rejected(client, lockdown, method, path, body):
    assert call(client, method, path, body).status_code == 401


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_parents_and_admins_rejected(client, client2, make_admin, method, path, body):
    register(client, "p@example.com", role="parent")
    assert call(client, method, path, body).status_code == 403
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert call(client2, method, path, body).status_code == 403


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_works_without_a_language_profile(client, method, path, body):
    register(client, "np@example.com")
    assert call(client, method, path, body).status_code in (200, 404, 409)
    assert client.get("/api/gamification").status_code == 200       # XP needs no profile; nothing has been done yet


def test_children_can_see_their_own_stars(client):
    make_learner(client, "kid@example.com", 7)
    assert client.get("/api/gamification").status_code == 200
    assert client.get("/api/gamification/achievements").status_code == 200


# ---------- XP is credited for real activity, once ----------
def test_a_new_learner_has_nothing(teen):
    s = summary(teen)
    assert s["xp"]["total"] == 0 and s["xp"]["level"] == 1 and s["xp"]["rank"] == "Explorer"
    assert s["streak"]["current"] == 0 and s["streak"]["freezes"] == 0 and s["recent"] == []


def test_correct_listening_earns_xp_once_wrong_earns_none(teen):
    listen_wrong(teen, 3)
    assert total_xp(teen) == 0
    listen_right(teen, 1)
    assert total_xp(teen) == rules.XP_RULES["listening"]
    listen_right(teen, 1)                                              # the SAME activity again: nothing more
    assert total_xp(teen) == rules.XP_RULES["listening"]
    listen_right(teen, 2)                                              # one new activity: +5
    assert total_xp(teen) == 2 * rules.XP_RULES["listening"]


def test_refreshing_and_replaying_never_pays_again(teen):
    listen_right(teen, 3)
    before = total_xp(teen)
    for _ in range(10):
        teen.get("/api/gamification"); teen.get("/api/gamification/achievements"); teen.get("/api/gamification/challenges")
    assert total_xp(teen) == before and len(events(uid("teen@example.com"))) == 3


def test_exercise_xp_once_per_exercise(teen):
    with db() as conn:
        ex = conn.execute("SELECT e.id, a.id AS ans FROM exercises e JOIN exercise_answers a ON a.exercise_id = e.id WHERE e.kind = 'multiple_choice' AND a.is_correct = 1 LIMIT 1").fetchone()
    for _ in range(3):
        assert teen.post(f"/api/exercises/{ex['id']}/attempts", json={"answer_id": ex["ans"]}).status_code == 200
    assert total_xp(teen) == rules.XP_RULES["exercise"]
    assert [e["kind"] for e in events(uid("teen@example.com"))] == ["exercise"]


def test_wrong_exercise_answers_earn_nothing(teen):
    with db() as conn:
        ex = conn.execute("SELECT e.id, a.id AS ans FROM exercises e JOIN exercise_answers a ON a.exercise_id = e.id WHERE e.kind = 'multiple_choice' AND a.is_correct = 0 LIMIT 1").fetchone()
    teen.post(f"/api/exercises/{ex['id']}/attempts", json={"answer_id": ex["ans"]})
    assert total_xp(teen) == 0


def test_lesson_and_situation_completion_pay_once(client, teen):
    me = uid("teen@example.com")
    with db() as conn:
        conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, 1, '2026-09-01 08:00:00', '2026-09-01 08:30:00')", (me,))
        conn.execute("INSERT INTO situation_progress(user_id, situation_id, started_at, completed_at) VALUES (?, 1, '2026-09-01 08:00:00', '2026-09-01 08:40:00')", (me,))
        conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at) VALUES (?, 2, '2026-09-01 08:00:00')", (me,))        # started, not completed
    assert total_xp(teen) == rules.XP_RULES["lesson"] + rules.XP_RULES["situation"]
    assert total_xp(teen) == rules.XP_RULES["lesson"] + rules.XP_RULES["situation"]
    assert {e["kind"] for e in events(me)} == {"lesson", "situation"}


def test_speaking_pays_once_per_phrase(client, teen, monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock")
    from .spk import prompt_items, transcribed
    first = prompt_items(teen)[0]["item"]["id"]
    transcribed(teen, "नमस्ते, आप कैसे हैं?", item_id=first)
    assert total_xp(teen) == rules.XP_RULES["speaking"]
    transcribed(teen, "नमस्ते, आप कैसे हैं?", item_id=first)           # same phrase again
    assert total_xp(teen) == rules.XP_RULES["speaking"]
    transcribed(teen, "नमस्ते", item_id=prompt_items(teen)[1]["item"]["id"])
    assert total_xp(teen) == 2 * rules.XP_RULES["speaking"]


def test_a_daily_task_marked_done_by_hand_earns_nothing(teen):
    teen.post("/api/daily-plan/generate")
    tasks = teen.get("/api/daily-plan").json()["plan"]["tasks"]
    assert tasks
    for t in tasks:
        assert teen.post(f"/api/daily-plan/tasks/{t['id']}/status", json={"status": "done"}).status_code == 200
    assert all(t["status"] == "done" for t in teen.get("/api/daily-plan").json()["plan"]["tasks"])      # really marked done...
    assert [e for e in events(uid("teen@example.com")) if e["kind"] == "daily_task"] == []              # ...and still worth nothing
    assert total_xp(teen) == 0


def test_a_verified_daily_task_pays_once(teen, monkeypatch):
    freeze_clock(monkeypatch)
    me = uid("teen@example.com")
    teen.post("/api/daily-plan/generate")
    with db() as conn:
        task = conn.execute("SELECT id, lesson_id FROM daily_tasks WHERE user_id = ? AND task_type = 'study_lesson' LIMIT 1", (me,)).fetchone()
        assert task, "the plan starts with a lesson"
        conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, ?, '2026-09-01 08:00:00', '2026-09-01 08:30:00')", (me, task["lesson_id"]))
    summary(teen)                                                       # credits the lesson; the plan view marks the task done
    teen.get("/api/daily-plan")
    summary(teen)
    kinds = [e["kind"] for e in events(me)]
    assert kinds.count("daily_task") == 1 and kinds.count("lesson") == 1
    assert total_xp(teen) == rules.XP_RULES["lesson"] + rules.XP_RULES["daily_task"]


def test_daily_cap_records_overflow_as_zero(teen):
    me = uid("teen@example.com")
    with db() as conn:
        for (eid,) in conn.execute("SELECT id FROM exercises").fetchall():
            conn.execute("INSERT INTO exercise_attempts(user_id, exercise_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, 'x', 1, '2026-09-01 09:00:00')", (me, eid))
        for (lid,) in conn.execute("SELECT id FROM lessons").fetchall():
            conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, ?, '2026-09-01 08:00:00', '2026-09-01 10:00:00')", (me, lid))
    assert total_xp(teen) == rules.DAILY_XP_CAP
    ev = events(me)
    assert sum(e["xp"] for e in ev) == rules.DAILY_XP_CAP and any(e["xp"] == 0 for e in ev) and all(e["day"] == "2026-09-01" for e in ev)
    assert len(ev) == len({(e["kind"], e["source_id"]) for e in ev})


def test_cap_is_per_day(teen):
    me = uid("teen@example.com")
    with db() as conn:
        for i, (eid,) in enumerate(conn.execute("SELECT id FROM exercises").fetchall()):
            conn.execute("INSERT INTO exercise_attempts(user_id, exercise_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, 'x', 1, ?)",
                         (me, eid, "2026-09-01 09:00:00" if i < 17 else "2026-09-02 09:00:00"))
        for (lid,) in conn.execute("SELECT id FROM lessons").fetchall():
            conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, ?, '2026-09-02 08:00:00', '2026-09-02 10:00:00')", (me, lid))
    summary(teen)
    by_day = {}
    for e in events(me):
        by_day[e["day"]] = by_day.get(e["day"], 0) + e["xp"]
    assert by_day["2026-09-02"] == rules.DAILY_XP_CAP and by_day["2026-09-01"] == 85


def test_totals_are_independent_per_learner(client, client2, teen):
    other = make_learner(client2, "other@example.com", 14)
    listen_right(teen, 3)
    assert total_xp(teen) == 15 and total_xp(other) == 0


# ---------- nothing a client sends changes anything ----------
@pytest.mark.parametrize("path", ["/api/gamification/xp", "/api/gamification/award", "/api/gamification/level", "/api/gamification/streak", "/api/gamification/freeze",
                                  "/api/gamification/freezes", "/api/gamification/achievements/first_lesson/unlock", "/api/gamification/achievements/unlock",
                                  "/api/social/leaderboard/score", "/api/xp"])
@pytest.mark.parametrize("method", ["post", "put", "patch"])
def test_there_is_no_endpoint_to_grant_anything(teen, path, method):
    assert getattr(teen, method)(path, json={"xp": 1000, "level": 20, "streak": 99, "freezes": 5}).status_code in (404, 405)
    assert total_xp(teen) == 0


@pytest.mark.parametrize("body", [{"xp": 100}, {"xp": -5}, {"reward_xp": 999}, {"progress": 99}, {"user_id": 1}, {"level": 20}])
def test_claim_rejects_any_client_value(teen, body):
    listen_right(teen, 3)
    cid = next(c["id"] for c in teen.get("/api/gamification/challenges").json()["challenges"] if c["status"] == "claimable")
    assert teen.post(f"/api/gamification/challenges/{cid}/claim", json=body).status_code == 422
    assert total_xp(teen) == 15


@pytest.mark.parametrize("body", [{}, {"timezone": ""}, {"timezone": 5}, {"timezone": None}, {"timezone": "Mars/Base"}, {"timezone": "UTC", "xp": 5}, {"timezone": "x" * 80}])
def test_timezone_is_validated(teen, body):
    assert teen.put("/api/gamification/settings", json=body).status_code == 422
    assert summary(teen)["timezone"] == "UTC"


def test_negative_or_inflated_xp_cannot_exist_in_the_ledger(teen):
    me = uid("teen@example.com")
    summary(teen)
    for xp in (-1, 101, 10 ** 6):
        with pytest.raises(sqlite3.IntegrityError), db() as conn:
            conn.execute("INSERT INTO xp_events(user_id, kind, source_id, xp, earned_at, day, created_at) VALUES (?, 'lesson', 99, ?, 't', '2026-09-01', 't')", (me, xp))


def test_the_ledger_refuses_duplicates_and_edits(teen):
    me = uid("teen@example.com")
    listen_right(teen, 1)
    summary(teen)
    ev = events(me)[0]
    with pytest.raises(sqlite3.IntegrityError), db() as conn:
        conn.execute("INSERT INTO xp_events(user_id, kind, source_id, xp, earned_at, day, created_at) VALUES (?, ?, ?, 5, 't', '2026-09-01', 't')", (me, ev["kind"], ev["source_id"]))
    with pytest.raises(sqlite3.IntegrityError), db() as conn:
        conn.execute("UPDATE xp_events SET xp = 100 WHERE user_id = ?", (me,))
    assert total_xp(teen) == 5


# ---------- levels ----------
def test_level_follows_the_ledger(teen):
    me = uid("teen@example.com")
    summary(teen)
    seed_event(me, "challenge", 1, 99, "2026-09-01")
    assert summary(teen)["xp"]["level"] == 1 and summary(teen)["xp"]["to_next"] == 1
    seed_event(me, "challenge", 2, 1, "2026-09-01")
    x = summary(teen)["xp"]
    assert (x["total"], x["level"], x["into_level"], x["level_start"], x["next_level_at"]) == (100, 2, 0, 100, 300)


def test_cefr_level_is_separate_from_xp_level(teen):
    me = uid("teen@example.com")
    summary(teen)
    for i in range(10):
        seed_event(me, "challenge", i + 1, 100, "2026-09-01")
    assert summary(teen)["xp"]["level"] > 1
    assert teen.get("/api/profile").json()["profile"]["cefr_level"] == "A1"          # the learner profile stays authoritative


def test_confidence_is_unchanged_by_xp(teen):
    before = teen.get("/api/confidence").json()
    listen_right(teen, 5)
    summary(teen)
    after = teen.get("/api/confidence").json()
    assert set(after) == set(before) and "xp" not in json.dumps(after).lower()


# ---------- achievements ----------
def test_achievements_unlock_from_real_progress_once(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    by = lambda: {a["code"]: a for a in teen.get("/api/gamification/achievements").json()["achievements"]}
    assert not any(a["unlocked"] for a in by().values())
    assert by()["listening_10"]["progress"] == 0 and by()["listening_10"]["target"] == 10
    listen_right(teen, 10)
    got = by()
    assert got["listening_10"]["unlocked"] and got["xp_100"]["progress"] == 50 and not got["xp_100"]["unlocked"]
    stamp = got["listening_10"]["unlocked_at"]
    tick(3600)
    assert by()["listening_10"]["unlocked_at"] == stamp                    # unlocked once, timestamp stable
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM learner_achievements WHERE user_id = ?", (uid("teen@example.com"),)).fetchone()[0] == 1


def test_first_lesson_and_xp_milestones(teen):
    me = uid("teen@example.com")
    with db() as conn:
        conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, 1, '2026-09-01 08:00:00', '2026-09-01 08:30:00')", (me,))
    got = {a["code"]: a for a in teen.get("/api/gamification/achievements").json()["achievements"]}
    assert got["first_lesson"]["unlocked"] and not got["first_situation"]["unlocked"]
    seed_event(me, "challenge", 50, 100, "2026-09-01")
    got = {a["code"]: a for a in teen.get("/api/gamification/achievements").json()["achievements"]}
    assert got["xp_100"]["unlocked"] and not got["xp_500"]["unlocked"]


def test_an_achievement_can_only_be_unlocked_once_in_the_database(teen):
    me = uid("teen@example.com")
    summary(teen)
    with db() as conn:
        conn.execute("INSERT INTO learner_achievements VALUES (?, 1, 't')", (me,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO learner_achievements VALUES (?, 1, 't2')", (me,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO learner_achievements VALUES (?, 999, 't')", (me,))


def test_achievement_definitions_are_unique_and_few(db_path):
    from backend.db import connect
    with connect(db_path) as conn:
        rows = conn.execute("SELECT code, metric, threshold FROM achievements").fetchall()
        assert len(rows) < 15 and len({r[0] for r in rows}) == len(rows) and len({(r[1], r[2]) for r in rows}) == len(rows)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO achievements(code, title, description, metric, threshold, sort_order) VALUES ('x', 'x', 'x', 'total_xp', 0, 99)")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO achievements(code, title, description, metric, threshold, sort_order) VALUES ('y', 'y', 'y', 'nonsense', 5, 99)")


# ---------- streaks ----------
def one_activity_a_day(c, days, tick, start_skip=0):
    for i in range(days):
        listen_right(c, 1, skip=start_skip + i)
        tick(86400)


def test_streak_counts_days_not_actions(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    listen_right(teen, 4)                                                  # four answers on one day
    assert summary(teen)["streak"]["current"] == 1
    tick(86400)
    listen_right(teen, 1, skip=4)
    assert summary(teen)["streak"]["current"] == 2
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM streak_days WHERE user_id = ?", (uid("teen@example.com"),)).fetchone()[0] == 2


def test_consecutive_days_build_and_a_missed_day_resets(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    one_activity_a_day(teen, 3, tick)
    assert summary(teen)["streak"]["current"] == 3 and summary(teen)["streak"]["at_risk"] is True
    tick(86400)                                                            # a whole day with nothing
    s = summary(teen)["streak"]
    assert s["current"] == 0 and s["longest"] == 3
    listen_right(teen, 1, skip=3)
    s = summary(teen)["streak"]
    assert s["current"] == 1 and s["longest"] == 3 and s["freezes"] == 0


def test_a_wrong_answer_is_not_a_learning_day(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    listen_wrong(teen, 3)
    assert summary(teen)["streak"]["current"] == 0


def test_reading_pages_does_not_extend_a_streak(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    listen_right(teen, 1)
    tick(86400)
    for _ in range(5):
        summary(teen)
    tick(86400 * 3)
    for _ in range(3):
        teen.get("/api/gamification/challenges")
    assert summary(teen)["streak"]["current"] == 0


def build_week(c, tick):
    for i in range(7):
        listen_right(c, 1, skip=i)
        if i < 6:
            tick(86400)


def test_a_freeze_is_earned_on_the_seventh_day(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    build_week(teen, tick)
    s = summary(teen)["streak"]
    assert s["current"] == 7 and s["freezes"] == 1 and s["freeze_log"] == [{"kind": "earned", "day": "2026-09-07"}]


def test_a_freeze_protects_a_missed_day_once(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    build_week(teen, tick)                                                 # day 7 (09-07), one freeze
    tick(86400 * 2)                                                        # miss 09-08, return 09-09
    listen_right(teen, 1, skip=7)
    s = summary(teen)["streak"]
    assert s["current"] == 8 and s["freezes"] == 0
    assert {"kind": "used", "day": "2026-09-08"} in s["freeze_log"]
    for _ in range(3):
        again = summary(teen)["streak"]                                    # replays spend nothing more
    assert again["freezes"] == 0 and again["current"] == 8
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM streak_freezes WHERE kind = 'used'").fetchone()[0] == 1


def test_without_enough_freezes_the_streak_restarts_and_keeps_the_freeze(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    build_week(teen, tick)
    tick(86400 * 3)                                                        # two missed days, one freeze
    listen_right(teen, 1, skip=7)
    s = summary(teen)["streak"]
    assert s["current"] == 1 and s["longest"] == 7 and s["freezes"] == 1


def test_freeze_balance_never_exceeds_the_cap(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    for i in range(15):
        listen_right(teen, 1, skip=i)
        tick(86400)
    s = summary(teen)["streak"]
    assert s["current"] == 15 and s["freezes"] == 2 and rules.MAX_FREEZES == 2


def test_the_freeze_trigger_enforces_the_cap_and_balance_itself(teen):
    me = uid("teen@example.com")
    summary(teen)
    with db() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO streak_freezes(user_id, kind, day, created_at) VALUES (?, 'used', '2026-09-01', 't')", (me,))        # nothing to spend
        conn.execute("INSERT INTO streak_freezes(user_id, kind, day, created_at) VALUES (?, 'earned', '2026-09-01', 't')", (me,))
        conn.execute("INSERT INTO streak_freezes(user_id, kind, day, created_at) VALUES (?, 'earned', '2026-09-02', 't')", (me,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO streak_freezes(user_id, kind, day, created_at) VALUES (?, 'earned', '2026-09-03', 't')", (me,))       # over the cap
        conn.execute("INSERT INTO streak_freezes(user_id, kind, day, created_at) VALUES (?, 'used', '2026-09-04', 't')", (me,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO streak_freezes(user_id, kind, day, created_at) VALUES (?, 'used', '2026-09-04', 't')", (me,))       # same day twice
        conn.execute("INSERT INTO streak_freezes(user_id, kind, day, created_at) VALUES (?, 'used', '2026-09-05', 't')", (me,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO streak_freezes(user_id, kind, day, created_at) VALUES (?, 'used', '2026-09-06', 't')", (me,))       # balance would go negative
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE streak_freezes SET day = '2026-12-01' WHERE user_id = ?", (me,))


def test_freeze_ledger_is_scoped_per_learner(client, client2, teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    other = make_learner(client2, "other@example.com", 14)
    build_week(teen, tick)
    assert summary(teen)["streak"]["freezes"] == 1 and summary(other)["streak"]["freezes"] == 0


# ---------- timezones ----------
def test_the_learners_timezone_decides_the_day(teen, monkeypatch):
    freeze_clock(monkeypatch, "2026-09-01 20:00:00")                       # 01:30 on 09-02 in Kolkata
    assert teen.put("/api/gamification/settings", json={"timezone": "Asia/Kolkata"}).json() == {"timezone": "Asia/Kolkata"}
    listen_right(teen, 1)
    s = summary(teen)
    assert s["today"]["date"] == "2026-09-02" and events(uid("teen@example.com"))[0]["day"] == "2026-09-02"


def test_changing_timezone_does_not_rewrite_past_days(teen, monkeypatch):
    freeze_clock(monkeypatch, "2026-09-01 20:00:00")
    listen_right(teen, 1)
    summary(teen)
    assert events(uid("teen@example.com"))[0]["day"] == "2026-09-01"
    teen.put("/api/gamification/settings", json={"timezone": "Asia/Kolkata"})
    summary(teen)
    assert events(uid("teen@example.com"))[0]["day"] == "2026-09-01"       # it happened on the 1st (UTC) and stays there


def test_unsynced_activity_is_placed_with_the_timezone_in_force_when_it_was_set(teen, monkeypatch):
    freeze_clock(monkeypatch, "2026-09-01 20:00:00")
    listen_right(teen, 1)                                                  # not yet credited
    teen.put("/api/gamification/settings", json={"timezone": "Asia/Kolkata"})   # crediting happens first, under UTC
    assert events(uid("teen@example.com"))[0]["day"] == "2026-09-01"


# ---------- challenges ----------
def by_title(c):
    return {x["title"]: x for x in c.get("/api/gamification/challenges").json()["challenges"]}


def test_challenges_show_progress_and_become_claimable(teen, monkeypatch):
    freeze_clock(monkeypatch)
    ch = by_title(teen)["Get 3 listening activities right"]
    assert (ch["progress"], ch["target"], ch["status"], ch["reward_xp"], ch["period"]) == (0, 3, "active", 15, "daily")
    listen_right(teen, 2)
    assert by_title(teen)["Get 3 listening activities right"]["progress"] == 2
    listen_right(teen, 3)
    assert by_title(teen)["Get 3 listening activities right"]["status"] == "claimable"
    assert by_title(teen)["Get 3 listening activities right"]["progress"] == 3                 # capped at the target


def test_claim_pays_the_defined_reward_once(teen, monkeypatch):
    freeze_clock(monkeypatch)
    listen_right(teen, 3)
    ch = by_title(teen)["Get 3 listening activities right"]
    r = teen.post(f"/api/gamification/challenges/{ch['id']}/claim")
    assert r.status_code == 200 and r.json()["challenge"]["status"] == "claimed" and r.json()["xp"]["total"] == 15 + 15
    assert total_xp(teen) == 30
    for _ in range(3):
        assert teen.post(f"/api/gamification/challenges/{ch['id']}/claim").status_code == 409
    assert total_xp(teen) == 30
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM xp_events WHERE kind = 'challenge'").fetchone()[0] == 1
    got = {a["code"]: a for a in teen.get("/api/gamification/achievements").json()["achievements"]}
    assert got["challenge_1"]["unlocked"]


def test_cannot_claim_early(teen, monkeypatch):
    freeze_clock(monkeypatch)
    listen_right(teen, 2)
    ch = by_title(teen)["Get 3 listening activities right"]
    r = teen.post(f"/api/gamification/challenges/{ch['id']}/claim")
    assert r.status_code == 409 and "not finished" in r.json()["detail"]
    assert total_xp(teen) == 10 and by_title(teen)["Get 3 listening activities right"]["status"] == "active"


def test_a_challenge_expires_unclaimed(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    listen_right(teen, 3)
    ch = by_title(teen)["Get 3 listening activities right"]
    tick(86400)
    assert "Get 3 listening activities right" in by_title(teen)                     # today's new instance
    assert by_title(teen)["Get 3 listening activities right"]["id"] != ch["id"]
    r = teen.post(f"/api/gamification/challenges/{ch['id']}/claim")
    assert r.status_code == 409 and "ended" in r.json()["detail"]
    assert total_xp(teen) == 15


def test_a_new_period_starts_fresh_and_weekly_runs_monday_to_sunday(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)                                                # Tuesday 2026-09-01
    w = by_title(teen)["Complete 2 lessons this week"]
    assert (w["period_start"], w["period_end"]) == ("2026-08-31", "2026-09-06")
    tick(86400 * 5)                                                                 # Sunday: same week
    assert by_title(teen)["Complete 2 lessons this week"]["id"] == w["id"]
    tick(86400)                                                                     # Monday: next week
    n = by_title(teen)["Complete 2 lessons this week"]
    assert n["id"] != w["id"] and (n["period_start"], n["period_end"]) == ("2026-09-07", "2026-09-13")


def test_weekly_challenge_counts_the_whole_week(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    me = uid("teen@example.com")
    with db() as conn:
        for lid, day in ((1, "2026-08-31"), (2, "2026-09-01")):
            conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, ?, ?, ?)", (me, lid, day + " 08:00:00", day + " 09:00:00"))
    w = by_title(teen)["Complete 2 lessons this week"]
    assert w["progress"] == 2 and w["status"] == "claimable"


def test_streak_challenge_uses_the_streak(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    for i in range(5):
        listen_right(teen, 1, skip=i)
        if i < 4:
            tick(86400)
    c = by_title(teen)["Keep a 5-day streak"]
    assert c["progress"] == 5 and c["status"] == "claimable"


def test_claiming_does_not_count_as_activity_or_toward_xp_challenges(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    listen_right(teen, 3)
    ch = by_title(teen)["Get 3 listening activities right"]
    teen.post(f"/api/gamification/challenges/{ch['id']}/claim")
    assert by_title(teen)["Earn 30 XP today"]["progress"] == 15                      # 3 x 5 activity XP; the 15 reward does not feed it
    me = uid("teen@example.com")
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM streak_days WHERE user_id = ?", (me,)).fetchone()[0] == 1


def test_a_challenge_reward_alone_is_not_a_learning_day(teen, monkeypatch):
    tick = freeze_clock(monkeypatch)
    me = uid("teen@example.com")
    summary(teen)
    seed_event(me, "challenge", 77, 40, "2026-09-01")
    assert summary(teen)["streak"]["current"] == 0


def test_someone_elses_challenge_is_not_found(client, client2, teen, monkeypatch):
    freeze_clock(monkeypatch)
    other = make_learner(client2, "other@example.com", 14)
    listen_right(other, 3)
    theirs = by_title(other)["Get 3 listening activities right"]
    r = teen.post(f"/api/gamification/challenges/{theirs['id']}/claim")
    assert r.status_code == 404
    assert teen.post("/api/gamification/challenges/99999/claim").status_code == 404
    assert total_xp(other) == 15 and by_title(other)["Get 3 listening activities right"]["status"] == "claimable"


def test_challenge_constraints(teen):
    me = uid("teen@example.com")
    summary(teen)
    with db() as conn:
        cid = conn.execute("SELECT id FROM challenges LIMIT 1").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO learner_challenges(user_id, challenge_id, period_start, period_end) SELECT user_id, challenge_id, period_start, period_end FROM learner_challenges LIMIT 1")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO learner_challenges(user_id, challenge_id, period_start, period_end) VALUES (?, ?, '2026-09-05', '2026-09-01')", (me, cid))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO challenges(code, title, period, metric, target, reward_xp, sort_order) VALUES ('z', 'z', 'daily', 'xp', 0, 5, 9)")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO challenges(code, title, period, metric, target, reward_xp, sort_order) VALUES ('z', 'z', 'daily', 'xp', 5, 500, 9)")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO challenges(code, title, period, metric, target, reward_xp, sort_order) VALUES ('z', 'z', 'monthly', 'xp', 5, 5, 9)")


def test_an_inactive_challenge_is_not_offered(teen):
    with db() as conn:
        conn.execute("UPDATE challenges SET active = 0 WHERE code = 'daily_xp'")
    assert "Earn 30 XP today" not in by_title(teen)


# ---------- privacy ----------
def test_responses_carry_no_private_data(teen):
    listen_right(teen, 3)
    blob = json.dumps([summary(teen), teen.get("/api/gamification/achievements").json(), teen.get("/api/gamification/challenges").json()])
    for needle in ("teen@example.com", "date_of_birth", "password", "handle", "user_id"):
        assert needle not in blob


def test_existing_phases_still_work(teen):
    for path in ("/api/lessons", "/api/situations", "/api/listening", "/api/recommendations", "/api/daily-plan", "/api/weaknesses", "/api/confidence", "/api/experience"):
        assert teen.get(path).status_code == 200


# ---------- each guard holds on its own (the repository layer) ----------
def test_the_repository_refuses_double_rewards_and_double_claims(db_path):
    from backend.db import connect
    from backend.repositories import gamification as repo
    with connect(db_path) as conn:
        conn.execute("INSERT INTO users(handle, display_name) VALUES ('g1', 'G')")
        u = conn.execute("SELECT id FROM users WHERE handle = 'g1'").fetchone()[0]
        repo.create_settings(conn, u, "t")
        assert repo.insert_event(conn, u, "lesson", 1, 20, "2026-09-01 09:00:00", "2026-09-01", "t") is True
        assert repo.insert_event(conn, u, "lesson", 1, 20, "2026-09-01 09:00:00", "2026-09-01", "t") is False        # same thing: no second reward
        assert repo.insert_event(conn, u, "lesson", 2, 20, "2026-09-01 09:00:00", "2026-09-01", "t") is True         # another thing: rewarded
        assert repo.total_xp(conn, u) == 40
        # a credited lesson is no longer offered as an uncredited source
        conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, 1, 'a', 'b')", (u,))
        conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, 3, 'a', 'b')", (u,))
        assert [s["source_id"] for s in repo.uncredited_sources(conn, u) if s["kind"] == "lesson"] == [3]
        cid = conn.execute("SELECT id FROM challenges LIMIT 1").fetchone()[0]
        repo.ensure_instance(conn, u, cid, "2026-09-01", "2026-09-01")
        inst = conn.execute("SELECT id FROM learner_challenges").fetchone()[0]
        assert repo.mark_claimed(conn, u, inst, "t") is True
        assert repo.mark_claimed(conn, u, inst, "t2") is False                                                          # claimed once
        assert repo.mark_claimed(conn, u + 1, inst, "t3") is False


def test_the_repository_scopes_challenges_to_their_owner(db_path):
    from backend.db import connect
    from backend.repositories import gamification as repo
    with connect(db_path) as conn:
        for h in ("o1", "o2"):
            conn.execute("INSERT INTO users(handle, display_name) VALUES (?, 'O')", (h,))
        a, b = [r[0] for r in conn.execute("SELECT id FROM users WHERE handle IN ('o1', 'o2') ORDER BY handle")]
        cid = conn.execute("SELECT id FROM challenges LIMIT 1").fetchone()[0]
        repo.ensure_instance(conn, a, cid, "2026-09-01", "2026-09-01")
        inst = conn.execute("SELECT id FROM learner_challenges").fetchone()[0]
        assert repo.get_instance(conn, a, inst) is not None and repo.get_instance(conn, b, inst) is None
        assert repo.current_instances(conn, b, "2026-09-01") == []
        repo.insert_event(conn, a, "challenge", 1, 40, "t", "2026-09-01", "t")
        assert repo.xp_between(conn, a, "2026-09-01", "2026-09-01") == 0          # challenge rewards are not activity XP
        assert repo.xp_since(conn, a, "2026-09-01") == 40 and repo.xp_since(conn, b, "2026-09-01") == 0


def test_unfinished_situations_and_unfinished_speaking_earn_nothing(teen, monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock")
    me = uid("teen@example.com")
    with db() as conn:
        conn.execute("INSERT INTO situation_progress(user_id, situation_id, started_at) VALUES (?, 1, '2026-09-01 08:00:00')", (me,))
    from .spk import create, prompt_items, cancel
    s = create(teen, prompt_items(teen)[0]["item"]["id"])                       # created, never recorded
    s2 = create(teen, prompt_items(teen)[1]["item"]["id"])
    cancel(teen, s2["id"])
    assert total_xp(teen) == 0 and events(me) == []


def test_xp_values_are_exactly_the_documented_ones():
    assert rules.XP_RULES == {"exercise": 5, "lesson": 20, "situation": 25, "listening": 5, "speaking": 10, "daily_task": 10}
    assert rules.DAILY_XP_CAP == 150 and rules.MAX_LEVEL == 20


def test_replaying_a_claim_says_it_was_already_claimed(teen, monkeypatch):
    freeze_clock(monkeypatch)
    listen_right(teen, 3)
    cid = next(c["id"] for c in teen.get("/api/gamification/challenges").json()["challenges"] if c["status"] == "claimable")
    assert teen.post(f"/api/gamification/challenges/{cid}/claim").status_code == 200
    assert "already been claimed" in teen.post(f"/api/gamification/challenges/{cid}/claim").json()["detail"]


def test_progress_is_capped_at_the_target(teen, monkeypatch):
    freeze_clock(monkeypatch)
    listen_right(teen, 5)                                                       # five distinct activities; the challenge asks for three
    ch = {c["title"]: c for c in teen.get("/api/gamification/challenges").json()["challenges"]}["Get 3 listening activities right"]
    assert ch["progress"] == 3 and ch["target"] == 3


def test_one_learners_achievements_are_not_anothers(client, client2, teen):
    other = make_learner(client2, "other@example.com", 14)
    listen_right(teen, 10)
    got = {a["code"]: a["unlocked"] for a in teen.get("/api/gamification/achievements").json()["achievements"]}
    assert got["listening_10"] is True
    theirs = {a["code"]: a for a in other.get("/api/gamification/achievements").json()["achievements"]}
    assert not any(a["unlocked"] for a in theirs.values()) and theirs["listening_10"]["progress"] == 0


def test_only_the_addressee_can_answer_at_the_repository_level(db_path):
    from backend.db import connect
    from backend.repositories import social as repo
    with connect(db_path) as conn:
        a, b, c = [conn.execute("INSERT INTO users(handle, display_name) VALUES (?, ?)", (f"s{i}", f"S{i}")).lastrowid for i in range(3)]
        rid = repo.insert_request(conn, a, b, "2026-09-01 09:00:00")
        assert repo.respond(conn, rid, a, "accepted", "t") is False                 # the sender
        assert repo.respond(conn, rid, c, "accepted", "t") is False                 # a stranger
        assert repo.get_incoming(conn, c, rid) is None and repo.get_incoming(conn, a, rid) is None
        assert repo.respond(conn, rid, b, "accepted", "t") is True
        assert repo.respond(conn, rid, b, "rejected", "t") is False                 # only while pending


def test_a_friends_list_is_only_the_callers(db_path):
    from backend.db import connect
    from backend.repositories import social as repo
    with connect(db_path) as conn:
        a, b, c, d = [conn.execute("INSERT INTO users(handle, display_name) VALUES (?, ?)", (f"f{i}", f"F{i}")).lastrowid for i in range(4)]
        repo.insert_friendship(conn, a, b, "t")
        repo.insert_friendship(conn, c, d, "t")
        assert [f["friend_id"] for f in repo.list_friendships(conn, a)] == [b]
        assert [f["friend_id"] for f in repo.list_friendships(conn, d)] == [c]
        assert repo.count_friends(conn, a) == 1
        fid = repo.list_friendships(conn, c)[0]["id"]
        assert repo.delete_friendship(conn, a, fid) is False                         # not theirs
        assert repo.delete_friendship(conn, d, fid) is True


def test_the_service_rejects_an_unknown_leaderboard_period(client):
    from backend.social import service
    from .agekids import make_learner as ml
    ml(client, "x@example.com", 14)
    from backend import main
    from .gam import uid as u
    with pytest.raises(service.InvalidInput):
        service.leaderboard(main.DB_PATH, u("x@example.com"), "forever")


def test_a_non_learner_with_a_code_cannot_be_befriended(client, client2):
    """Even a parent account that somehow has a profile and a friend code is not reachable: only learners can be friends."""
    from backend import main
    from backend.auth import service as auth
    from backend.learner import service as learner_service
    teen = make_learner(client, "t@example.com", 14)
    parent, _ = auth.create_user(main.DB_PATH, email="par@example.com", password=PASSWORD, display_name="Par", roles=["parent"])
    learner_service.save_profile(main.DB_PATH, parent.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth=profile_dob())
    with db() as conn:
        conn.execute("INSERT INTO learner_gamification(user_id, friend_code, created_at) VALUES (?, 'PARENTCODE', 't')", (parent.id,))
    assert teen.post("/api/social/friends/requests", json={"code": "PARENTCODE"}).status_code == 404


def profile_dob():
    from .agekids import profile
    return profile(14)["date_of_birth"]

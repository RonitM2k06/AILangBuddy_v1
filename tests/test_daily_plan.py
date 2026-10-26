import threading

import pytest

from backend import main
from backend.db import connect
from backend.personalization import clock, plan as plan_service, rules
from backend.repositories import personalization as repo

from .conftest import register
from .pers import complete_lesson, complete_situation, cycle_attempts, db, uid

PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}
DAY = "2026-01-15"   # well before "now", so anything the learner does in the test counts as done on/after the plan date


@pytest.fixture(autouse=True)
def fixed_day(monkeypatch):
    monkeypatch.setattr(clock, "today", lambda: DAY)


@pytest.fixture
def learner(client):
    register(client, "l@example.com")
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


def get_plan(c):
    r = c.get("/api/daily-plan")
    assert r.status_code == 200
    return r.json()["plan"]


def generate(c):
    r = c.post("/api/daily-plan/generate")
    assert r.status_code == 200
    return r.json()["plan"]


def shape(plan):
    return [(t["priority"], t["task_type"], t["source"], t["target"]["title"]) for t in plan["tasks"]]


def task_count():
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM daily_tasks").fetchone()[0]


# ---------- generation ----------
def test_no_plan_until_one_is_generated(learner):
    assert get_plan(learner) == {"date": DAY, "generated": False, "tasks": [], "done": 0, "total": 0}
    assert task_count() == 0


def test_new_learner_gets_a_small_starting_plan(learner):
    plan = generate(learner)
    assert shape(plan) == [(1, "study_lesson", "next_lesson", "Greetings"), (2, "practice_situation", "next_situation", "Meet your landlady")]
    assert plan["generated"] and (plan["done"], plan["total"], plan["date"]) == (0, 2, DAY)
    t = plan["tasks"][0]
    assert t["status"] == "pending" and t["completed_at"] is None and t["why"] == "Your next lesson" and t["target"]["type"] == "lesson"
    assert get_plan(learner) == plan


def test_plan_is_personalised_from_real_data(learner):
    user = uid("l@example.com")
    cycle_attempts(user, "transport", [0, 0, 0, 0, 1, 1])
    learner.post("/api/confidence", json={"topic": "shopping", "score": 25})
    assert shape(generate(learner))[0] == (1, "study_lesson", "review_topic", "Transport")
    assert len(shape(generate(learner))) == rules.DAILY_TASK_LIMIT


def test_plan_size_is_limited(learner):
    user = uid("l@example.com")
    for slug in ("transport", "food", "shopping", "directions"):
        cycle_attempts(user, slug, [0] * 7)
    plan = generate(learner)
    assert plan["total"] == rules.DAILY_TASK_LIMIT and [t["priority"] for t in plan["tasks"]] == [1, 2, 3]


def test_a_learner_without_content_gets_an_empty_plan_and_no_rows(learner):
    learner.put("/api/profile", json={**PROFILE, "target_language": "hinglish"})
    assert generate(learner) == {"date": DAY, "generated": False, "tasks": [], "done": 0, "total": 0}
    assert task_count() == 0


# ---------- idempotency / no duplicates ----------
def test_generating_twice_is_a_noop(learner):
    first = generate(learner)
    second = generate(learner)
    assert first == second and [t["id"] for t in first["tasks"]] == [t["id"] for t in second["tasks"]]
    assert task_count() == 2


def test_many_repeated_calls_never_duplicate(learner):
    for _ in range(5):
        generate(learner)
    with db() as conn:
        dupes = conn.execute("SELECT COUNT(*) FROM (SELECT task_type, lesson_id, situation_id, topic_id, COUNT(*) c FROM daily_tasks GROUP BY 1, 2, 3, 4 HAVING c > 1)").fetchone()[0]
    assert dupes == 0 and task_count() == 2


def test_concurrent_generation_creates_one_plan(learner):
    user = uid("l@example.com")
    errors = []

    def run():
        try:
            plan_service.generate_plan(main.DB_PATH, user)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=run) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors or all("locked" in str(e) for e in errors)        # SQLite may make a writer wait; it must never make a duplicate
    assert task_count() == 2
    with db() as conn:
        assert conn.execute("SELECT COUNT(DISTINCT priority) FROM daily_tasks").fetchone()[0] == 2


def test_repository_insert_is_ignored_when_the_task_already_exists(learner):
    generate(learner)
    with connect(main.DB_PATH) as conn:
        t = conn.execute("SELECT user_id, language_id, plan_date, task_type, source, lesson_id FROM daily_tasks WHERE priority = 1").fetchone()
        again = repo.insert_task(conn, t["user_id"], t["language_id"], t["plan_date"], 5, t["task_type"], t["source"], t["lesson_id"], None, None, "2026-01-15 00:00:00")
        assert again is False                                                    # same task, other priority: refused by the unique index
        assert conn.execute("SELECT COUNT(*) FROM daily_tasks").fetchone()[0] == 2


def test_an_existing_plan_is_returned_without_recomputing_recommendations(learner, monkeypatch):
    """The once-per-day guarantee comes from the service, not only from the unique indexes that back it up."""
    generate(learner)

    def boom(*args, **kwargs):
        raise AssertionError("recommendations were recomputed for a day that already has a plan")

    monkeypatch.setattr(plan_service.recommendations, "build", boom)
    assert generate(learner)["total"] == 2 and generate(learner)["total"] == 2


def test_the_plan_does_not_reshuffle_during_the_day(learner):
    before = generate(learner)
    cycle_attempts(uid("l@example.com"), "food", [0] * 8)        # a weakness appears after the plan was made
    assert shape(generate(learner)) == shape(before)
    assert get_plan(learner)["tasks"] == before["tasks"]


def test_a_new_day_gets_a_fresh_plan_from_current_data(learner, monkeypatch):
    day1 = generate(learner)
    cycle_attempts(uid("l@example.com"), "food", [0] * 8)
    monkeypatch.setattr(clock, "today", lambda: "2026-01-16")
    assert get_plan(learner)["generated"] is False
    day2 = generate(learner)
    assert day2["date"] == "2026-01-16" and shape(day2)[0][2] == "review_topic" and shape(day2) != shape(day1)
    monkeypatch.setattr(clock, "today", lambda: DAY)
    assert shape(get_plan(learner)) == shape(day1)                # yesterday's plan is untouched
    assert task_count() == len(day1["tasks"]) + len(day2["tasks"])


def test_identical_learners_get_identical_plans(learner, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    for email in ("l@example.com", "b@example.com"):
        cycle_attempts(uid(email), "food", [0, 0, 0, 0, 1, 1])
    assert shape(generate(learner)) == shape(generate(client2))


def test_plans_are_per_language(learner):
    hindi = generate(learner)
    learner.put("/api/profile", json={**PROFILE, "target_language": "hinglish"})
    assert get_plan(learner)["tasks"] == [] and generate(learner)["tasks"] == []
    learner.put("/api/profile", json={**PROFILE, "target_language": "hi"})
    assert get_plan(learner)["tasks"] == hindi["tasks"]


# ---------- status ----------
def set_status(c, task_id, status):
    return c.post(f"/api/daily-plan/tasks/{task_id}/status", json={"status": status})


def test_mark_done_skipped_and_back(learner):
    t = generate(learner)["tasks"][0]
    done = set_status(learner, t["id"], "done").json()["task"]
    assert done["status"] == "done" and done["completed_at"]
    assert (get_plan(learner)["done"], get_plan(learner)["total"]) == (1, 2)
    skipped = set_status(learner, t["id"], "skipped").json()["task"]
    assert skipped["status"] == "skipped" and skipped["completed_at"] is None
    pending = set_status(learner, t["id"], "pending").json()["task"]
    assert pending["status"] == "pending" and pending["completed_at"] is None


@pytest.mark.parametrize("body", [{"status": "finished"}, {}, {"status": "done", "user_id": 1}, {"status": 1}])
def test_invalid_status_rejected(learner, body):
    t = generate(learner)["tasks"][0]
    assert learner.post(f"/api/daily-plan/tasks/{t['id']}/status", json=body).status_code == 422
    assert get_plan(learner)["tasks"][0]["status"] == "pending"


def test_unknown_task_404(learner):
    assert set_status(learner, 99999, "done").status_code == 404


def test_a_learner_cannot_touch_another_learners_tasks(learner, client2):
    mine = generate(learner)["tasks"][0]
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    assert set_status(client2, mine["id"], "done").status_code == 404
    assert get_plan(client2)["tasks"] == []                       # B sees nothing of A's plan
    assert get_plan(learner)["tasks"][0]["status"] == "pending"
    theirs = generate(client2)["tasks"][0]
    assert theirs["id"] != mine["id"] and set_status(learner, theirs["id"], "skipped").status_code == 404


# ---------- automatic completion ----------
def test_finishing_the_lesson_marks_its_task_done(learner):
    plan = generate(learner)
    assert plan["tasks"][0]["target"]["title"] == "Greetings"
    complete_lesson(learner, "greetings")
    after = get_plan(learner)
    assert [t["status"] for t in after["tasks"]] == ["done", "pending"] and after["tasks"][0]["completed_at"] and (after["done"], after["total"]) == (1, 2)


def test_finishing_the_situation_marks_its_task_done(learner):
    generate(learner)
    complete_situation(learner, "greetings")
    assert [t["status"] for t in get_plan(learner)["tasks"]] == ["pending", "done"]


def test_partial_progress_does_not_complete_a_task(learner):
    generate(learner)
    lesson = next(l for l in learner.get("/api/lessons").json()["lessons"] if l["slug"] == "greetings")
    ex = learner.get(f"/api/lessons/{lesson['id']}").json()["lesson"]["exercises"][0]
    learner.post(f"/api/exercises/{ex['id']}/attempts", json={"answer_id": ex["options"][0]["id"]})
    assert get_plan(learner)["done"] == 0


def test_work_done_before_the_plan_date_does_not_complete_a_task(learner, monkeypatch):
    monkeypatch.setattr(clock, "today", lambda: "2999-01-01")        # a plan for a day that has not happened yet
    plan = generate(learner)
    assert plan["tasks"][0]["target"]["title"] == "Greetings"
    complete_lesson(learner, "greetings")                             # done now, i.e. before that plan date
    assert all(t["status"] == "pending" for t in get_plan(learner)["tasks"])


def test_rating_the_topic_completes_a_confidence_checkin(learner):
    cycle_attempts(uid("l@example.com"), "food", [1, 1, 1])
    plan = generate(learner)
    checkin = next(t for t in plan["tasks"] if t["task_type"] == "confidence_checkin")
    assert checkin["target"]["slug"] == "food" and checkin["status"] == "pending"
    learner.post("/api/confidence", json={"topic": "food", "score": 75})
    after = next(t for t in get_plan(learner)["tasks"] if t["id"] == checkin["id"])
    assert after["status"] == "done" and after["completed_at"]
    learner.post("/api/confidence", json={"topic": "transport", "score": 75})            # rating another topic does not
    assert sum(t["status"] == "done" for t in get_plan(learner)["tasks"]) == 1


def test_manual_skip_is_not_overridden_by_auto_completion(learner):
    plan = generate(learner)
    set_status(learner, plan["tasks"][0]["id"], "skipped")
    complete_lesson(learner, "greetings")
    assert get_plan(learner)["tasks"][0]["status"] == "skipped"


# ---------- tasks reference real, available content ----------
def test_tasks_reference_available_content(learner):
    cycle_attempts(uid("l@example.com"), "food", [0] * 7)
    lessons = {l["id"] for l in learner.get("/api/lessons").json()["lessons"]}
    situations = {s["id"] for s in learner.get("/api/situations").json()["situations"]}
    for t in generate(learner)["tasks"]:
        if t["target"]["type"] == "lesson":
            assert t["target"]["id"] in lessons
        elif t["target"]["type"] == "situation":
            assert t["target"]["id"] in situations

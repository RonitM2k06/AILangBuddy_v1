"""Phase 13F: the dashboard must not contradict what learners themselves see. Six learners do real work through the real learner APIs; the admin figures are then
compared with the learner-facing ones (progress status, XP total) and with the exact number of requests the test made."""
from datetime import datetime, timezone

import pytest

from backend import main
from backend.admin import analytics
from backend.db import connect

from . import adm
from .adm import admin, learner_browser, ok  # noqa: F401


@pytest.fixture(autouse=True)
def real_clock(monkeypatch):
    monkeypatch.setattr(analytics, "utcnow", lambda: datetime.now(timezone.utc))        # the learner APIs stamp real UTC times


def answer_lesson(me, lesson_id, wrong_first=False, stop_after=None):
    """Answer a lesson's exercises through the API, reading the key from the database. Returns (attempts made, attempts correct)."""
    with connect(main.DB_PATH) as conn:
        exercises = conn.execute("SELECT id, kind FROM exercises WHERE lesson_id = ? ORDER BY sort_order", (lesson_id,)).fetchall()
        keys = {e["id"]: [dict(a) for a in conn.execute("SELECT id, answer_text, is_correct FROM exercise_answers WHERE exercise_id = ?", (e["id"],))] for e in exercises}
    made = correct = 0
    for n, e in enumerate(exercises):
        if stop_after is not None and n >= stop_after:
            break
        right = [a for a in keys[e["id"]] if a["is_correct"]]
        wrong = [a for a in keys[e["id"]] if not a["is_correct"]]
        def send(answer):
            body = {"answer_id": answer["id"]} if e["kind"] == "multiple_choice" else {"text": answer["answer_text"]}
            r = me.post(f"/api/exercises/{e['id']}/attempts", body)
            assert r.status_code == 200, r.text
            return r.json()["correct"]
        if wrong_first and n == 0 and e["kind"] == "multiple_choice":
            made += 1
            correct += send(wrong[0])
        made += 1
        correct += send(right[0])
    return made, correct


def test_admin_figures_agree_with_what_six_real_learners_did_and_saw(admin):
    with connect(main.DB_PATH) as conn:
        lesson_id = conn.execute("SELECT id FROM lessons WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0]
        n_ex = conn.execute("SELECT COUNT(*) FROM exercises WHERE lesson_id = ?", (lesson_id,)).fetchone()[0]
    people = [learner_browser(f"agree{i}@example.com") for i in range(6)]
    made = correct = 0
    for i, me in enumerate(people):
        if i < 5:                                            # five finish the lesson (the first of them stumbles once on the way)
            m, c = answer_lesson(me, lesson_id, wrong_first=(i == 0))
        else:                                                # one answers one exercise and stops
            m, c = answer_lesson(me, lesson_id, stop_after=1)
        made, correct = made + m, correct + c
    # what the learners see
    seen_completed = sum(1 for me in people for p in me.get("/api/progress/lessons").json()["progress"] if p["lesson_id"] == lesson_id and p["status"] == "completed")
    seen_started = sum(1 for me in people for p in me.get("/api/progress/lessons").json()["progress"] if p["lesson_id"] == lesson_id)
    xp_total = sum(me.get("/api/gamification").json()["xp"]["total"] for me in people)
    assert (seen_completed, seen_started) == (5, 6) and xp_total > 0
    # what the admin sees
    learning = ok(admin.get("/api/admin/analytics/learning"))
    assert learning["lesson_completion"] == {"numerator": seen_completed, "denominator": seen_started, "rate": round(seen_completed / seen_started, 4), "status": "ok"}
    assert learning["exercise_accuracy"] == {"numerator": correct, "denominator": made, "rate": round(correct / made, 4), "status": "ok"} and made > n_ex * 5
    engagement = ok(admin.get("/api/admin/analytics/engagement"))
    assert engagement["xp"]["xp_awarded"] == {"value": xp_total, "status": "ok"} and engagement["xp"]["learners_earning"] == {"value": 6, "status": "ok"}
    dash = ok(admin.get("/api/admin/dashboard"))
    assert dash["learners"]["total"]["value"] == 6 and dash["learners"]["active"]["value"] == 6 and dash["activity"]["dau"]["value"] == 6
    assert dash["distributions"]["language"]["buckets"] == [{"key": "hi", "label": "Hindi", "count": 6, "learners": 6, "status": "ok"}]
    # the evidence the admin figures rest on is exactly the rows the learner features wrote
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*), SUM(is_correct) FROM exercise_attempts").fetchone()[:] == (made, correct)


def test_listening_figures_agree_with_the_attempts_learners_made(admin):
    people = [learner_browser(f"listen{i}@example.com") for i in range(6)]
    with connect(main.DB_PATH) as conn:
        activities = [dict(r) for r in conn.execute("SELECT id FROM listening_activities ORDER BY id LIMIT 2")]
    made = right = 0
    for i, me in enumerate(people):
        for a in activities:
            with connect(main.DB_PATH) as conn:
                good, bad = adm.right_option(conn, a["id"]), adm.wrong_option(conn, a["id"])
            pick = good if (i + a["id"]) % 3 else bad
            r = me.post(f"/api/listening/{a['id']}/attempts", {"option_id": pick})
            assert r.status_code == 200, r.text
            made += 1
            right += r.json()["correct"]
    assert 0 < right < made
    assert ok(admin.get("/api/admin/analytics/learning"))["listening_accuracy"] == {"numerator": right, "denominator": made, "rate": round(right / made, 4), "status": "ok"}

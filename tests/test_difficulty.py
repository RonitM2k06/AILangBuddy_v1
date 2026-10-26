import pytest

from backend.personalization import difficulty, rules

from .conftest import register
from .pers import add_exercise_attempts, db, exercise_ids, uid

PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}


def attempts(*pairs):
    """Newest-first list from (correct, difficulty) pairs given oldest-first."""
    return [{"is_correct": c, "difficulty": d} for c, d in reversed(pairs)]


def rec(*pairs):
    return difficulty.recommend(attempts(*pairs))


# ---------- pure logic ----------
@pytest.mark.parametrize("n", [0, 1, 4])
def test_too_little_data_starts_at_the_easiest_level(n):
    r = rec(*[(1, 3)] * n)
    assert (r["recommended"], r["label"], r["reason_code"]) == (1, "easy", "not_enough_data")
    assert r["evidence"]["accuracy"] is None and f"{n} recent answers" in r["reason"]


@pytest.mark.parametrize("pairs,expected,code", [
    ([(1, 1)] * 8, 2, "step_up"),                                # perfect at easy  -> medium
    ([(1, 2)] * 8, 3, "step_up"),                                # perfect at medium -> hard
    ([(1, 3)] * 8, 3, "step_up"),                                # already hardest: capped
    ([(1, 2)] * 7 + [(0, 2)], 3, "step_up"),                     # 7/8 = 0.875
    ([(1, 2)] * 6 + [(0, 2)] * 2, 2, "stay"),                    # 6/8 = 0.75
    ([(1, 2)] * 4 + [(0, 2)] * 4, 2, "stay"),                    # 0.5 exactly is not "below 0.5"
    ([(1, 2)] * 3 + [(0, 2)] * 5, 1, "step_down"),               # 0.375 -> easier
    ([(0, 3)] * 8, 2, "step_down"),
    ([(0, 1)] * 8, 1, "step_down"),                              # already easiest: floored
    ([(1, 1)] * 4 + [(1, 3)] * 4, 3, "step_up"),                 # mean difficulty 2.0, perfect -> 3
    ([(1, 1)] * 5 + [(1, 3)] * 3, 3, "step_up"),                 # mean 1.75 rounds to 2 -> step up to 3
    ([(1, 1)] * 5, 2, "step_up"),                                # exactly the minimum window: 5/5
    ([(1, 2)] * 4 + [(0, 2)], 3, "step_up"),                     # 4/5 = 0.80 exactly is enough to step up
])
def test_recommendation_rules(pairs, expected, code):
    r = rec(*pairs)
    assert (r["recommended"], r["reason_code"]) == (expected, code)
    assert r["label"] == rules.DIFFICULTY_LABELS[expected] and 1 <= r["recommended"] <= 3


def test_only_the_most_recent_window_is_used():
    old_failures = [(0, 2)] * 6
    recent_successes = [(1, 2)] * rules.DIFFICULTY_WINDOW
    r = rec(*old_failures, *recent_successes)
    assert r["evidence"]["attempts"] == rules.DIFFICULTY_WINDOW and r["evidence"]["correct"] == rules.DIFFICULTY_WINDOW and r["recommended"] == 3


def test_recommendation_is_explainable():
    r = rec(*([(1, 2)] * 7 + [(0, 2)]))
    assert r["reason"] == "You got 7 of 8 right at about medium difficulty, so try hard."
    assert r["evidence"] == {"attempts": 8, "correct": 7, "accuracy": 0.88, "working_level": 2, "scale": {"min": 1, "max": 3}}
    assert "hardest level" in rec(*([(1, 3)] * 8))["reason"] and "easiest level" in rec(*([(0, 1)] * 8))["reason"]


def test_deterministic():
    data = attempts(*([(1, 1)] * 3 + [(0, 2)] * 5))
    assert difficulty.recommend(data) == difficulty.recommend(list(data))


# ---------- API ----------
@pytest.fixture
def learner(client):
    register(client, "l@example.com")
    client.put("/api/profile", json=PROFILE)
    return client


def test_new_learner_starts_easy(learner):
    d = learner.get("/api/difficulty").json()["difficulty"]
    assert (d["recommended"], d["reason_code"]) == (1, "not_enough_data")


def test_api_uses_the_seeded_exercise_difficulty_of_the_answered_exercises(learner):
    user = uid("l@example.com")
    mc = exercise_ids("food", "multiple_choice")[0]            # difficulty 1
    add_exercise_attempts(user, mc, [1] * 6)
    d = learner.get("/api/difficulty").json()["difficulty"]
    assert (d["recommended"], d["reason_code"], d["evidence"]["working_level"]) == (2, "step_up", 1)
    add_exercise_attempts(user, exercise_ids("food", "translation")[0], [1] * 8, start=10)   # now 8 perfect at translation (3)
    d = learner.get("/api/difficulty").json()["difficulty"]
    assert (d["recommended"], d["evidence"]["working_level"]) == (3, 3)


def test_api_steps_down_after_struggling(learner):
    add_exercise_attempts(uid("l@example.com"), exercise_ids("food", "fill_blank")[0], [0, 0, 0, 0, 1, 0])
    d = learner.get("/api/difficulty").json()["difficulty"]
    assert (d["recommended"], d["reason_code"], d["evidence"]["working_level"]) == (1, "step_down", 2)


def test_situation_attempts_do_not_affect_the_exercise_difficulty(learner):
    from .pers import add_step_attempts, step_ids
    add_step_attempts(uid("l@example.com"), step_ids("food", "choose_response")[0], [1] * 10)
    assert learner.get("/api/difficulty").json()["difficulty"]["reason_code"] == "not_enough_data"


def test_other_learners_do_not_affect_my_recommendation(learner, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    add_exercise_attempts(uid("b@example.com"), exercise_ids("food", "multiple_choice")[0], [1] * 8)
    assert learner.get("/api/difficulty").json()["difficulty"]["reason_code"] == "not_enough_data"
    assert client2.get("/api/difficulty").json()["difficulty"]["reason_code"] == "step_up"


def test_recommending_never_changes_stored_content(learner):
    with db() as conn:
        snapshot = lambda: (conn.execute("SELECT id, kind, prompt, explanation, difficulty FROM exercises ORDER BY id").fetchall(),
                            conn.execute("SELECT id, answer_text, is_correct FROM exercise_answers ORDER BY id").fetchall())
        before = [[tuple(r) for r in part] for part in snapshot()]
    add_exercise_attempts(uid("l@example.com"), exercise_ids("food", "multiple_choice")[0], [1] * 8)
    for _ in range(3):
        learner.get("/api/difficulty")
        learner.get("/api/recommendations")
    with db() as conn:
        after = [[tuple(r) for r in part] for part in (conn.execute("SELECT id, kind, prompt, explanation, difficulty FROM exercises ORDER BY id").fetchall(),
                                                       conn.execute("SELECT id, answer_text, is_correct FROM exercise_answers ORDER BY id").fetchall())]
    assert before == after

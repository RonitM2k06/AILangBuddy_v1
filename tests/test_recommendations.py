import pytest

from backend.personalization import rules

from .conftest import register
from .pers import add_exercise_attempts, cycle_attempts, exercise_ids, uid

PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}


@pytest.fixture
def learner(client):
    register(client, "l@example.com")
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


def recs(c):
    r = c.get("/api/recommendations")
    assert r.status_code == 200
    return r.json()["recommendations"]


def kinds(c):
    return [r["kind"] for r in recs(c)]


def targets(c):
    return [(r["kind"], r["target"]["type"], r["target"]["title"]) for r in recs(c)]


# ---------- nothing invented ----------
def test_new_learner_only_gets_a_starting_point(learner):
    assert targets(learner) == [("next_lesson", "lesson", "Greetings"), ("next_situation", "situation", "Meet your landlady")]
    body = learner.get("/api/recommendations").json()
    assert body["next_activity"] == body["recommendations"][0]
    assert [r["priority"] for r in body["recommendations"]] == [1, 2]
    assert all(r["evidence"] == {} for r in body["recommendations"])          # no data, so no data-based claims


def test_no_content_means_no_recommendations(learner):
    learner.put("/api/profile", json={**PROFILE, "target_language": "hinglish"})
    body = learner.get("/api/recommendations").json()
    assert body["recommendations"] == [] and body["next_activity"] is None
    assert body["difficulty"]["reason_code"] == "not_enough_data"


def test_good_performance_produces_no_remedial_advice(learner):
    cycle_attempts(uid("l@example.com"), "food", [1] * 8)
    assert [k for k in kinds(learner) if k.startswith("review")] == []
    assert kinds(learner) == ["confidence_checkin", "next_lesson", "next_situation"]   # practised 8 times, never rated


def test_a_single_mistake_does_not_trigger_review(learner):
    cycle_attempts(uid("l@example.com"), "food", [0, 1, 1, 1, 1, 1, 1])
    assert [k for k in kinds(learner) if k.startswith("review")] == []


# ---------- each rule, from real data ----------
def test_unfinished_lesson_is_continued_first(learner):
    """Answering one exercise through the real API starts the lesson."""
    lesson = next(l for l in learner.get("/api/lessons").json()["lessons"] if l["slug"] == "transport")
    ex = learner.get(f"/api/lessons/{lesson['id']}").json()["lesson"]["exercises"][0]
    learner.post(f"/api/exercises/{ex['id']}/attempts", json={"answer_id": ex["options"][0]["id"]})
    r = recs(learner)
    assert r[0]["kind"] == "continue_lesson" and r[0]["target"] == {"type": "lesson", "id": lesson["id"], "title": "Transport"}
    assert "of 3 exercises right in “Transport”" in r[0]["reason"] and r[0]["evidence"]["exercises_total"] == 3
    assert ("next_lesson", "lesson", "Greetings") in targets(learner)          # the next unstarted lesson, not the started one


def test_unfinished_situation_is_continued(learner):
    sit = next(s for s in learner.get("/api/situations").json()["situations"] if s["slug"] == "emergency")
    step = learner.get(f"/api/situations/{sit['id']}").json()["situation"]["steps"][0]
    learner.post(f"/api/situations/{sit['id']}/steps/{step['id']}/responses", json={})
    r = recs(learner)[0]
    assert (r["kind"], r["target"]["title"]) == ("continue_situation", "Getting help") and "step 2 of 7" in r["reason"]
    assert r["evidence"] == {"steps_completed": 1, "steps_total": 7}


def test_weak_topic_is_reviewed_first(learner):
    cycle_attempts(uid("l@example.com"), "transport", [0, 0, 0, 0, 1, 1])
    first = recs(learner)[0]
    assert first["kind"] == "review_topic" and first["target"]["title"] == "Transport" and first["topic"]["slug"] == "transport"
    assert first["evidence"] == {"severity": "high", "attempts": 6, "incorrect": 4, "accuracy": 0.33}
    assert "You answered 2 of your last 6 Transport questions correctly" in first["reason"]


def test_repeated_item_errors_point_at_the_lesson_containing_the_item(learner):
    add_exercise_attempts(uid("l@example.com"), exercise_ids("food", "translation")[0], [0, 0, 0])
    r = recs(learner)
    assert (r[0]["kind"], r[0]["target"]["title"]) == ("review_item", "Food")
    assert "Ek plate chhole bhature dena." in r[0]["reason"] and "It is in “Food”" in r[0]["reason"]
    assert r[0]["evidence"]["incorrect"] == 3


def test_one_target_is_recommended_once(learner):
    """A weak topic AND weak items in it all point at the same lesson: it appears a single time, with the strongest reason."""
    cycle_attempts(uid("l@example.com"), "food", [0] * 7)
    assert [t for t in targets(learner) if t[2] == "Food" and t[1] == "lesson"] == [("review_topic", "lesson", "Food")]


def test_low_confidence_points_at_a_situation_in_that_topic(learner):
    learner.post("/api/confidence", json={"topic": "shopping", "score": 30})
    r = recs(learner)[0]
    assert (r["kind"], r["target"]["type"], r["target"]["title"]) == ("low_confidence", "situation", "Bargain at Sarojini")
    assert r["evidence"] == {"confidence": 30} and "30%" in r["reason"] and r["topic"]["slug"] == "shopping"


@pytest.mark.parametrize("score,expected", [(50, True), (51, False), (100, False)])
def test_low_confidence_threshold(learner, score, expected):
    learner.post("/api/confidence", json={"topic": "shopping", "score": score})
    assert ("low_confidence" in kinds(learner)) is expected


def test_only_the_latest_confidence_counts(learner):
    learner.post("/api/confidence", json={"topic": "shopping", "score": 10})
    learner.post("/api/confidence", json={"topic": "shopping", "score": 90})
    assert "low_confidence" not in kinds(learner)


def test_confidence_checkin_for_practised_but_unrated_topics(learner):
    cycle_attempts(uid("l@example.com"), "food", [1, 1, 1])
    r = next(x for x in recs(learner) if x["kind"] == "confidence_checkin")
    assert r["target"] == {"type": "topic", "id": r["target"]["id"], "slug": "food", "title": "Food"} and "practised Food 3 times" in r["reason"]
    learner.post("/api/confidence", json={"topic": "food", "score": 80})
    assert "confidence_checkin" not in kinds(learner)                       # rated now
    cycle_attempts(uid("l@example.com"), "transport", [1, 1])               # only 2 attempts: too early to ask
    assert "confidence_checkin" not in kinds(learner)


# ---------- ordering, limits, determinism ----------
def test_priority_order_across_rules(learner):
    user = uid("l@example.com")
    cycle_attempts(user, "transport", [0, 0, 0, 0, 1, 1])                   # weak topic
    learner.post("/api/confidence", json={"topic": "shopping", "score": 20})  # low confidence
    order = kinds(learner)
    assert order[0] == "review_topic"
    assert order.index("review_topic") < order.index("low_confidence") < order.index("confidence_checkin") < order.index("next_lesson") < order.index("next_situation")
    assert [r["priority"] for r in recs(learner)] == list(range(1, len(order) + 1))


def test_weaknesses_are_recommended_most_severe_first(learner):
    user = uid("l@example.com")
    cycle_attempts(user, "food", [0, 0, 0, 1, 1, 1])                         # low
    cycle_attempts(user, "shopping", [0] * 8)                                # high
    cycle_attempts(user, "directions", [0, 0, 0, 0, 1, 1, 1, 1, 0, 0])       # medium
    assert [r["target"]["title"] for r in recs(learner) if r["kind"] == "review_topic"] == ["Shopping", "Directions", "Food"]


def test_recommendations_are_capped(learner):
    user = uid("l@example.com")
    for slug in ("transport", "food", "shopping", "directions", "college", "smalltalk", "greetings"):
        cycle_attempts(user, slug, [0] * 7)
    r = recs(learner)
    assert len(r) == rules.MAX_RECOMMENDATIONS and len({(x["target"]["type"], x["target"]["id"]) for x in r}) == len(r)
    assert [x["priority"] for x in r] == list(range(1, 7))


def test_lesson_targets_carry_the_suggested_difficulty(learner):
    add_exercise_attempts(uid("l@example.com"), exercise_ids("food", "multiple_choice")[0], [1] * 6)
    body = learner.get("/api/recommendations").json()
    suggested = body["difficulty"]["recommended"]
    assert suggested == 2
    for r in body["recommendations"]:
        assert ("suggested_difficulty" in r) == (r["target"]["type"] == "lesson")
        if r["target"]["type"] == "lesson":
            assert r["suggested_difficulty"] == suggested
    assert learner.get("/api/difficulty").json()["difficulty"] == body["difficulty"]


def test_deterministic_and_stable_between_calls(learner):
    cycle_attempts(uid("l@example.com"), "food", [0, 0, 0, 0, 1, 1])
    assert learner.get("/api/recommendations").json() == learner.get("/api/recommendations").json()


def test_identical_learners_get_identical_recommendations(learner, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    for email in ("l@example.com", "b@example.com"):
        cycle_attempts(uid(email), "food", [0, 0, 0, 0, 1, 1])
    assert recs(learner) == recs(client2)


def test_other_learners_data_is_never_used(learner, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    cycle_attempts(uid("b@example.com"), "food", [0] * 8)
    client2.post("/api/confidence", json={"topic": "shopping", "score": 5})
    assert kinds(learner) == ["next_lesson", "next_situation"]
    assert kinds(client2)[0] == "review_topic"


def test_recommendations_refresh_as_the_learner_improves(learner):
    user = uid("l@example.com")
    n = cycle_attempts(user, "food", [0, 0, 0, 0, 1, 1])
    assert kinds(learner)[0] == "review_topic"
    cycle_attempts(user, "food", [1] * 10, start=n)
    assert "review_topic" not in kinds(learner) and "review_item" not in kinds(learner)


def test_recommended_targets_are_always_available_to_the_learner(learner):
    cycle_attempts(uid("l@example.com"), "food", [0] * 7)
    lessons = {l["id"] for l in learner.get("/api/lessons").json()["lessons"]}
    situations = {s["id"] for s in learner.get("/api/situations").json()["situations"]}
    for r in recs(learner):
        if r["target"]["type"] == "lesson":
            assert r["target"]["id"] in lessons
        if r["target"]["type"] == "situation":
            assert r["target"]["id"] in situations

"""Listening attempts are performance evidence for the existing personalization rules (the two attempt views gained a
listening branch; no rule was redesigned)."""
import pytest

from .conftest import register
from .lis import answer_right, answer_wrong, db
from .pers import cycle_attempts, uid

PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}


@pytest.fixture
def learner(client):
    register(client, "l@example.com")
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


def weak(c):
    return c.get("/api/weaknesses").json()["weaknesses"]


def topic_weak(c, slug):
    return [w for w in weak(c) if w["rule"] == "low_topic_accuracy" and w["topic"]["slug"] == slug]


def item_weak(c):
    return [w for w in weak(c) if w["rule"] == "repeated_item_errors"]


def test_listening_attempts_are_visible_to_the_personalization_views(learner):
    answer_wrong(learner, "transport-meaning")
    answer_right(learner, "transport-phrase")
    with db() as conn:
        rows = conn.execute("SELECT source, kind, is_correct FROM learner_attempts ORDER BY attempt_id").fetchall()
        topics = conn.execute("SELECT t.slug, v.source FROM learner_attempt_topics v JOIN topics t ON t.id=v.topic_id ORDER BY v.attempt_id").fetchall()
    assert [tuple(r) for r in rows] == [("listening", "listening", 0), ("listening", "listening", 1)]
    assert [tuple(r) for r in topics] == [("transport", "listening")] * 2


def test_one_or_two_listening_mistakes_are_not_a_weakness(learner):
    answer_wrong(learner, "transport-meaning")
    assert weak(learner) == []
    answer_wrong(learner, "transport-meaning")
    assert weak(learner) == []


def test_repeated_listening_errors_on_one_phrase_are_an_item_weakness(learner):
    for _ in range(3):
        answer_wrong(learner, "transport-meaning")
    (w,) = item_weak(learner)
    assert w["item"]["pronunciation"] == "Kitne paise honge?" and (w["attempts"], w["incorrect"], w["severity"]) == (3, 3, "low")
    assert topic_weak(learner, "transport") == []            # three answers are too few for a topic verdict


def test_a_listening_slump_in_a_topic_is_a_topic_weakness(learner):
    for _ in range(3):
        answer_wrong(learner, "transport-meaning")
        answer_wrong(learner, "transport-phrase")
    (w,) = topic_weak(learner, "transport")
    assert (w["attempts"], w["incorrect"], w["severity"]) == (6, 6, "high")
    assert w["explanation"] == "You answered 0 of your last 6 Transport questions correctly."


def test_correct_listening_answers_never_create_weaknesses(learner):
    for _ in range(8):
        answer_right(learner, "transport-meaning")
    assert weak(learner) == []


def test_recovering_by_listening_resolves_the_weakness(learner):
    for _ in range(3):
        answer_wrong(learner, "transport-meaning")
    assert item_weak(learner)
    answer_right(learner, "transport-meaning")              # the latest answer on the phrase is now right
    assert item_weak(learner) == []


def test_listening_and_lesson_evidence_combine_in_a_topic(learner):
    user = uid("l@example.com")
    n = cycle_attempts(user, "transport", [0, 0, 0])        # three wrong lesson answers
    for _ in range(3):
        answer_wrong(learner, "transport-phrase")          # three wrong listening answers
    (w,) = topic_weak(learner, "transport")
    assert (w["attempts"], w["incorrect"]) == (6, 6)


def test_other_learners_listening_mistakes_do_not_count(learner, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    for _ in range(6):
        answer_wrong(client2, "transport-meaning")
    assert weak(learner) == [] and [w["rule"] for w in weak(client2)].count("low_topic_accuracy") == 1


def test_topic_performance_includes_listening(learner):
    answer_right(learner, "food-meaning")
    answer_wrong(learner, "food-phrase")
    row = next(t for t in learner.get("/api/confidence").json()["topics"] if t["topic"]["slug"] == "food")
    assert row["performance"] == {"attempts": 2, "correct": 1, "accuracy": 0.5} and row["confidence"] is None


def test_listening_feeds_recommendations_through_the_existing_rules(learner):
    for _ in range(3):
        answer_wrong(learner, "transport-meaning")
        answer_wrong(learner, "transport-phrase")
    first = learner.get("/api/recommendations").json()["recommendations"][0]
    assert first["kind"] == "review_topic" and first["target"]["title"] == "Transport"


def test_adaptive_difficulty_still_reads_only_lesson_exercises(learner):
    for _ in range(10):
        answer_right(learner, "food-meaning")
    d = learner.get("/api/difficulty").json()["difficulty"]
    assert d["reason_code"] == "not_enough_data" and d["evidence"]["attempts"] == 0


def test_views_keep_reporting_lessons_and_situations_unchanged(learner):
    user = uid("l@example.com")
    cycle_attempts(user, "food", [0, 0, 0])
    with db() as conn:
        sources = {r[0] for r in conn.execute("SELECT DISTINCT source FROM learner_attempts")}
    assert sources == {"lesson"}
    assert weak(learner) == []                               # three wrong answers spread over three exercises: no pattern yet

import pytest

from backend.personalization import clock

from .conftest import register
from .pers import cycle_attempts, db, uid

PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}


@pytest.fixture
def learner(client):
    register(client, "l@example.com")
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


def record(c, **body):
    return c.post("/api/confidence", json=body)


def overview(c):
    return c.get("/api/confidence").json()


def topic_row(c, slug):
    return next(t for t in overview(c)["topics"] if t["topic"]["slug"] == slug)


# ---------- recording ----------
def test_record_topic_confidence(learner):
    r = record(learner, topic="food", score=70)
    assert r.status_code == 201
    rec = r.json()["confidence"]
    assert rec["dimension"] == {"type": "topic", "slug": "food", "name": "Food", "icon": "🍛"}
    assert (rec["score"], rec["source"], rec["lesson_id"], rec["situation_id"]) == (70, "self_report", None, None)
    assert rec["recorded_at"] and "user" not in str(rec)


def test_record_skill_confidence(learner):
    rec = record(learner, skill="grammar", score=35).json()["confidence"]
    assert rec["dimension"] == {"type": "skill", "slug": "grammar", "name": "Grammar"} and rec["score"] == 35


@pytest.mark.parametrize("score", [0, 1, 50, 99, 100])
def test_score_boundaries_accepted(learner, score):
    assert record(learner, topic="food", score=score).status_code == 201


@pytest.mark.parametrize("body", [
    {"topic": "food", "score": -1}, {"topic": "food", "score": 101}, {"topic": "food", "score": 50.5}, {"topic": "food", "score": "high"},
    {"topic": "food"}, {"score": 50},                                              # missing score / dimension
    {"topic": "food", "skill": "grammar", "score": 50},                            # both dimensions
    {"topic": "nope", "score": 50}, {"skill": "speaking", "score": 50},            # unknown (speaking does not exist yet)
    {"topic": "food", "score": 50, "source": "guess"},
    {"topic": "food", "score": 50, "user_id": 1}, {"topic": "food", "score": 50, "language": "es"},   # the client never chooses the user/language
])
def test_invalid_requests_rejected_and_nothing_stored(learner, body):
    assert record(learner, **body).status_code == 422
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM confidence_scores").fetchone()[0] == 0


def test_topic_without_available_content_rejected(learner):
    with db() as conn:
        conn.execute("INSERT INTO topics(slug, name, icon) VALUES ('workplace', 'Workplace', '💼')")
    assert record(learner, topic="workplace", score=50).status_code == 422


def test_source_and_context_must_agree(learner):
    lesson = learner.get("/api/lessons").json()["lessons"][0]["id"]
    situation = learner.get("/api/situations").json()["situations"][0]["id"]
    assert record(learner, topic="food", score=50, source="lesson", lesson_id=lesson).json()["confidence"]["lesson_id"] == lesson
    assert record(learner, topic="food", score=50, source="situation", situation_id=situation).json()["confidence"]["situation_id"] == situation
    for bad in ({"source": "lesson"}, {"source": "lesson", "lesson_id": lesson, "situation_id": situation}, {"source": "situation"},
                {"source": "self_report", "lesson_id": lesson}, {"source": "lesson", "lesson_id": 9999},
                {"source": "situation", "situation_id": 9999}, {"source": "situation", "lesson_id": lesson}):
        assert record(learner, topic="food", score=50, **bad).status_code == 422, bad


def test_lesson_context_must_be_visible_to_the_learner(learner):
    lesson = learner.get("/api/lessons").json()["lessons"][0]["id"]
    with db() as conn:
        conn.execute("UPDATE lessons SET status='draft' WHERE id=?", (lesson,))
    assert record(learner, topic="food", score=50, source="lesson", lesson_id=lesson).status_code == 422


# ---------- retrieval ----------
def test_overview_before_any_report(learner):
    o = overview(learner)
    assert o["overall"] is None
    assert [t["topic"]["slug"] for t in o["topics"]] == ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk", "emergency"]
    assert all(t["confidence"] is None and t["performance"] is None for t in o["topics"])
    assert [s["skill"]["code"] for s in o["skills"]] == ["vocabulary", "grammar", "conversation"] and all(s["confidence"] is None for s in o["skills"])


def test_latest_report_is_the_current_confidence_and_history_is_kept(learner, monkeypatch):
    for i, score in enumerate([30, 55, 80]):
        monkeypatch.setattr(clock, "now", lambda i=i: f"2026-09-30 10:0{i}:00")
        record(learner, topic="food", score=score)
    assert topic_row(learner, "food")["confidence"] == {"score": 80, "source": "self_report", "recorded_at": "2026-09-30 10:02:00"}
    history = learner.get("/api/confidence/history?topic=food").json()["history"]
    assert [h["score"] for h in history] == [80, 55, 30]                                        # newest first
    assert learner.get("/api/confidence/history").json()["history"] == history


def test_reports_in_the_same_second_resolve_by_insertion_order(learner, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: "2026-09-30 10:00:00")
    record(learner, topic="food", score=10)
    record(learner, topic="food", score=90)
    assert topic_row(learner, "food")["confidence"]["score"] == 90


def test_overall_is_the_mean_of_the_latest_topic_scores_only(learner):
    record(learner, topic="food", score=20)
    record(learner, topic="food", score=60)           # replaces 20
    record(learner, topic="transport", score=80)
    record(learner, skill="grammar", score=0)          # skills are not part of the topic mean
    assert overview(learner)["overall"] == 70


def test_history_filters_and_limit(learner):
    for s in (10, 20, 30):
        record(learner, topic="food", score=s)
    record(learner, skill="grammar", score=99)
    assert [h["score"] for h in learner.get("/api/confidence/history?skill=grammar").json()["history"]] == [99]
    assert len(learner.get("/api/confidence/history?topic=food&limit=2").json()["history"]) == 2
    assert len(learner.get("/api/confidence/history").json()["history"]) == 4
    for bad in ("?topic=food&skill=grammar", "?topic=nope", "?skill=nope", "?limit=0", "?limit=500"):
        assert learner.get("/api/confidence/history" + bad).status_code == 422, bad


# ---------- confidence is not performance ----------
def test_confidence_and_performance_are_reported_separately(learner):
    cycle_attempts(uid("l@example.com"), "food", [0, 0, 0, 1, 1, 1, 1, 0])        # 4/8 correct: poor recent accuracy
    record(learner, topic="food", score=95)                                        # ...but the learner feels very confident
    row = topic_row(learner, "food")
    assert row["confidence"]["score"] == 95
    assert row["performance"] == {"attempts": 8, "correct": 4, "accuracy": 0.5}    # from attempts, untouched by the self-report


def test_recording_confidence_does_not_change_performance_or_weaknesses(learner):
    cycle_attempts(uid("l@example.com"), "food", [0, 0, 0, 0, 1, 1])
    before = (topic_row(learner, "food")["performance"], learner.get("/api/weaknesses").json())
    for score in (0, 100):
        record(learner, topic="food", score=score)
    assert (topic_row(learner, "food")["performance"], learner.get("/api/weaknesses").json()) == before


def test_performance_is_none_without_attempts_even_when_confidence_exists(learner):
    record(learner, topic="shopping", score=40)
    row = topic_row(learner, "shopping")
    assert row["confidence"]["score"] == 40 and row["performance"] is None


def test_performance_uses_the_recent_window(learner):
    cycle_attempts(uid("l@example.com"), "food", [1] * 5 + [0] * 10)               # 15 answers; last 10 are all wrong
    assert topic_row(learner, "food")["performance"] == {"attempts": 10, "correct": 0, "accuracy": 0.0}


# ---------- scoping ----------
def test_confidence_is_private_to_the_learner(learner, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    record(learner, topic="food", score=90)
    assert topic_row(client2, "food")["confidence"] is None
    assert overview(client2)["overall"] is None
    assert client2.get("/api/confidence/history").json()["history"] == []
    record(client2, topic="food", score=10)
    assert topic_row(learner, "food")["confidence"]["score"] == 90
    assert [h["score"] for h in client2.get("/api/confidence/history").json()["history"]] == [10]


def test_the_user_cannot_be_chosen_by_the_client(learner):
    record(learner, topic="food", score=50)
    assert learner.get("/api/confidence?user_id=1").json()["topics"][2]["confidence"]["score"] == 50   # query param ignored: still own data
    with db() as conn:
        demo = conn.execute("SELECT id FROM users WHERE handle='demo-alex'").fetchone()[0]
        assert conn.execute("SELECT COUNT(*) FROM confidence_scores WHERE user_id=?", (demo,)).fetchone()[0] == 0


def test_confidence_is_scoped_to_the_target_language(learner):
    record(learner, topic="food", score=70)
    learner.put("/api/profile", json={**PROFILE, "target_language": "hinglish"})
    assert overview(learner)["topics"] == []                      # no Hinglish content yet
    assert learner.get("/api/confidence/history").json()["history"] == []
    learner.put("/api/profile", json={**PROFILE, "target_language": "hi"})
    assert topic_row(learner, "food")["confidence"]["score"] == 70 # still there for Hindi

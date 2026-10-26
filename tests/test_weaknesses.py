import pytest

from backend.personalization import clock, rules

from .conftest import PASSWORD, register
from .pers import add_exercise_attempts, add_step_attempts, cycle_attempts, db, exercise_ids, step_ids, ts, uid

PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}


@pytest.fixture
def learner(client):
    register(client, "l@example.com")
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


def weaknesses(c):
    r = c.get("/api/weaknesses")
    assert r.status_code == 200
    return r.json()["weaknesses"]


def topic_weak(c, slug):
    return [w for w in weaknesses(c) if w["rule"] == "low_topic_accuracy" and w["topic"]["slug"] == slug]


# ---------- no false positives ----------
def test_new_learner_has_no_weaknesses(learner):
    assert weaknesses(learner) == []


@pytest.mark.parametrize("results", [
    [0], [0, 0], [0, 0, 0, 0, 0],          # fewer than TOPIC_MIN_ATTEMPTS answers, even if all wrong
    [1] * 10, [1, 1, 1, 1, 1, 1, 0],       # one slip among many
    [0, 1, 1, 1, 1, 1],                    # a single mistake
])
def test_a_few_mistakes_do_not_make_a_weakness(learner, results):
    cycle_attempts(uid("l@example.com"), "food", results)
    assert weaknesses(learner) == []


def test_one_wrong_answer_on_one_item_is_not_an_item_weakness(learner):
    add_exercise_attempts(uid("l@example.com"), exercise_ids("food")[0], [0])
    assert weaknesses(learner) == []


def test_two_wrong_answers_on_one_item_are_not_enough(learner):
    add_exercise_attempts(uid("l@example.com"), exercise_ids("food")[0], [0, 0])
    assert weaknesses(learner) == []


def test_learn_phrase_acknowledgements_are_not_evidence(learner):
    add_step_attempts(uid("l@example.com"), step_ids("food", "learn_phrase")[0], [0] * 10)   # even recorded as wrong
    assert weaknesses(learner) == []


def test_accuracy_at_the_threshold_is_not_a_weakness(learner):
    cycle_attempts(uid("l@example.com"), "food", [1, 1, 1, 0, 0, 1, 1, 1, 0, 0])   # 6/10 = 0.60, the threshold itself
    assert topic_weak(learner, "food") == []


# ---------- topic rule ----------
@pytest.mark.parametrize("results,severity,correct", [
    ([0, 0, 0, 1, 1, 1], "low", 3),                      # 0.50
    ([1, 0, 1, 0, 1, 0, 1, 0, 1, 0], "low", 5),          # 0.50 over 10
    ([0, 0, 0, 0, 1, 1, 1, 1, 0, 0], "medium", 4),      # 0.40
    ([0, 0, 0, 0, 1, 1], "high", 2),                     # 0.33
    ([0] * 10, "high", 0),
])
def test_low_topic_accuracy_and_severity(learner, results, severity, correct):
    cycle_attempts(uid("l@example.com"), "food", results)
    (w,) = topic_weak(learner, "food")
    assert w["severity"] == severity and (w["attempts"], w["incorrect"]) == (len(results), len(results) - correct)
    assert w["accuracy"] == round(correct / len(results), 2)
    assert w["explanation"] == f"You answered {correct} of your last {len(results)} Food questions correctly."
    assert set(w["topic"]) == {"slug", "name", "icon"} and w["rule"] == "low_topic_accuracy"


def test_only_the_most_recent_window_counts(learner):
    user = uid("l@example.com")
    nxt = cycle_attempts(user, "food", [0] * 8)                      # old mistakes
    cycle_attempts(user, "food", [1] * 10, start=nxt)                # then ten correct answers
    assert topic_weak(learner, "food") == []
    # ...and the reverse: old successes do not hide a recent slump
    user2 = uid("l@example.com")
    cycle_attempts(user2, "transport", [1] * 20, start=100)
    cycle_attempts(user2, "transport", [0] * 6, start=200)
    (w,) = topic_weak(learner, "transport")
    assert w["attempts"] == rules.TOPIC_WINDOW and w["incorrect"] == 6


def test_situation_attempts_count_toward_their_topic(learner):
    user = uid("l@example.com")
    steps = step_ids("shopping", "choose_response") + step_ids("shopping", "conversation")
    n = 0
    for i in range(6):
        n = add_step_attempts(user, steps[i % 2], [0], start=n)
    (w,) = topic_weak(learner, "shopping")
    assert (w["attempts"], w["incorrect"]) == (6, 6) and w["severity"] == "high"


def test_lessons_and_situations_in_the_same_topic_are_combined(learner):
    user = uid("l@example.com")
    n = cycle_attempts(user, "food", [0, 0, 0])                                      # 3 wrong in the lesson
    add_step_attempts(user, step_ids("food", "choose_response")[0], [0, 1, 1], start=n)   # 1 wrong, 2 right in the situation
    (w,) = topic_weak(learner, "food")
    assert (w["attempts"], w["incorrect"]) == (6, 4)


def test_topics_are_judged_independently(learner):
    user = uid("l@example.com")
    cycle_attempts(user, "food", [0, 0, 0, 0, 1, 1])
    cycle_attempts(user, "transport", [1] * 8)
    assert [w["topic"]["slug"] for w in weaknesses(learner)] == ["food"]


# ---------- item rule ----------
def item_weak(c):
    return [w for w in weaknesses(c) if w["rule"] == "repeated_item_errors"]


def test_repeated_errors_on_the_same_item(learner):
    ex = exercise_ids("food", "translation")[0]
    add_exercise_attempts(uid("l@example.com"), ex, [0, 0, 0])
    (w,) = item_weak(learner)
    assert w["severity"] == "low" and (w["attempts"], w["incorrect"]) == (3, 3)
    assert w["item"]["pronunciation"] == "Ek plate chhole bhature dena." and w["item"]["meaning"]
    assert "wrongly 3 times out of 3" in w["explanation"] and "still wrong" in w["explanation"]
    assert topic_weak(learner, "food") == []          # three answers are too few for a topic verdict


@pytest.mark.parametrize("wrong,severity", [(3, "low"), (4, "medium"), (5, "high"), (9, "high")])
def test_item_severity_grows_with_repeated_errors(learner, wrong, severity):
    add_exercise_attempts(uid("l@example.com"), exercise_ids("food", "translation")[0], [0] * wrong)
    assert item_weak(learner)[0]["severity"] == severity


def test_item_weakness_needs_the_latest_answer_to_still_be_wrong(learner):
    add_exercise_attempts(uid("l@example.com"), exercise_ids("food", "translation")[0], [0, 0, 0, 1])   # learned it in the end
    assert item_weak(learner) == []


def test_item_errors_across_lessons_and_situations_add_up(learner):
    """'Main kho gaya hoon' is tested by a translate step only in the Emergency situation; errors there count for the item."""
    add_step_attempts(uid("l@example.com"), step_ids("emergency", "translate")[0], [0, 0, 0])
    (w,) = item_weak(learner)
    assert w["item"]["pronunciation"] == "Main kho gaya hoon."


# ---------- lifecycle, idempotency ----------
def test_refresh_is_idempotent(learner, monkeypatch):
    add_exercise_attempts(uid("l@example.com"), exercise_ids("food", "translation")[0], [0, 0, 0])
    monkeypatch.setattr(clock, "now", lambda: "2026-09-30 10:00:00")
    first = weaknesses(learner)
    monkeypatch.setattr(clock, "now", lambda: "2026-09-30 18:00:00")
    second = weaknesses(learner)
    assert first == second                                     # same row, same detected_at: nothing was re-detected
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM weaknesses").fetchone()[0] == 1


def test_stored_evidence_is_refreshed_as_the_pattern_changes(learner):
    ex = exercise_ids("food", "translation")[0]
    user = uid("l@example.com")
    n = add_exercise_attempts(user, ex, [0, 0, 0])
    assert item_weak(learner)[0]["severity"] == "low"
    add_exercise_attempts(user, ex, [0, 0], start=n)
    w = item_weak(learner)[0]
    assert (w["severity"], w["incorrect"]) == ("high", 5)
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM weaknesses").fetchone()[0] == 1


def test_weakness_resolves_when_the_learner_recovers_and_returns_if_it_recurs(learner, monkeypatch):
    user = uid("l@example.com")
    monkeypatch.setattr(clock, "now", lambda: "2026-09-30 10:00:00")
    n = cycle_attempts(user, "food", [0, 0, 0, 0, 1, 1])
    (w,) = topic_weak(learner, "food")
    assert w["detected_at"] == "2026-09-30 10:00:00"
    monkeypatch.setattr(clock, "now", lambda: "2026-09-30 11:00:00")
    n = cycle_attempts(user, "food", [1] * 10, start=n)                        # recovered
    assert weaknesses(learner) == []
    with db() as conn:
        row = conn.execute("SELECT status, resolved_at FROM weaknesses WHERE rule='low_topic_accuracy'").fetchone()
        assert tuple(row) == ("resolved", "2026-09-30 11:00:00")               # kept, not deleted
    monkeypatch.setattr(clock, "now", lambda: "2026-09-30 12:00:00")
    cycle_attempts(user, "food", [0] * 6, start=n)                             # relapse
    (again,) = topic_weak(learner, "food")
    assert again["detected_at"] == "2026-09-30 12:00:00"
    with db() as conn:
        assert tuple(conn.execute("SELECT COUNT(*), MIN(status), MAX(resolved_at IS NULL) FROM weaknesses WHERE rule='low_topic_accuracy'").fetchone()) == (1, "active", 1)


def test_weaknesses_are_ordered_by_severity(learner):
    user = uid("l@example.com")
    cycle_attempts(user, "food", [0, 0, 0, 1, 1, 1])             # low
    cycle_attempts(user, "transport", [0] * 7)                   # high
    cycle_attempts(user, "shopping", [0, 0, 0, 0, 1, 1, 1, 1, 0, 0])   # medium
    assert [(w["topic"]["slug"], w["severity"]) for w in weaknesses(learner) if w["rule"] == "low_topic_accuracy"] == \
        [("transport", "high"), ("shopping", "medium"), ("food", "low")]


# ---------- scoping ----------
def test_other_learners_attempts_do_not_count(learner, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    cycle_attempts(uid("b@example.com"), "food", [0] * 8)
    assert weaknesses(learner) == []
    assert [w["topic"]["slug"] for w in weaknesses(client2) if w["rule"] == "low_topic_accuracy"] == ["food"]
    add_exercise_attempts(uid("l@example.com"), exercise_ids("transport", "translation")[0], [0, 0, 0])
    assert all(w["rule"] == "repeated_item_errors" for w in weaknesses(learner))
    assert not [w for w in weaknesses(client2) if "transport" in str(w)]              # B unaffected by A's transport mistakes


def test_weaknesses_are_scoped_to_the_target_language(learner):
    """Attempts in a lesson of another language never count for (or show up under) the current target language."""
    user = uid("l@example.com")
    with db() as conn:
        conn.execute("INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order, status) "
                     "VALUES ((SELECT id FROM languages WHERE code='hinglish'), 'A1', 'h1', 'H1', 'd', 1, 'published')")
        lid = conn.execute("SELECT id FROM lessons WHERE slug='h1'").fetchone()[0]
        conn.execute("INSERT INTO lesson_topics(lesson_id, topic_id) SELECT ?, id FROM topics WHERE slug='food'", (lid,))
        conn.execute("INSERT INTO exercises(lesson_id, language_id, kind, prompt, sort_order) VALUES (?, (SELECT id FROM languages WHERE code='hinglish'), 'fill_blank', 'p', 1)", (lid,))
        ex = conn.execute("SELECT id FROM exercises WHERE lesson_id=?", (lid,)).fetchone()[0]
    add_exercise_attempts(user, ex, [0] * 8)
    assert weaknesses(learner) == []                                          # target is Hindi
    learner.put("/api/profile", json={**PROFILE, "target_language": "hinglish"})
    assert [w["topic"]["slug"] for w in weaknesses(learner)] == ["food"]      # target is Hinglish: now it counts
    learner.put("/api/profile", json={**PROFILE, "target_language": "hi"})
    assert weaknesses(learner) == []                                          # and the Hindi view is still clean


# ---------- the rules are what the docs say ----------
def test_thresholds_are_the_documented_values():
    assert (rules.TOPIC_WINDOW, rules.TOPIC_MIN_ATTEMPTS, rules.TOPIC_MIN_INCORRECT, rules.TOPIC_WEAK_BELOW) == (10, 6, 3, 0.6)
    assert (rules.ITEM_MIN_INCORRECT, rules.ITEM_MEDIUM_AT, rules.ITEM_HIGH_AT) == (3, 4, 5)

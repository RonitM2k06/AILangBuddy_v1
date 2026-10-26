import pytest

from backend import main
from backend.curriculum import service as cur
from backend.db import connect

from .conftest import PASSWORD, register

PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}


def db():
    return connect(main.DB_PATH)


@pytest.fixture
def learner(client):
    register(client, "l@example.com")
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


def lessons(c):
    return c.get("/api/lessons").json()["lessons"]


def lesson_id(c, slug):
    return next(l["id"] for l in lessons(c) if l["slug"] == slug)


def exercises(c, slug):
    return c.get(f"/api/lessons/{lesson_id(c, slug)}").json()["lesson"]["exercises"]


def correct_attempt(c, ex):
    """Answer an exercise correctly, using the database for the answer key."""
    with db() as conn:
        key = [r["answer_text"] for r in conn.execute("SELECT answer_text FROM exercise_answers WHERE exercise_id=? AND is_correct=1", (ex["id"],))]
        if ex["kind"] == "multiple_choice":
            aid = conn.execute("SELECT id FROM exercise_answers WHERE exercise_id=? AND is_correct=1", (ex["id"],)).fetchone()[0]
            return c.post(f"/api/exercises/{ex['id']}/attempts", json={"answer_id": aid})
    return c.post(f"/api/exercises/{ex['id']}/attempts", json={"text": key[0]})


def wrong_attempt(c, ex):
    if ex["kind"] == "multiple_choice":
        with db() as conn:
            aid = conn.execute("SELECT id FROM exercise_answers WHERE exercise_id=? AND is_correct=0 LIMIT 1", (ex["id"],)).fetchone()[0]
        return c.post(f"/api/exercises/{ex['id']}/attempts", json={"answer_id": aid})
    return c.post(f"/api/exercises/{ex['id']}/attempts", json={"text": "definitely wrong"})


# ---------- access control ----------
@pytest.mark.parametrize("method,path,body", [
    ("get", "/api/lessons", None), ("get", "/api/lessons/1", None),
    ("post", "/api/exercises/1/attempts", {"answer_id": 1}), ("get", "/api/progress/lessons", None),
])
def test_anonymous_requests_rejected_even_in_demo_mode(client, method, path, body):
    r = getattr(client, method)(path, **({"json": body} if body else {}))
    assert r.status_code == 401


@pytest.mark.parametrize("role", ["parent"])
def test_non_learners_rejected(client, role):
    register(client, f"{role}@example.com", role=role)
    assert client.get("/api/lessons").status_code == 403
    assert client.post("/api/exercises/1/attempts", json={"answer_id": 1}).status_code == 403
    assert client.get("/api/progress/lessons").status_code == 403


def test_admin_is_not_a_learner(client, client2, make_admin):
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert client2.get("/api/lessons").status_code == 403


def test_profile_required(client):
    register(client, "noprofile@example.com")
    assert client.get("/api/lessons").status_code == 409
    assert client.get("/api/lessons/1").status_code == 409
    assert client.post("/api/exercises/1/attempts", json={"answer_id": 1}).status_code == 409
    assert client.get("/api/progress/lessons").status_code == 409


# ---------- listing ----------
def test_list_lessons_for_selected_language_and_level(learner):
    ls = lessons(learner)
    assert [l["slug"] for l in ls] == ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk"]
    assert ls[0]["title"] == "Greetings" and ls[0]["cefr_level"] == "A1"
    assert ls[0]["topics"] == [{"slug": "greetings", "name": "Greetings", "icon": "👋"}]
    assert ls[0]["progress"] == {"status": "not_started", "exercises_total": 4, "exercises_correct": 0, "started_at": None, "completed_at": None}


def test_other_target_language_has_no_lessons_yet(client):
    register(client, "h@example.com")
    client.put("/api/profile", json={**PROFILE, "target_language": "hinglish"})
    assert lessons(client) == []
    assert client.get("/api/lessons/1").status_code == 404


def test_level_filter_includes_lower_levels_only(learner):
    with db() as conn:
        conn.execute("INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order, status) "
                     "VALUES ((SELECT id FROM languages WHERE code='hi'), 'A2', 'advanced', 'A2 lesson', 'd', 1, 'published')")
    assert "advanced" not in [l["slug"] for l in lessons(learner)]           # A1 learner
    learner.put("/api/profile", json={**PROFILE, "cefr_level": "A2"})
    assert [l["slug"] for l in lessons(learner)][-1] == "advanced"            # A2 learner sees A1 + A2, ordered by level
    assert len(lessons(learner)) == 8


def test_unpublished_lessons_are_hidden_and_unreachable(learner):
    lid = lesson_id(learner, "food")
    ex = exercises(learner, "food")[0]
    with db() as conn:
        conn.execute("UPDATE lessons SET status='draft' WHERE id=?", (lid,))
    assert "food" not in [l["slug"] for l in lessons(learner)]
    assert learner.get(f"/api/lessons/{lid}").status_code == 404
    assert learner.post(f"/api/exercises/{ex['id']}/attempts", json={"answer_id": 1}).status_code == 404


# ---------- lesson content ----------
def test_lesson_content(learner):
    l = learner.get(f"/api/lessons/{lesson_id(learner, 'transport')}").json()["lesson"]
    assert l["title"] == "Transport" and "Connaught Place" in l["situation"] and "bhaiya" in l["tip"]
    first = l["vocabulary"][0]
    assert first["kind"] == "phrase" and first["text"] == "भैया, कनॉट प्लेस चलोगे?" and first["pronunciation"] == "Bhaiya, Connaught Place chaloge?"
    assert first["meaning"].startswith("Brother") and first["natural"] == "Could you take me to Connaught Place?"
    words = [v for v in l["vocabulary"] if v["kind"] == "word"]
    assert {w["pronunciation"] for w in words} == {"bhaiya", "kitne", "paise"}
    assert next(w for w in words if w["pronunciation"] == "kitne")["examples"][0]["pronunciation"] == "Kitne paise honge?"
    assert l["grammar"][0]["slug"] == "polite-requests" and l["grammar"][0]["examples"]
    assert [e["kind"] for e in l["exercises"]] == ["multiple_choice", "translation", "fill_blank"]


def test_answers_are_never_leaked_in_lesson_content(learner):
    text = learner.get(f"/api/lessons/{lesson_id(learner, 'food')}").text
    assert not any(f'"{k}"' in text for k in ("is_correct", "correct_answers", "correct"))
    assert all(set(e) <= {"id", "kind", "prompt", "options"} for e in exercises(learner, "food"))  # no explanation before answering
    mc = exercises(learner, "food")[0]
    assert set(mc) == {"id", "kind", "prompt", "options"} and all(set(o) == {"id", "text"} for o in mc["options"])
    assert "options" not in exercises(learner, "food")[1]


def test_unknown_lesson_404(learner):
    assert learner.get("/api/lessons/9999").status_code == 404


def test_meanings_follow_native_language_with_fallback(learner):
    with db() as conn:
        item = conn.execute("SELECT id FROM vocabulary_items WHERE pronunciation='Namaste, aap kaise hain?'").fetchone()[0]
        conn.execute("INSERT INTO vocabulary_translations(item_id, language_id, meaning, natural) VALUES (?, (SELECT id FROM languages WHERE code='es'), 'Hola, ¿cómo está?', 'Hola')", (item,))
    learner.put("/api/profile", json={**PROFILE, "native_language": "es"})
    vocab = learner.get(f"/api/lessons/{lesson_id(learner, 'greetings')}").json()["lesson"]["vocabulary"]
    assert vocab[0]["meaning"] == "Hola, ¿cómo está?"        # translated
    assert vocab[1]["meaning"] == "My name is Alex."          # no Spanish yet: falls back to English


# ---------- submitting answers ----------
def test_multiple_choice_correct_and_incorrect(learner):
    mc = exercises(learner, "greetings")[0]
    r = wrong_attempt(learner, mc)
    assert r.status_code == 200 and r.json()["correct"] is False and r.json()["correct_answers"] == ["A respectful hello"]
    r = correct_attempt(learner, mc)
    assert r.json()["correct"] is True
    assert r.json()["lesson_progress"]["exercises_correct"] == 1


@pytest.mark.parametrize("typed,ok", [
    ("Namaste, aap kaise hain?", True), ("  namaste aap KAISE hain  ", True), ("नमस्ते, आप कैसे हैं?", True),
    ("Namaste aap kaise hai", False), ("", False),
])
def test_translation_grading_normalises_case_and_punctuation(learner, typed, ok):
    tr = exercises(learner, "greetings")[2]
    r = learner.post(f"/api/exercises/{tr['id']}/attempts", json={"text": typed})
    if typed == "":
        assert r.status_code == 422
    else:
        assert r.json()["correct"] is ok


def test_devanagari_vowel_signs_survive_normalisation():
    assert cur.normalize("नमस्ते!") == "नमस्ते" and cur.normalize("कैसे, हैं?") == "कैसे हैं"
    assert cur.normalize("कम") != cur.normalize("कुम")


def test_fill_blank(learner):
    fb = exercises(learner, "transport")[2]
    assert "____" in fb["prompt"]
    assert learner.post(f"/api/exercises/{fb['id']}/attempts", json={"text": "Honge"}).json()["correct"] is True
    assert learner.post(f"/api/exercises/{fb['id']}/attempts", json={"text": "hoga"}).json()["correct"] is False


def test_explanation_returned_after_attempt(learner):
    mc = exercises(learner, "food")[0]
    assert "polite" in correct_attempt(learner, mc).json()["explanation"]


@pytest.mark.parametrize("body", [
    {}, {"answer_id": 1, "text": "x"}, {"text": "x"}, {"answer_id": 999999}, {"answer_id": 0}, {"user_id": 5, "answer_id": 1},
])
def test_invalid_multiple_choice_submissions_rejected(learner, body):
    mc = exercises(learner, "greetings")[0]
    assert learner.post(f"/api/exercises/{mc['id']}/attempts", json=body).status_code == 422
    assert learner.get("/api/progress/lessons").json() == {"progress": []}  # rejected attempts leave no trace


def test_option_of_another_exercise_rejected(learner):
    a, b = exercises(learner, "greetings")[:2]
    with db() as conn:
        foreign = conn.execute("SELECT id FROM exercise_answers WHERE exercise_id=? LIMIT 1", (b["id"],)).fetchone()[0]
    assert learner.post(f"/api/exercises/{a['id']}/attempts", json={"answer_id": foreign}).status_code == 422


@pytest.mark.parametrize("body", [{"answer_id": 1}, {}, {"text": "x" * 1200}])
def test_invalid_typed_submissions_rejected(learner, body):
    tr = exercises(learner, "greetings")[2]
    assert learner.post(f"/api/exercises/{tr['id']}/attempts", json=body).status_code == 422


def test_unknown_exercise_404(learner):
    assert learner.post("/api/exercises/99999/attempts", json={"answer_id": 1}).status_code == 404


# ---------- progress ----------
def test_progress_lifecycle(learner, monkeypatch):
    stamps = iter(["2026-09-30 10:00:00", "2026-09-30 10:05:00", "2026-09-30 10:06:00", "2026-09-30 10:07:00"])
    monkeypatch.setattr(cur, "now", lambda: next(stamps))
    assert learner.get("/api/progress/lessons").json() == {"progress": []}
    exs = exercises(learner, "transport")
    r = wrong_attempt(learner, exs[0]).json()["lesson_progress"]          # a wrong answer starts the lesson but earns nothing
    assert (r["status"], r["exercises_correct"], r["started_at"]) == ("in_progress", 0, "2026-09-30 10:00:00")
    assert correct_attempt(learner, exs[1]).json()["lesson_progress"]["exercises_correct"] == 1
    mid = correct_attempt(learner, exs[2]).json()["lesson_progress"]
    assert (mid["status"], mid["exercises_correct"]) == ("in_progress", 2)   # exs[0] still only answered wrongly
    done = correct_attempt(learner, exs[0]).json()["lesson_progress"]
    assert (done["status"], done["exercises_correct"], done["exercises_total"]) == ("completed", 3, 3)
    assert done["completed_at"] == "2026-09-30 10:07:00" and done["started_at"] == "2026-09-30 10:00:00"
    progress = learner.get("/api/progress/lessons").json()["progress"]
    assert [(p["title"], p["status"]) for p in progress] == [("Transport", "completed")]
    assert next(l for l in lessons(learner) if l["slug"] == "transport")["progress"]["status"] == "completed"
    with db() as conn:  # full history is kept, including the wrong attempt
        assert conn.execute("SELECT COUNT(*), SUM(is_correct) FROM exercise_attempts").fetchone()[:] == (4, 3)


def test_completion_time_does_not_move_on_retries(learner):
    exs = exercises(learner, "transport")
    for ex in exs:
        correct_attempt(learner, ex)
    first = learner.get("/api/progress/lessons").json()["progress"][0]["completed_at"]
    correct_attempt(learner, exs[0])
    assert learner.get("/api/progress/lessons").json()["progress"][0]["completed_at"] == first


def test_progress_lists_only_started_lessons_most_recent_first(learner, monkeypatch):
    stamps = iter(["2026-01-01 00:00:00", "2026-01-02 00:00:00"])
    monkeypatch.setattr(cur, "now", lambda: next(stamps))
    wrong_attempt(learner, exercises(learner, "food")[0])
    wrong_attempt(learner, exercises(learner, "college")[0])
    assert [p["title"] for p in learner.get("/api/progress/lessons").json()["progress"]] == ["College & Work", "Food"]


# ---------- learner isolation ----------
def test_progress_belongs_to_the_authenticated_learner(learner, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    for ex in exercises(learner, "transport"):
        correct_attempt(learner, ex)
    assert client2.get("/api/progress/lessons").json() == {"progress": []}
    assert next(l for l in lessons(client2) if l["slug"] == "transport")["progress"]["status"] == "not_started"
    wrong_attempt(client2, exercises(client2, "food")[0])
    assert [p["title"] for p in learner.get("/api/progress/lessons").json()["progress"]] == ["Transport"]  # B's attempt invisible to A
    with db() as conn:
        owners = {r[0] for r in conn.execute("SELECT DISTINCT user_id FROM exercise_attempts")}
        assert len(owners) == 2


def test_client_cannot_attribute_attempts_to_another_user(learner):
    ex = exercises(learner, "greetings")[0]
    assert learner.post(f"/api/exercises/{ex['id']}/attempts", json={"answer_id": ex["options"][0]["id"], "user_id": 1}).status_code == 422
    assert learner.post(f"/api/exercises/{ex['id']}/attempts?user_id=1", json={"answer_id": ex["options"][0]["id"]}).status_code == 200
    with db() as conn:
        demo = conn.execute("SELECT id FROM users WHERE handle='demo-alex'").fetchone()[0]
        assert conn.execute("SELECT COUNT(*) FROM exercise_attempts WHERE user_id=?", (demo,)).fetchone()[0] == 0


def test_logout_ends_access(learner):
    learner.post("/api/auth/logout")
    assert learner.get("/api/lessons").status_code == 401


# ---------- existing prototype unaffected ----------
def test_prototype_endpoints_unchanged(client):
    # Phase 14A: there is no shared demo state any more (anonymous visitors keep theirs in the browser); everything else is unchanged.
    assert client.get("/api/state/demo-alex").status_code == 401
    assert client.put("/api/state/demo-alex", json={"v": 1, "completedDays": [1, 2]}).status_code == 401
    assert client.get("/api/cities").json()["cities"][0]["slug"] == "delhi"
    assert client.get("/static/content.js").status_code == 200
    assert "window.PACKS" in client.get("/static/content.js").text  # prototype content still served

import json

import pytest

from backend import main
from backend.db import connect
from backend.situations import service as sit

from .conftest import PASSWORD, register

PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}


def db():
    return connect(main.DB_PATH)


@pytest.fixture
def learner(client):
    register(client, "l@example.com")
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


def listing(c):
    return c.get("/api/situations").json()["situations"]


def sid(c, slug):
    return next(s["id"] for s in listing(c) if s["slug"] == slug)


def situation(c, slug):
    return c.get(f"/api/situations/{sid(c, slug)}").json()["situation"]


def respond(c, slug, step_id, **body):
    return c.post(f"/api/situations/{sid(c, slug)}/steps/{step_id}/responses", json=body)


def solve(c, slug, step):
    """Pass a step the right way, taking the answer key from the database."""
    if step["kind"] == "learn_phrase":
        return respond(c, slug, step["id"])
    with db() as conn:
        rows = conn.execute("SELECT id, answer_text FROM situation_step_answers WHERE step_id=? AND is_correct=1 ORDER BY sort_order", (step["id"],)).fetchall()
    if step["kind"] == "choose_response":
        return respond(c, slug, step["id"], answer_id=rows[0]["id"])
    return respond(c, slug, step["id"], text=rows[0]["answer_text"])


def fail(c, slug, step):
    if step["kind"] == "choose_response":
        with db() as conn:
            aid = conn.execute("SELECT id FROM situation_step_answers WHERE step_id=? AND is_correct=0 LIMIT 1", (step["id"],)).fetchone()[0]
        return respond(c, slug, step["id"], answer_id=aid)
    return respond(c, slug, step["id"], text="definitely not it")


def first_of(c, slug, kind):
    return next(s for s in situation(c, slug)["steps"] if s["kind"] == kind)


def advance_to(c, slug, step_id):
    for s in situation(c, slug)["steps"]:
        if s["id"] == step_id:
            return
        assert solve(c, slug, s).json()["correct"]


# ---------- access control ----------
@pytest.mark.parametrize("method,path,body", [
    ("get", "/api/situations", None), ("get", "/api/situations/1", None),
    ("post", "/api/situations/1/steps/1/responses", {}), ("get", "/api/progress/situations", None),
])
def test_anonymous_requests_rejected_even_in_demo_mode(client, method, path, body):
    assert getattr(client, method)(path, **({"json": body} if body is not None else {})).status_code == 401


def test_parent_and_admin_are_not_learners(client, client2, make_admin):
    register(client, "p@example.com", role="parent")
    for r in (client.get("/api/situations"), client.post("/api/situations/1/steps/1/responses", json={}), client.get("/api/progress/situations")):
        assert r.status_code == 403
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert client2.get("/api/situations").status_code == 403


def test_profile_required(client):
    register(client, "noprofile@example.com")
    for r in (client.get("/api/situations"), client.get("/api/situations/1"),
              client.post("/api/situations/1/steps/1/responses", json={}), client.get("/api/progress/situations")):
        assert r.status_code == 409


# ---------- listing ----------
def test_list_situations_for_selected_language_and_level(learner):
    ls = listing(learner)
    assert [s["slug"] for s in ls] == ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk", "emergency"]
    t = ls[1]
    assert (t["title"], t["partner_name"], t["partner_role"], t["cefr_level"], t["difficulty"]) == ("Auto-rickshaw ride", "Raju bhaiya", "Auto driver", "A1", 1)
    assert t["topic"] == {"slug": "transport", "name": "Transport", "icon": "🚌"}
    assert t["progress"] == {"status": "not_started", "steps_total": 7, "steps_completed": 0, "attempts": 0, "current_step_id": t["progress"]["current_step_id"],
                             "current_step_order": 1, "started_at": None, "completed_at": None}
    assert ls[-1]["partner_name"] is None and ls[-1]["topic"]["slug"] == "emergency"


def test_other_target_language_has_no_situations_yet(client):
    register(client, "h@example.com")
    client.put("/api/profile", json={**PROFILE, "target_language": "hinglish"})
    assert listing(client) == []
    assert client.get("/api/situations/1").status_code == 404


def test_level_filter_includes_lower_levels_only(learner):
    with db() as conn:
        conn.execute("INSERT INTO situations(language_id, cefr_code, topic_id, slug, title, description, difficulty, sort_order, status) "
                     "VALUES ((SELECT id FROM languages WHERE code='hi'), 'A2', (SELECT id FROM topics WHERE slug='food'), 'a2', 'A2 one', 'd', 2, 1, 'published')")
    assert "a2" not in [s["slug"] for s in listing(learner)]
    learner.put("/api/profile", json={**PROFILE, "cefr_level": "A2"})
    slugs = [s["slug"] for s in listing(learner)]
    assert slugs[-1] == "a2" and len(slugs) == 9


def test_unpublished_situations_hidden_and_unreachable(learner):
    i = sid(learner, "food")
    step = situation(learner, "food")["steps"][0]
    with db() as conn:
        conn.execute("UPDATE situations SET status='draft' WHERE id=?", (i,))
    assert "food" not in [s["slug"] for s in listing(learner)]
    assert learner.get(f"/api/situations/{i}").status_code == 404
    assert learner.post(f"/api/situations/{i}/steps/{step['id']}/responses", json={}).status_code == 404


# ---------- retrieval ----------
def test_situation_with_ordered_steps(learner):
    s = situation(learner, "transport")
    assert s["title"] == "Auto-rickshaw ride" and s["goal"] == "Get to Connaught Place for a fair price." and s["setting"] == "Outside Kashmere Gate metro"
    assert [st["order"] for st in s["steps"]] == list(range(1, 8))
    assert [st["kind"] for st in s["steps"]] == ["learn_phrase"] * 5 + ["choose_response", "conversation"]
    learn = s["steps"][0]
    assert learn["item"]["text"] == "भैया, कनॉट प्लेस चलोगे?" and learn["item"]["meaning"].startswith("Brother") and learn["item"]["natural"]
    choose = s["steps"][5]
    assert choose["prompt"] == "Namaste! Kahan jaana hai?" and choose["prompt_meaning"] == "Hello! Where do you want to go?"
    assert len(choose["options"]) == 3 and all(set(o) == {"id", "text"} for o in choose["options"])
    convo = s["steps"][6]
    assert "150 rupaye" in convo["prompt"] and convo["suggestions"] == ["Bhaiya, thoda kam kijiye.", "Meter se chaliye.", "Theek hai, chaliye."]


def test_answer_keys_are_not_leaked(learner):
    text = json.dumps(situation(learner, "emergency"))
    assert not any(f'"{k}"' in text for k in ("is_correct", "correct_answers", "correct", "explanation", "answers"))
    steps = situation(learner, "emergency")["steps"]
    translate = next(s for s in steps if s["kind"] == "translate")
    assert "options" not in translate and "suggestions" not in translate
    assert "Main kho gaya hoon" not in json.dumps(translate)       # the typed answer stays secret
    assert "Paas mein hospital kahan hai?" in json.dumps(next(s for s in steps if s["kind"] == "choose_response"))  # an option, not marked


def test_unknown_situation_404(learner):
    assert learner.get("/api/situations/9999").status_code == 404


def test_meanings_follow_native_language_with_fallback(learner):
    with db() as conn:
        item = conn.execute("SELECT id FROM vocabulary_items WHERE pronunciation='Mujhe madad chahiye!'").fetchone()[0]
        conn.execute("INSERT INTO vocabulary_translations(item_id, language_id, meaning) VALUES (?, (SELECT id FROM languages WHERE code='es'), '¡Necesito ayuda!')", (item,))
    learner.put("/api/profile", json={**PROFILE, "native_language": "es"})
    steps = situation(learner, "emergency")["steps"]
    assert steps[0]["item"]["meaning"] == "¡Necesito ayuda!" and steps[1]["item"]["meaning"] == "Where's the nearest hospital?"


# ---------- submitting responses ----------
def test_learn_step_acknowledgement_advances(learner):
    s = situation(learner, "food")
    r = respond(learner, "food", s["steps"][0]["id"])
    assert r.status_code == 200 and r.json()["correct"] is True and r.json()["correct_answers"] == []
    assert r.json()["progress"]["current_step_order"] == 2 and r.json()["progress"]["status"] == "in_progress"


def test_learn_step_rejects_an_answer(learner):
    step = situation(learner, "food")["steps"][0]
    assert respond(learner, "food", step["id"], text="x").status_code == 422
    assert respond(learner, "food", step["id"], answer_id=1).status_code == 422


def test_steps_must_be_taken_in_order(learner):
    steps = situation(learner, "food")["steps"]
    assert respond(learner, "food", steps[2]["id"]).status_code == 409        # skipping ahead
    assert learner.get("/api/progress/situations").json() == {"progress": []}  # a refused step leaves no trace
    respond(learner, "food", steps[0]["id"])
    assert respond(learner, "food", steps[1]["id"]).status_code == 200
    assert respond(learner, "food", steps[0]["id"]).status_code == 200        # redoing a passed step is fine
    assert respond(learner, "food", steps[3]["id"]).status_code == 409


def test_choose_response_right_and_wrong(learner):
    slug = "transport"
    advance_to(learner, slug, first_of(learner, slug, "choose_response")["id"])
    step = first_of(learner, slug, "choose_response")
    bad = fail(learner, slug, step).json()
    assert bad["correct"] is False and bad["correct_answers"] == ["Connaught Place jaana hai."]
    assert bad["progress"]["current_step_order"] == 6                          # still on the same step
    good = solve(learner, slug, step).json()
    assert good["correct"] is True and good["progress"]["current_step_order"] == 7


@pytest.mark.parametrize("typed,ok", [
    ("Bhaiya, thoda kam kijiye.", True), ("  bhaiya thoda KAM kijiye  ", True), ("Meter se chaliye", True),
    ("Kuch aur", False),
])
def test_conversation_grading(learner, typed, ok):
    slug = "transport"
    advance_to(learner, slug, first_of(learner, slug, "conversation")["id"])
    r = respond(learner, slug, first_of(learner, slug, "conversation")["id"], text=typed).json()
    assert r["correct"] is ok
    assert bool(r["correct_answers"]) is (not ok) and "suggestions" in r["explanation"]


def test_translate_accepts_roman_or_devanagari(learner):
    slug = "emergency"
    advance_to(learner, slug, first_of(learner, slug, "translate")["id"])
    step = first_of(learner, slug, "translate")
    assert respond(learner, slug, step["id"], text="main kho gaya hoon").json()["correct"] is True
    assert respond(learner, slug, step["id"], text="मैं खो गया हूँ।").json()["correct"] is True
    assert respond(learner, slug, step["id"], text="Main kho gayi hoon").json()["correct"] is False


def test_fill_blank_steps_are_supported(learner):
    with db() as conn:
        i = conn.execute("SELECT id FROM situations WHERE slug='emergency' AND language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[0]
        conn.execute("DELETE FROM situation_steps WHERE situation_id=?", (i,))
        conn.execute("INSERT INTO situation_steps(situation_id, language_id, sort_order, kind, prompt) VALUES (?, (SELECT id FROM languages WHERE code='hi'), 1, 'fill_blank', 'Mujhe ____ chahiye!')", (i,))
        step = conn.execute("SELECT id FROM situation_steps WHERE situation_id=?", (i,)).fetchone()[0]
        conn.execute("INSERT INTO situation_step_answers(step_id, answer_text, is_correct, sort_order) VALUES (?, 'madad', 1, 1)", (step,))
    assert respond(learner, "emergency", step, text="Kuch").json()["correct"] is False
    done = respond(learner, "emergency", step, text="Madad!").json()
    assert done["correct"] is True and done["progress"]["status"] == "completed"


@pytest.mark.parametrize("body", [{}, {"answer_id": 1, "text": "x"}, {"text": "x"}, {"answer_id": 999999}, {"answer_id": 0}, {"user_id": 5, "answer_id": 1}])
def test_invalid_choose_response_submissions_rejected(learner, body):
    slug = "transport"
    advance_to(learner, slug, first_of(learner, slug, "choose_response")["id"])
    step = first_of(learner, slug, "choose_response")
    before = learner.get("/api/progress/situations").json()["progress"][0]["attempts"]
    assert respond(learner, slug, step["id"], **body).status_code == 422
    assert learner.get("/api/progress/situations").json()["progress"][0]["attempts"] == before  # no attempt recorded


@pytest.mark.parametrize("body", [{}, {"answer_id": 1}, {"text": "  "}, {"text": "x" * 1200}])
def test_invalid_typed_submissions_rejected(learner, body):
    slug = "transport"
    advance_to(learner, slug, first_of(learner, slug, "conversation")["id"])
    assert respond(learner, slug, first_of(learner, slug, "conversation")["id"], **body).status_code == 422


def test_option_from_another_step_rejected(learner):
    advance_to(learner, "transport", first_of(learner, "transport", "choose_response")["id"])
    step = first_of(learner, "transport", "choose_response")
    with db() as conn:
        other = conn.execute("SELECT id FROM situation_step_answers WHERE step_id != ? LIMIT 1", (step["id"],)).fetchone()[0]
    assert respond(learner, "transport", step["id"], answer_id=other).status_code == 422


def test_step_from_another_situation_or_unknown_404(learner):
    other = situation(learner, "food")["steps"][0]["id"]
    assert respond(learner, "transport", other).status_code == 404
    assert respond(learner, "transport", 999999).status_code == 404
    assert learner.post("/api/situations/9999/steps/1/responses", json={}).status_code == 404


# ---------- progress ----------
def test_progress_lifecycle(learner, monkeypatch):
    clock = iter(f"2026-09-30 10:{m:02d}:00" for m in range(60))
    monkeypatch.setattr(sit, "now", lambda: next(clock))
    slug = "transport"
    assert learner.get("/api/progress/situations").json() == {"progress": []}
    steps = situation(learner, slug)["steps"]
    p = solve(learner, slug, steps[0]).json()["progress"]
    assert (p["status"], p["steps_completed"], p["current_step_order"], p["attempts"], p["started_at"]) == ("in_progress", 1, 2, 1, "2026-09-30 10:00:00")
    for s in steps[1:5]:
        solve(learner, slug, s)
    bad = fail(learner, slug, steps[5]).json()["progress"]                      # a wrong answer: attempt counted, no progress
    assert (bad["steps_completed"], bad["current_step_order"], bad["attempts"]) == (5, 6, 6)
    solve(learner, slug, steps[5])
    last = solve(learner, slug, steps[6]).json()["progress"]
    assert (last["status"], last["steps_completed"], last["steps_total"], last["attempts"]) == ("completed", 7, 7, 8)
    assert last["current_step_id"] is None and last["current_step_order"] is None
    assert last["completed_at"] == "2026-09-30 10:07:00" and last["started_at"] == "2026-09-30 10:00:00"
    assert [(p["title"], p["status"]) for p in learner.get("/api/progress/situations").json()["progress"]] == [("Auto-rickshaw ride", "completed")]
    assert next(s for s in listing(learner) if s["slug"] == slug)["progress"]["status"] == "completed"
    with db() as conn:
        assert conn.execute("SELECT COUNT(*), SUM(is_correct) FROM situation_step_attempts").fetchone()[:] == (8, 7)  # full history incl. the wrong one


def test_completion_time_does_not_move_when_steps_are_redone(learner):
    slug = "emergency"
    for s in situation(learner, slug)["steps"]:
        assert solve(learner, slug, s).json()["correct"]
    first = learner.get("/api/progress/situations").json()["progress"][0]["completed_at"]
    assert first
    steps = situation(learner, slug)["steps"]
    assert solve(learner, slug, steps[0]).status_code == 200          # completed situations can be practised freely
    assert solve(learner, slug, steps[-1]).status_code == 200
    assert learner.get("/api/progress/situations").json()["progress"][0]["completed_at"] == first


def test_progress_lists_only_started_most_recent_first(learner, monkeypatch):
    stamps = iter(["2026-01-01 00:00:00", "2026-01-02 00:00:00"])
    monkeypatch.setattr(sit, "now", lambda: next(stamps))
    solve(learner, "food", situation(learner, "food")["steps"][0])
    solve(learner, "college", situation(learner, "college")["steps"][0])
    assert [p["title"] for p in learner.get("/api/progress/situations").json()["progress"]] == ["First day on campus", "Street food stall"]


# ---------- learner isolation ----------
def test_progress_belongs_to_the_authenticated_learner(learner, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    for s in situation(learner, "emergency")["steps"]:
        solve(learner, "emergency", s)
    assert client2.get("/api/progress/situations").json() == {"progress": []}
    assert next(s for s in listing(client2) if s["slug"] == "emergency")["progress"]["status"] == "not_started"
    solve(client2, "food", situation(client2, "food")["steps"][0])
    assert [p["title"] for p in learner.get("/api/progress/situations").json()["progress"]] == ["Getting help"]   # B's step invisible to A
    # B is still at step 1 of emergency: A's completion does not unlock B's later steps
    assert respond(client2, "emergency", situation(client2, "emergency")["steps"][3]["id"]).status_code == 409
    with db() as conn:
        assert len({r[0] for r in conn.execute("SELECT DISTINCT user_id FROM situation_step_attempts")}) == 2


def test_client_cannot_attribute_responses_to_another_user(learner):
    step = situation(learner, "food")["steps"][0]
    assert respond(learner, "food", step["id"], user_id=1).status_code == 422
    assert learner.post(f"/api/situations/{sid(learner, 'food')}/steps/{step['id']}/responses?user_id=1", json={}).status_code == 200
    with db() as conn:
        demo = conn.execute("SELECT id FROM users WHERE handle='demo-alex'").fetchone()[0]
        assert conn.execute("SELECT COUNT(*) FROM situation_step_attempts WHERE user_id=?", (demo,)).fetchone()[0] == 0


def test_logout_ends_access(learner):
    learner.post("/api/auth/logout")
    assert learner.get("/api/situations").status_code == 401


# ---------- existing behaviour unaffected ----------
def test_prototype_and_earlier_phases_unchanged(learner, client2):
    assert client2.get("/api/state/demo-alex").status_code == 401         # Phase 14A: no shared demo state
    assert client2.put("/api/state/demo-alex", json={"v": 1, "completedDays": [1]}).status_code == 401
    content = client2.get("/static/content.js").text
    assert "window.SCENARIOS" in content and "window.PACKS" in content          # prototype content still served unchanged
    assert [l["slug"] for l in learner.get("/api/lessons").json()["lessons"]][0] == "greetings"
    assert client2.get("/api/cities").json()["cities"][0]["slug"] == "delhi"
    assert client2.get("/api/situations").status_code == 401

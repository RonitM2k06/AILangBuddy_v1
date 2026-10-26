"""Roleplay over HTTP: it rides on the existing situations, the server judges every answer, the answer key stays hidden until a step is
resolved, ownership and age rules hold, spoken input obeys the voice restrictions, feedback is evidence-only, and XP goes through the
existing ledger."""
import json
import sqlite3

import pytest

from backend import main, settings
from backend.ai.base import AiError

from .aih import Failing, Fixed, Recorder, all_answers, child, db, fail_step, script, situation_id, say, solve, start, teen, use
from .agekids import make_learner, profile
from .conftest import PASSWORD, register
from .gam import total_xp
from .par import browser, link, make_parent

SLUG = "transport"


ROUTES = [("get", "/api/roleplay/sessions", None), ("post", "/api/roleplay/sessions", {"situation_id": 1}), ("get", "/api/roleplay/sessions/1", None),
          ("post", "/api/roleplay/sessions/1/turns", {"text": "hi"}), ("post", "/api/roleplay/sessions/1/complete", None), ("get", "/api/roleplay/sessions/1/feedback", None)]


def call(c, method, path, body=None):
    return getattr(c, method)(path, **({"json": body} if body is not None else {}))


# ---------- access ----------
@pytest.mark.parametrize("method,path,body", ROUTES)
def test_unauthenticated_rejected(client, lockdown, method, path, body):
    assert call(client, method, path, body).status_code == 401


@pytest.mark.parametrize("method,path,body", ROUTES)
def test_parents_and_admins_rejected(client, client2, make_admin, method, path, body):
    register(client, "p@example.com", role="parent")
    assert call(client, method, path, body).status_code == 403
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert call(client2, method, path, body).status_code == 403


@pytest.mark.parametrize("method,path,body", ROUTES)
def test_a_profile_is_required(client, method, path, body):
    register(client, "np@example.com")
    assert call(client, method, path, body).status_code == 409


# ---------- starting ----------
def test_start_builds_on_an_existing_situation(client):
    t = teen(client)
    with db() as conn:
        before = conn.execute("SELECT COUNT(*) FROM situations").fetchone()[0]
    r = t.post("/api/roleplay/sessions", json={"situation_id": situation_id(t, SLUG)})
    assert r.status_code == 201 and r.json()["resumed"] is False
    s = r.json()["session"]
    assert (s["status"], s["mode"], s["situation"]["title"], s["situation"]["partner_name"]) == ("active", "teen", "Auto-rickshaw ride", "Raju bhaiya")
    assert s["progress"] == {"steps_total": 7, "steps_resolved": 0, "current_step": 1, "all_done": False, "completed": False}
    assert s["current"]["objective"].startswith("Say this in Hindi: “") and s["current"]["attempts_left"] == 3 and s["turns"] == []
    assert "Raju bhaiya" in s["scene"]
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM situations").fetchone()[0] == before                    # no second scenario system: nothing is created
        assert conn.execute("SELECT COUNT(*) FROM situations WHERE language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0] == 8
        assert conn.execute("SELECT COUNT(*) FROM situation_step_attempts").fetchone()[0] == 0           # Phase 5 progress is untouched
        assert conn.execute("SELECT COUNT(*) FROM situation_progress").fetchone()[0] == 0


def test_starting_again_resumes_the_active_session(client):
    t = teen(client)
    a = t.post("/api/roleplay/sessions", json={"situation_id": situation_id(t, SLUG)})
    b = t.post("/api/roleplay/sessions", json={"situation_id": situation_id(t, SLUG)})
    assert b.status_code == 200 and b.json()["resumed"] is True and b.json()["session"]["id"] == a.json()["session"]["id"]
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM roleplay_sessions").fetchone()[0] == 1


@pytest.mark.parametrize("slug", ["transport", "food", "shopping", "directions", "college", "emergency", "greetings", "smalltalk"])
def test_every_existing_situation_works_as_a_roleplay(client, slug):
    t = teen(client)
    s = start(t, slug)
    assert s["progress"]["steps_total"] == len(script(slug)) and s["current"]["objective"]
    assert s["situation"]["partner_name"]                                                                 # the emergency situation has no partner: "Helper"


def test_unknown_unavailable_and_invalid_situations(client, client2):
    t = teen(client)
    assert t.post("/api/roleplay/sessions", json={"situation_id": 99999}).status_code == 404
    k = child(client2)
    assert k.post("/api/roleplay/sessions", json={"situation_id": situation_id(k, "college")}).status_code == 404       # restricted for children (Phase 8)
    for body in ({}, {"situation_id": 0}, {"situation_id": "x"}, {"situation_id": 1, "user_id": 2}, {"situation_id": 1, "steps": 1}):
        assert t.post("/api/roleplay/sessions", json=body).status_code == 422


# ---------- the answer key stays hidden ----------
def test_no_answer_is_ever_shown_before_a_step_is_resolved(client):
    t = teen(client)
    key = [a for a in all_answers(SLUG)]
    blobs = []
    s = t.post("/api/roleplay/sessions", json={"situation_id": situation_id(t, SLUG)})
    blobs.append(s.text)
    sid = s.json()["session"]["id"]
    blobs.append(t.get(f"/api/roleplay/sessions/{sid}").text)
    blobs.append(t.get("/api/roleplay/sessions").text)
    r1 = say(t, sid, "wrong one")
    r2 = say(t, sid, "wrong two")
    blobs += [r1.text, r2.text, t.get(f"/api/roleplay/sessions/{sid}").text]
    first = script(SLUG)[0][2]
    for blob in blobs:
        for answer in key:
            assert answer not in blob, answer
    assert "model_answer" not in r1.text and "model_answer" not in r2.text
    r3 = say(t, sid, "wrong three")                                                                       # the third miss reveals it
    assert r3.json()["turn"]["model_answer"].startswith(first[0])


def test_only_resolved_steps_reveal_their_answer(client):
    t = teen(client)
    sid = start(t, SLUG)["id"]
    keys = script(SLUG)
    assert say(t, sid, keys[0][2][0]).json()["turn"]["model_answer"]                                    # a correct step may show it
    after = t.get(f"/api/roleplay/sessions/{sid}").text
    for _, _, texts in keys[1:]:
        for text in texts:
            assert text not in after                                                                       # later steps stay secret
    assert keys[0][2][0] in after


def test_the_provider_is_not_told_the_answer_while_a_step_is_open(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    sid = start(t, SLUG)["id"]
    say(t, sid, "no"); say(t, sid, "still no")
    key = [x for x in script(SLUG)[0][2] if x]
    for req in rec.turns:
        dump = json.dumps(req.__dict__, default=str, ensure_ascii=False)
        assert req.revealed is None and not any(k in dump for k in all_answers(SLUG)), dump
    say(t, sid, "third")                                                                                  # missed: now it is no longer a secret
    assert rec.turns[-1].revealed and key[0] in rec.turns[-1].revealed
    say(t, sid, script(SLUG)[1][2][0])
    assert rec.turns[-1].revealed and rec.turns[-1].verdict == "correct"


# ---------- turns ----------
def test_a_correct_answer_advances(client):
    t = teen(client)
    s = start(t, SLUG)
    r = say(t, s["id"], script(SLUG)[0][2][0])
    body = r.json()
    assert r.status_code == 200 and body["turn"]["verdict"] == "correct" and body["turn"]["resolved"] == "correct" and body["turn"]["attempt_no"] == 1
    assert body["progress"]["current_step"] == 2 and body["progress"]["steps_resolved"] == 1 and "Raju bhaiya:" in body["turn"]["character"]
    assert "Next:" in body["turn"]["character"]


def test_either_accepted_spelling_counts_and_matching_is_forgiving(client):
    t = teen(client)
    keys = script(SLUG)
    sid = start(t, SLUG)["id"]
    assert say(t, sid, keys[0][2][1]).json()["turn"]["verdict"] == "correct"                              # the Devanagari form
    assert say(t, sid, "  " + keys[1][2][0].upper() + "  ").json()["turn"]["verdict"] == "correct"       # case and spaces do not matter


def test_wrong_answers_get_a_hint_ladder_then_the_step_is_missed(client):
    t = teen(client)
    sid = start(t, SLUG)["id"]
    first = script(SLUG)[0][2][0].split()
    a = say(t, sid, "x").json()["turn"]
    assert (a["verdict"], a["attempt_no"], a["resolved"], a["hint"]) == ("incorrect", 1, "no", f"The phrase is {len(first)} words long.")
    b = say(t, sid, "y").json()["turn"]
    assert b["attempt_no"] == 2 and b["hint"] == f"It starts with “{first[0]}”."
    mid = t.get(f"/api/roleplay/sessions/{sid}").json()["session"]
    assert mid["current"]["attempts_used"] == 2 and mid["current"]["attempts_left"] == 1 and mid["current"]["hint"] == b["hint"]
    c = say(t, sid, "z").json()
    assert c["turn"]["resolved"] == "missed" and c["turn"]["hint"] is None and c["turn"]["model_answer"] and c["progress"]["current_step"] == 2


def test_the_server_decides_correctness_not_the_client(client):
    t = teen(client)
    sid = start(t, SLUG)["id"]
    for extra in ({"verdict": "correct"}, {"correct": True}, {"is_correct": 1}, {"step_id": 2}, {"xp": 50}, {"resolved": "correct"}, {"user_id": 1}, {"attempt_no": 1}):
        assert say(t, sid, "wrong", **extra).status_code == 422
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM roleplay_turns").fetchone()[0] == 0


def test_a_whole_roleplay_end_to_end(client):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    done = t.get(f"/api/roleplay/sessions/{s['id']}").json()["session"]
    assert done["progress"]["all_done"] is True and done["current"] is None and len(done["turns"]) == 7 and done["status"] == "active"
    assert say(t, s["id"], "more").status_code == 409                                                      # nothing left to answer
    r = t.post(f"/api/roleplay/sessions/{s['id']}/complete")
    assert r.status_code == 200
    f = r.json()["feedback"]
    assert f["correctness"] == {"steps_total": 7, "steps_correct": 7, "steps_missed": 0, "first_try_correct": 7, "summary": "7 of 7 steps correct (7 on the first try)."}
    assert set(f) == {"correctness", "vocabulary", "grammar", "hint", "encouragement", "next_step", "pronunciation", "generated_by", "created_at"}
    assert t.get(f"/api/roleplay/sessions/{s['id']}").json()["session"]["status"] == "completed"
    assert say(t, s["id"], "more").status_code == 409                                                      # finished
    assert t.get(f"/api/roleplay/sessions/{s['id']}/feedback").json() == {"feedback": f}


def test_complete_needs_every_step_and_feedback_needs_completion(client):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG, n=3)
    assert t.post(f"/api/roleplay/sessions/{s['id']}/complete").status_code == 409
    assert t.get(f"/api/roleplay/sessions/{s['id']}/feedback").status_code == 409
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM roleplay_feedback").fetchone()[0] == 0


def test_a_new_roleplay_can_start_after_one_is_completed(client):
    t = teen(client)
    a = start(t, SLUG)
    solve(t, a["id"], SLUG)
    t.post(f"/api/roleplay/sessions/{a['id']}/complete")
    b = t.post("/api/roleplay/sessions", json={"situation_id": situation_id(t, SLUG)})
    assert b.status_code == 201 and b.json()["session"]["id"] != a["id"] and len(t.get("/api/roleplay/sessions").json()["sessions"]) == 2


# ---------- feedback is evidence-only ----------
def test_feedback_reflects_what_actually_happened(client):
    t = teen(client)
    s = start(t, SLUG)
    keys = script(SLUG)
    say(t, s["id"], keys[0][2][0])                                                  # first try
    say(t, s["id"], "wrong"); say(t, s["id"], keys[1][2][0])                         # second try
    fail_step(t, s["id"])                                                           # step 3 missed
    solve_rest = [say(t, s["id"], k[2][0]) for k in keys[3:]]
    f = t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()["feedback"]
    assert f["correctness"]["steps_correct"] == 6 and f["correctness"]["steps_missed"] == 1 and f["correctness"]["first_try_correct"] == 5
    assert keys[2][2][0] in f["vocabulary"]                                          # the missed phrase, which was revealed during the session
    for k in keys[3:]:
        assert k[2][0] not in f["vocabulary"]


def test_feedback_never_claims_a_pronunciation_score(client):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    f = t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()["feedback"]
    assert f["pronunciation"]["available"] is False and "score" not in f["pronunciation"] and "no pronunciation feedback" in f["pronunciation"]["note"]
    blob = json.dumps(f).lower()
    assert "pronunciation score" not in blob.replace("no pronunciation score", "") and "/ 100" not in blob


def test_feedback_comes_from_the_provider_but_is_validated(client, monkeypatch):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    use(monkeypatch, Fixed({"vocabulary_feedback": "V", "grammar_feedback": "G", "hint": "H", "encouragement": "E\x00", "next_step": "N"}))
    f = t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()["feedback"]
    assert (f["vocabulary"], f["grammar"], f["hint"], f["encouragement"], f["next_step"], f["generated_by"]) == ("V", "G", "H", "E", "N", "fixed")


@pytest.mark.parametrize("bad", [None, "text", {"vocabulary_feedback": "x"}, {"vocabulary_feedback": "", "grammar_feedback": "g", "hint": "h", "encouragement": "e", "next_step": "n"}])
def test_unusable_feedback_falls_back_to_the_built_in_text(client, monkeypatch, bad):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    use(monkeypatch, Fixed(bad))
    f = t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()["feedback"]
    assert f["generated_by"] == "builtin" and f["grammar"] and "7 of 7" in f["correctness"]["summary"]


# ---------- replay and idempotency ----------
def test_a_replayed_turn_is_not_counted_twice(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    sid = start(t, SLUG)["id"]
    first = say(t, sid, "nope", client_id="turn-1").json()
    second = say(t, sid, "nope", client_id="turn-1").json()
    assert second["replayed"] is True and second["turn"] == first["turn"] and len(rec.turns) == 1
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM roleplay_turns").fetchone()[0] == 1
    assert say(t, sid, "nope", client_id="turn-2").json()["turn"]["attempt_no"] == 2


def test_completing_twice_returns_the_same_feedback_and_pays_once(client):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    a = t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()
    b = t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()
    assert a["replayed"] is False and a["xp_awarded"] == 25 and b["replayed"] is True and b["xp_awarded"] == 0 and a["feedback"] == b["feedback"]
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM roleplay_feedback").fetchone()[0] == 1
    assert total_xp(t) == 25


# ---------- provider failure ----------
def test_a_provider_failure_does_not_lose_the_turn(client, monkeypatch):
    t = teen(client)
    sid = start(t, SLUG)["id"]
    failing = use(monkeypatch, Failing())
    r = say(t, sid, script(SLUG)[0][2][0])
    assert r.status_code == 200 and r.json()["turn"]["verdict"] == "correct" and "Raju bhaiya:" in r.json()["turn"]["character"] and failing.calls == 1
    with db() as conn:
        assert conn.execute("SELECT provider FROM roleplay_turns").fetchone()[0] == "builtin"
    assert say(t, sid, "wrong").json()["turn"]["verdict"] == "incorrect"


@pytest.mark.parametrize("value", ["", None, 5])
def test_unusable_character_lines_fall_back(client, monkeypatch, value):
    t = teen(client)
    sid = start(t, SLUG)["id"]
    use(monkeypatch, Fixed(value))
    r = say(t, sid, "wrong")
    assert r.status_code == 200 and r.json()["turn"]["character"].startswith("Raju bhaiya:")


def test_feedback_survives_a_provider_failure(client, monkeypatch):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    use(monkeypatch, Failing())
    r = t.post(f"/api/roleplay/sessions/{s['id']}/complete")
    assert r.status_code == 200 and r.json()["feedback"]["generated_by"] == "builtin" and "secret" not in r.text


# ---------- validation ----------
@pytest.mark.parametrize("body", [{}, {"text": ""}, {"text": "   "}, {"text": "x" * 501}, {"text": "x" * 2001}, {"text": 5}, {"text": "a", "speaking_session_id": 1},
                                  {"speaking_session_id": 0}, {"speaking_session_id": "x"}, {"text": "a", "client_id": "bad id"}, {"text": "a", "client_id": "x" * 65}])
def test_turn_validation_stores_nothing(client, body):
    t = teen(client)
    sid = start(t, SLUG)["id"]
    assert t.post(f"/api/roleplay/sessions/{sid}/turns", json=body).status_code in (409, 422, 404)
    assert t.post(f"/api/roleplay/sessions/{sid}/turns", json=body).status_code != 200
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM roleplay_turns").fetchone()[0] == 0


def test_the_longest_answer_works_and_ids_are_integers(client):
    t = teen(client)
    sid = start(t, SLUG)["id"]
    assert say(t, sid, "q" * settings.AI_MAX_MESSAGE_CHARS).status_code == 200
    assert t.get("/api/roleplay/sessions/abc").status_code == 422 and say(t, "abc", "x").status_code == 422


def test_complete_takes_no_body(client):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    assert t.post(f"/api/roleplay/sessions/{s['id']}/complete", json={"xp": 100}).status_code == 422
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM roleplay_feedback").fetchone()[0] == 0


# ---------- ownership ----------
def test_sessions_belong_to_their_owner(client, client2):
    a, b = teen(client, "a@example.com"), teen(client2, "b@example.com")
    s = start(a, SLUG)
    solve(a, s["id"], SLUG)
    a.post(f"/api/roleplay/sessions/{s['id']}/complete")
    sid = s["id"]
    foreign = [b.get(f"/api/roleplay/sessions/{sid}"), say(b, sid, "x"), b.post(f"/api/roleplay/sessions/{sid}/complete"), b.get(f"/api/roleplay/sessions/{sid}/feedback"), b.get("/api/roleplay/sessions/9999")]
    assert [r.status_code for r in foreign] == [404] * 5 and len({r.text for r in foreign}) == 1
    assert b.get("/api/roleplay/sessions").json()["sessions"] == []
    assert b.post("/api/roleplay/sessions", json={"situation_id": situation_id(b, SLUG)}).json()["session"]["id"] != sid
    assert total_xp(b) == 0


# ---------- spoken answers obey the voice rules ----------
def spoken(c, text, monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock")
    from .spk import prompt_items, transcribed
    return transcribed(c, text, item_id=prompt_items(c)[0]["item"]["id"])["id"]


def test_a_spoken_answer_is_judged_by_its_transcript(client, monkeypatch):
    t = teen(client)
    sid = start(t, SLUG)["id"]
    good, bad = spoken(t, script(SLUG)[0][2][0], monkeypatch), spoken(t, "something else entirely", monkeypatch)
    r = t.post(f"/api/roleplay/sessions/{sid}/turns", json={"speaking_session_id": bad})
    assert r.status_code == 200 and r.json()["turn"]["verdict"] == "incorrect" and r.json()["turn"]["input_mode"] == "voice" and r.json()["turn"]["you"] == "something else entirely"
    r = t.post(f"/api/roleplay/sessions/{sid}/turns", json={"speaking_session_id": good})
    assert r.json()["turn"]["verdict"] == "correct"
    assert t.post(f"/api/roleplay/sessions/{sid}/turns", json={"speaking_session_id": good}).status_code == 409        # one spoken answer, used once


def test_spoken_feedback_says_there_is_no_pronunciation_analysis(client, monkeypatch):
    t = teen(client)
    s = start(t, SLUG)
    first = spoken(t, script(SLUG)[0][2][0], monkeypatch)
    t.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"speaking_session_id": first})
    solve_rest = [say(t, s["id"], k[2][0]) for k in script(SLUG)[1:]]
    f = t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()["feedback"]
    assert f["pronunciation"]["available"] is False and "speech recognition" in f["pronunciation"]["note"] and "no pronunciation score" in f["pronunciation"]["note"]
    with db() as conn:
        assert conn.execute("SELECT voice_turns FROM roleplay_feedback").fetchone()[0] == 1


def test_an_untranscribed_or_foreign_speaking_session_is_refused(client, client2, monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock")
    from .spk import create, prompt_items
    a, b = teen(client, "a@example.com"), teen(client2, "b@example.com")
    sid = start(a, SLUG)["id"]
    raw = create(a, prompt_items(a)[0]["item"]["id"])["id"]
    assert a.post(f"/api/roleplay/sessions/{sid}/turns", json={"speaking_session_id": raw}).status_code == 409
    theirs = spoken(b, "x", monkeypatch)
    assert a.post(f"/api/roleplay/sessions/{sid}/turns", json={"speaking_session_id": theirs}).status_code == 404
    assert a.post(f"/api/roleplay/sessions/{sid}/turns", json={"speaking_session_id": 99999}).status_code == 404


def test_a_parent_voice_restriction_applies_to_spoken_roleplay_answers(client, monkeypatch):
    t = teen(client)
    sid = start(t, SLUG)["id"]
    heard = spoken(t, script(SLUG)[0][2][0], monkeypatch)
    parent = browser()
    make_parent(parent, "parent@example.com")
    link_id = link(parent, t)
    assert parent.put(f"/api/parent/children/{link_id}/controls", json={"voice_disabled": True}).status_code == 200
    r = t.post(f"/api/roleplay/sessions/{sid}/turns", json={"speaking_session_id": heard})
    assert r.status_code == 403
    assert say(t, sid, script(SLUG)[0][2][0]).json()["turn"]["verdict"] == "correct"                       # typing is not voice: still fine
    parent.put(f"/api/parent/children/{link_id}/controls", json={"voice_disabled": False})
    assert t.post(f"/api/roleplay/sessions/{sid}/turns", json={"speaking_session_id": heard}).status_code == 200


def test_a_child_cannot_use_spoken_roleplay(client, monkeypatch):
    k = child(client)
    sid = start(k, SLUG)["id"]
    assert k.post(f"/api/roleplay/sessions/{sid}/turns", json={"speaking_session_id": 1}).status_code == 403


def test_roleplay_creates_no_voice_data(client):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    t.post(f"/api/roleplay/sessions/{s['id']}/complete")
    with db() as conn:
        for table in ("audio_sessions", "speaking_sessions", "stt_runs", "speaking_transcripts", "pronunciation_assessments"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


# ---------- children ----------
def test_a_child_can_roleplay_with_bounded_input_and_the_built_in_provider(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    k = child(client)
    s = start(k, SLUG)
    assert s["mode"] == "child"
    assert say(k, s["id"], "x" * 101).status_code == 422
    r = say(k, s["id"], script(SLUG)[0][2][0])
    assert r.status_code == 200 and r.json()["turn"]["verdict"] == "correct" and rec.calls == 0
    solve_rest = [say(k, s["id"], key[2][0]) for key in script(SLUG)[1:]]
    assert k.post(f"/api/roleplay/sessions/{s['id']}/complete").status_code == 200 and rec.calls == 0


def test_a_child_never_reaches_an_external_model_in_roleplay(client, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "llm")
    monkeypatch.setattr(main, "provider", lambda: "groq")

    async def boom(*a, **k):
        raise AssertionError("a child must never reach an external model")
    monkeypatch.setattr(main, "call_llm", boom)
    k = child(client)
    s = start(k, SLUG)
    assert say(k, s["id"], "wrong").status_code == 200


def test_a_session_started_while_a_child_is_governed_by_the_current_age(client):
    k = child(client)
    s = start(k, SLUG)
    k.put("/api/profile", json=profile(30))
    assert say(k, s["id"], "x" * 300).status_code == 200                                                     # an adult may type longer answers
    k.put("/api/profile", json=profile(8))
    assert say(k, s["id"], "x" * 300).status_code == 422


def test_a_learner_who_loses_access_to_the_situation_loses_the_session(client):
    t = teen(client)
    s = start(t, "college")
    assert t.get(f"/api/roleplay/sessions/{s['id']}").status_code == 200
    t.put("/api/profile", json=profile(8))
    assert t.get(f"/api/roleplay/sessions/{s['id']}").status_code == 404 and say(t, s["id"], "x").status_code == 404


# ---------- weakness context (teens and adults only) ----------
def test_relevant_weaknesses_reach_the_provider_for_older_learners(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    s = start(t, "emergency")
    with db() as conn:
        uid = conn.execute("SELECT user_id FROM roleplay_sessions").fetchone()[0]
        step = conn.execute("SELECT id, item_id FROM situation_steps WHERE kind = 'translate' AND item_id IS NOT NULL AND situation_id = ?", (situation_id(t, "emergency"),)).fetchone()
        for i in range(4):                                  # the same item answered wrongly again and again, last answer wrong => a weakness
            conn.execute("INSERT INTO situation_step_attempts(user_id, step_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, 'x', 0, ?)", (uid, step["id"], f"2026-09-0{i + 1} 09:00:00"))
    assert any(w["item"]["id"] == step["item_id"] for w in t.get("/api/weaknesses").json()["weaknesses"] if "item" in w)
    say(t, s["id"], "x")
    assert len(rec.turns[-1].weaknesses) == 1 and "(" in rec.turns[-1].weaknesses[0]


def test_children_get_no_weakness_information(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    k = child(client)
    s = start(k, "emergency")
    say(k, s["id"], "x")
    assert rec.calls == 0                                    # a child's turn never reaches an injected provider, so nothing about them can


# ---------- gamification through the existing ledger ----------
def test_completing_a_roleplay_earns_situation_xp_once_through_the_ledger(client):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    r = t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()
    assert r["xp_awarded"] == 25 and total_xp(t) == 25
    with db() as conn:
        assert [tuple(x) for x in conn.execute("SELECT kind, xp FROM xp_events")] == [("situation", 25)]
    s2 = start(t, SLUG)                                                                                       # doing the same situation again pays nothing more
    solve(t, s2["id"], SLUG)
    assert t.post(f"/api/roleplay/sessions/{s2['id']}/complete").json()["xp_awarded"] == 0 and total_xp(t) == 25


def test_roleplay_and_the_situation_itself_share_one_reward(client):
    t = teen(client)
    sit = situation_id(t, SLUG)
    with db() as conn:
        uid = conn.execute("SELECT id FROM users WHERE email = 'teen@example.com'").fetchone()[0]
        conn.execute("INSERT INTO situation_progress(user_id, situation_id, started_at, completed_at) VALUES (?, ?, '2026-09-01 08:00:00', '2026-09-01 09:00:00')", (uid, sit))
    assert total_xp(t) == 25
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    assert t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()["xp_awarded"] == 0 and total_xp(t) == 25


def test_failing_on_purpose_earns_nothing(client):
    t = teen(client)
    s = start(t, SLUG)
    for _ in script(SLUG):
        fail_step(t, s["id"])
    r = t.post(f"/api/roleplay/sessions/{s['id']}/complete")
    assert r.status_code == 200 and r.json()["feedback"]["correctness"]["steps_correct"] == 0 and r.json()["xp_awarded"] == 0 and total_xp(t) == 0


def test_at_least_half_correct_is_needed(client):
    t = teen(client)
    s = start(t, SLUG)
    keys = script(SLUG)
    for i, k in enumerate(keys):
        if i < 3:
            say(t, s["id"], k[2][0])
        else:
            fail_step(t, s["id"])
    assert t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()["xp_awarded"] == 0                    # 3 of 7 is under half
    s2 = start(t, SLUG)
    for i, k in enumerate(keys):
        if i < 4:
            say(t, s2["id"], k[2][0])
        else:
            fail_step(t, s2["id"])
    assert t.post(f"/api/roleplay/sessions/{s2['id']}/complete").json()["xp_awarded"] == 25                 # 4 of 7


def test_no_xp_can_be_requested_by_the_client(client):
    t = teen(client)
    s = start(t, SLUG)
    for path, method in ((f"/api/roleplay/sessions/{s['id']}/xp", "post"), ("/api/roleplay/xp", "post"), ("/api/tutor/xp", "post")):
        assert getattr(t, method)(path, json={"xp": 1000}).status_code in (404, 405)
    assert total_xp(t) == 0


def test_the_tutor_awards_no_xp(client):
    t = teen(client)
    cid = t.post("/api/tutor/conversations", json={}).json()["conversation"]["id"]
    for _ in range(5):
        t.post(f"/api/tutor/conversations/{cid}/messages", json={"message": "hint"})
    assert total_xp(t) == 0


# ---------- schema ----------
def test_roleplay_constraints(client):
    t = teen(client)
    s = start(t, SLUG)
    other = situation_id(t, "food")
    with db() as conn:
        uid = conn.execute("SELECT user_id FROM roleplay_sessions WHERE id = ?", (s["id"],)).fetchone()[0]
        sit = situation_id(t, SLUG)
        steps = [r[0] for r in conn.execute("SELECT id FROM situation_steps WHERE situation_id = ? ORDER BY sort_order", (sit,))]
        foreign_step = conn.execute("SELECT id FROM situation_steps WHERE situation_id = ? LIMIT 1", (other,)).fetchone()[0]
        ins = ("INSERT INTO roleplay_turns(session_id, user_id, situation_id, step_id, turn_no, attempt_no, learner_text, input_mode, verdict, resolved, character_reply, provider, created_at) "
               "VALUES (?, ?, ?, ?, ?, ?, 'x', 'text', ?, ?, 'r', 'mock', 't')")
        good = (s["id"], uid, sit, steps[0], 1, 1, "incorrect", "no")
        conn.execute(ins, good)
        bad = [(s["id"], uid, sit, steps[0], 1, 1, "incorrect", "no"),                       # duplicate turn number
               (s["id"], uid, sit, foreign_step, 2, 1, "incorrect", "no"),                   # a step of a different situation
               (s["id"], uid + 1, sit, steps[0], 2, 1, "incorrect", "no"),                   # someone else's session
               (s["id"], uid, other, steps[0], 2, 1, "incorrect", "no"),                     # the session is for another situation
               (s["id"], uid, sit, steps[0], 2, 4, "incorrect", "no"),                       # attempt out of range
               (s["id"], uid, sit, steps[0], 2, 1, "correct", "no"),                         # verdict and resolution disagree
               (s["id"], uid, sit, steps[0], 2, 1, "incorrect", "missed"),                   # missed only on the third try
               (s["id"], uid, sit, steps[0], 2, 1, "maybe", "no")]
        for args in bad:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(ins, args)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO roleplay_sessions(user_id, situation_id, language_id, cefr_code, mode, steps_total, created_at) "
                         "SELECT user_id, situation_id, language_id, cefr_code, mode, steps_total, created_at FROM roleplay_sessions WHERE id = ?", (s["id"],))     # one active per situation
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE roleplay_sessions SET status = 'completed' WHERE id = ?", (s["id"],))            # completed needs a time and counts
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE roleplay_sessions SET status = 'completed', completed_at = 't', steps_correct = 5, steps_missed = 5 WHERE id = ?", (s["id"],))   # must add up
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO roleplay_feedback(session_id, user_id, steps_total, steps_correct, steps_missed, first_try_correct, voice_turns, correctness_text, vocabulary_feedback, "
                         "grammar_feedback, hint, encouragement, next_step, pronunciation_note, provider, created_at) VALUES (?, ?, 7, 5, 5, 0, 0, 'x', '', '', '', '', '', '', 'm', 't')", (s["id"], uid))
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        assert conn.execute("SELECT COUNT(*) FROM roleplay_turns").fetchone()[0] == 0 and conn.execute("SELECT COUNT(*) FROM roleplay_sessions").fetchone()[0] == 0


def test_phase_five_is_unchanged_by_roleplay(client):
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    t.post(f"/api/roleplay/sessions/{s['id']}/complete")
    sit = t.get(f"/api/situations/{situation_id(t, SLUG)}").json()["situation"]
    assert sit["progress"]["status"] == "not_started"                                                       # roleplay does not complete the Phase 5 situation
    assert t.get("/api/weaknesses").json()["weaknesses"] == [] and t.get("/api/confidence").status_code == 200


# ---------- no provider call is wasted, and children's prompts carry nothing personal ----------
def test_a_finished_session_does_not_call_the_provider(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    t.post(f"/api/roleplay/sessions/{s['id']}/complete")
    calls = rec.calls
    assert say(t, s["id"], "x").status_code == 409 and rec.calls == calls


def test_completing_twice_asks_the_provider_once(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    s = start(t, SLUG)
    solve(t, s["id"], SLUG)
    t.post(f"/api/roleplay/sessions/{s['id']}/complete")
    t.post(f"/api/roleplay/sessions/{s['id']}/complete")
    assert len(rec.feedback) == 1


def test_an_unfinished_roleplay_does_not_call_the_feedback_provider(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    s = start(t, SLUG)
    t.post(f"/api/roleplay/sessions/{s['id']}/complete")
    assert rec.feedback == []


def test_a_child_prompt_has_no_weakness_information(client, monkeypatch):
    from backend.ai import registry
    rec = Recorder()
    monkeypatch.setattr(registry, "offline", lambda: rec)                       # the provider children are given: now observable
    k = child(client)
    s = start(k, "emergency")
    with db() as conn:
        uid = conn.execute("SELECT user_id FROM roleplay_sessions").fetchone()[0]
        step = conn.execute("SELECT id FROM situation_steps WHERE kind = 'translate' AND situation_id = ?", (situation_id(k, "emergency"),)).fetchone()[0]
        for i in range(4):
            conn.execute("INSERT INTO situation_step_attempts(user_id, step_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, 'x', 0, ?)", (uid, step, f"2026-09-0{i + 1} 09:00:00"))
    assert say(k, s["id"], "x").status_code == 200
    assert rec.turns[-1].weaknesses == () and rec.turns[-1].mode == "child"


def test_exactly_half_correct_earns_the_reward(client):
    t = teen(client)
    keys = script("food")
    s = start(t, "food")
    for i, k in enumerate(keys):
        if i < len(keys) // 2:
            say(t, s["id"], k[2][0])
        else:
            fail_step(t, s["id"])
    assert len(keys) % 2 == 0
    assert t.post(f"/api/roleplay/sessions/{s['id']}/complete").json()["xp_awarded"] == 25


def test_a_completed_session_without_a_transcript_is_not_an_answer(client, monkeypatch):
    """Belt and braces: even if a speaking session were marked completed with no transcript behind it, there is nothing to judge."""
    monkeypatch.setenv("STT_PROVIDER", "mock")
    from .spk import audio, create, prompt_items, upload
    t = teen(client)
    sid = start(t, SLUG)["id"]
    raw = create(t, prompt_items(t)[0]["item"]["id"])["id"]
    assert upload(t, raw, audio("x")).status_code == 200
    with db() as conn:
        conn.execute("UPDATE speaking_sessions SET stage = 'completed' WHERE session_id = ?", (raw,))
    r = t.post(f"/api/roleplay/sessions/{sid}/turns", json={"speaking_session_id": raw})
    assert r.status_code == 409 and "transcribe" in r.json()["detail"]
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM roleplay_turns").fetchone()[0] == 0

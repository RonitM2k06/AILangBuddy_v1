"""The AI tutor over HTTP: authorization and isolation, persistence, bounded context, validation, provider failure, replay safety, the
child boundary, and that the model is only ever told what this learner may know."""
import json
import time

import pytest

from backend import main, settings
from backend.ai import llm, registry
from backend.ai.mock import QUICK_PROMPTS
from backend.tutor import service as tutor_service

from .aih import Failing, Fixed, Recorder, Slow, child, db, teen, use
from .agekids import make_learner, profile
from .conftest import PASSWORD, register
from .lis import activities, answer, wrong_options
from .par import browser


def new_conv(c, **body):
    r = c.post("/api/tutor/conversations", json=body)
    assert r.status_code == 201, r.text
    return r.json()["conversation"]["id"]


def send(c, cid, message="hello", **extra):
    return c.post(f"/api/tutor/conversations/{cid}/messages", json={"message": message, **extra})


ROUTES = [("get", "/api/tutor/conversations", None), ("post", "/api/tutor/conversations", {}), ("get", "/api/tutor/conversations/1", None),
          ("get", "/api/tutor/conversations/1/messages", None), ("post", "/api/tutor/conversations/1/messages", {"message": "hi"})]


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


# ---------- conversations ----------
def test_create_and_list(client):
    t = teen(client)
    r = t.post("/api/tutor/conversations", json={})
    assert r.status_code == 201
    c = r.json()["conversation"]
    assert (c["title"], c["mode"], c["status"], c["message_count"], c["context"]) == ("Chat with your tutor", "teen", "active", 0, None)
    assert r.json()["quick_prompts"] is None
    assert [x["id"] for x in t.get("/api/tutor/conversations").json()["conversations"]] == [c["id"]]


def test_conversation_about_a_lesson_a_situation_or_a_topic(client):
    t = teen(client)
    lesson = t.get("/api/lessons").json()["lessons"][0]
    sit = t.get("/api/situations").json()["situations"][0]
    a = t.post("/api/tutor/conversations", json={"lesson_id": lesson["id"]}).json()["conversation"]
    b = t.post("/api/tutor/conversations", json={"situation_id": sit["id"]}).json()["conversation"]
    c = t.post("/api/tutor/conversations", json={"topic": "food"}).json()["conversation"]
    assert a["title"] == lesson["title"] and a["context"] == {"type": "lesson", "id": lesson["id"]}
    assert b["title"] == sit["title"] and b["context"] == {"type": "situation", "id": sit["id"]}
    assert c["context"] == {"type": "topic", "slug": "food"}


@pytest.mark.parametrize("body", [{"lesson_id": 1, "situation_id": 1}, {"lesson_id": 1, "topic": "food"}, {"lesson_id": 0}, {"lesson_id": "x"}, {"topic": ""},
                                  {"topic": "x" * 41}, {"user_id": 1}, {"xp": 5}, {"language": "fr"}, {"title": "hi"}])
def test_create_validation(client, body):
    assert teen(client).post("/api/tutor/conversations", json=body).status_code == 422


def test_unknown_or_unavailable_context(client):
    t = teen(client)
    assert t.post("/api/tutor/conversations", json={"lesson_id": 99999}).status_code == 404
    assert t.post("/api/tutor/conversations", json={"situation_id": 99999}).status_code == 404
    assert t.post("/api/tutor/conversations", json={"topic": "nonsense"}).status_code == 422


def test_age_restricted_content_cannot_be_a_context_for_a_child(client, client2):
    k, a = child(client), teen(client2, "t@example.com")
    lesson = next(l["id"] for l in a.get("/api/lessons").json()["lessons"] if l["slug"] == "college")
    assert a.post("/api/tutor/conversations", json={"lesson_id": lesson}).status_code == 201
    assert k.post("/api/tutor/conversations", json={"lesson_id": lesson}).status_code == 404


def test_conversation_cap(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_MAX_CONVERSATIONS_PER_LEARNER", 2)
    t = teen(client)
    new_conv(t); new_conv(t)
    assert t.post("/api/tutor/conversations", json={}).status_code == 409


# ---------- messages and persistence ----------
def test_a_message_and_its_reply_are_stored_in_order(client):
    t = teen(client)
    cid = new_conv(t)
    r = send(t, cid, "give me a hint")
    assert r.status_code == 200
    body = r.json()
    assert (body["message"]["seq"], body["message"]["role"], body["reply"]["seq"], body["reply"]["role"]) == (1, "learner", 2, "tutor")
    assert body["reply"]["generated"] is True and body["reply"]["provider"] == "mock" and body["replayed"] is False
    send(t, cid, "why was I wrong?")
    msgs = t.get(f"/api/tutor/conversations/{cid}/messages").json()["messages"]
    assert [(m["seq"], m["role"]) for m in msgs] == [(1, "learner"), (2, "tutor"), (3, "learner"), (4, "tutor")]
    assert msgs[0]["content"] == "give me a hint" and t.get(f"/api/tutor/conversations/{cid}").json()["conversation"]["message_count"] == 4
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 4


def test_history_paging(client):
    t = teen(client)
    cid = new_conv(t)
    for i in range(3):
        send(t, cid, f"message {i}")
    assert [m["seq"] for m in t.get(f"/api/tutor/conversations/{cid}/messages?after_seq=2&limit=2").json()["messages"]] == [3, 4]
    assert t.get(f"/api/tutor/conversations/{cid}/messages?limit=0").status_code == 422
    assert t.get(f"/api/tutor/conversations/{cid}/messages?limit=101").status_code == 422
    assert t.get(f"/api/tutor/conversations/{cid}/messages?after_seq=-1").status_code == 422


def test_the_built_in_provider_is_deterministic(client, client2):
    a, b = teen(client, "a@example.com"), teen(client2, "b@example.com")
    ra = send(a, new_conv(a), "I need a hint").json()["reply"]["content"]
    rb = send(b, new_conv(b), "I need a hint").json()["reply"]["content"]
    assert ra == rb and "Advice (generated, not a record):" in ra and "From your records:" in ra
    assert send(a, new_conv(a), "I need a hint").json()["reply"]["content"] == ra


def test_it_works_with_no_api_key_and_ignores_a_configured_key_by_default(client, monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setattr(main, "provider", lambda: "groq")                       # an LLM IS configured in this environment...
    async def boom(*a, **k):
        raise AssertionError("the real LLM must not be called unless AI_PROVIDER=llm")
    monkeypatch.setattr(main, "call_llm", boom)
    t = teen(client)
    assert send(t, new_conv(t)).json()["reply"]["provider"] == "mock"           # ...and still the built-in provider answers


def test_replies_use_the_learners_own_phrases_and_level(client):
    t = teen(client)
    reply = send(t, new_conv(t), "help").json()["reply"]["content"]
    assert "Hindi" in reply and "level A1" in reply


# ---------- stored facts versus generated advice ----------
def test_a_new_learner_has_no_facts_and_the_tutor_says_so(client):
    t = teen(client)
    body = send(t, new_conv(t), "how am I doing?").json()
    assert body["facts"] == [] and "I don't have any practice records for you yet" in body["reply"]["content"]


def test_facts_come_from_the_learners_own_records(client):
    t = teen(client)
    for _ in range(4):
        for a in [x for x in activities(t) if x["topic"]["slug"] == "greetings"]:
            answer(t, a["id"], wrong_options(a["id"])[0])
    assert t.post("/api/confidence", json={"topic": "food", "score": 35}).status_code == 201
    body = send(t, new_conv(t), "why am I making mistakes?").json()
    kinds = {f["kind"] for f in body["facts"]}
    assert {"weakness", "confidence", "activity"} <= kinds
    texts = " ".join(f["text"] for f in body["facts"])
    assert "Self-rated confidence in" in texts and "35%" in texts and "answers in lessons, situations and listening were correct" in texts
    assert len(body["facts"]) <= settings.AI_MAX_FACTS
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutor_message_facts").fetchone()[0] == len(body["facts"])
    assert all(f["text"] in body["reply"]["content"] for f in body["facts"][:3])               # the stored facts are what the reply quotes


def test_a_conversation_context_is_a_stored_fact(client):
    t = teen(client)
    lesson = t.get("/api/lessons").json()["lessons"][0]
    body = send(t, new_conv(t, lesson_id=lesson["id"]), "hint").json()
    assert body["facts"][0] == {"kind": "context", "text": f"The conversation is about: {lesson['title']}"}


def test_another_learners_records_never_reach_the_tutor(client, client2, monkeypatch):
    rec = use(monkeypatch, Recorder())
    a, b = teen(client, "a@example.com"), teen(client2, "b@example.com")
    for _ in range(4):
        for act in activities(a)[:6]:
            answer(a, act["id"], wrong_options(act["id"])[0])
    a.post("/api/confidence", json={"topic": "food", "score": 11})
    body = send(b, new_conv(b), "tell me about my progress").json()
    assert body["facts"] == [] and not any("11%" in str(x) for x in rec.tutor[-1].facts)
    assert rec.tutor[-1].facts == ()


def test_the_model_is_never_told_private_data(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = make_learner(client, "secret.person@example.com", 14)
    client.put("/api/profile", json=profile(14))
    for a in activities(t)[:2]:
        answer(t, a["id"], wrong_options(a["id"])[0])
    send(t, new_conv(t), "hello")
    dump = json.dumps(rec.tutor[-1].__dict__, default=str, ensure_ascii=False)
    for needle in ("secret.person", "@example.com", "Test User", "date_of_birth", "password", "token", "handle", "user_id", "audio_ref", "parent"):
        assert needle not in dump, needle
    assert set(rec.tutor[-1].__dict__) == {"mode", "language", "cefr", "message", "facts", "history", "context_title", "phrases", "turn_index", "quick_prompt"}


def test_no_answer_key_or_other_private_item_is_in_the_prompt(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    send(t, new_conv(t), "hello")
    dump = json.dumps(rec.tutor[-1].__dict__, default=str, ensure_ascii=False)
    for a in ("is_correct", "answer_text", "exercise_answers"):
        assert a not in dump


# ---------- bounded context ----------
def test_a_long_history_is_never_an_unlimited_prompt(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    cid = new_conv(t)
    for i in range(12):
        assert send(t, cid, f"message number {i} " + "x" * 400).status_code == 200
    assert len(rec.tutor) == 12
    assert all(len(r.history) <= settings.AI_HISTORY_WINDOW for r in rec.tutor)
    assert len(rec.tutor[-1].history) == settings.AI_HISTORY_WINDOW
    assert rec.tutor[-1].history[-1][0] == "tutor" and "message number 10" in rec.tutor[-1].history[-2][1]       # the LATEST messages
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 24                            # ...while the database keeps all of them


def test_the_whole_prompt_is_bounded_by_characters(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_MAX_PROMPT_CHARS", 1500)
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    cid = new_conv(t)
    for i in range(8):
        send(t, cid, "y" * 450)
    last = rec.tutor[-1]
    size = len(last.message) + sum(len(f) for f in last.facts) + sum(len(x) for _, x in last.history) + sum(len(p["text"]) + len(p["meaning"]) + len(p["pronunciation"] or "") for p in last.phrases)
    assert size <= 1500 and len(last.history) < settings.AI_HISTORY_WINDOW


def test_facts_and_phrases_are_bounded(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    for _ in range(4):
        for a in activities(t):
            answer(t, a["id"], wrong_options(a["id"])[0])
    send(t, new_conv(t), "hello")
    assert len(rec.tutor[-1].facts) <= settings.AI_MAX_FACTS and len(rec.tutor[-1].phrases) <= 5
    assert all(len(f) <= 300 for f in rec.tutor[-1].facts)


def test_a_conversation_has_a_message_cap(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_MAX_MESSAGES_PER_CONVERSATION", 4)
    t = teen(client)
    cid = new_conv(t)
    assert send(t, cid).status_code == 200 and send(t, cid).status_code == 200
    r = send(t, cid)
    assert r.status_code == 409 and "full" in r.json()["detail"]
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 4


# ---------- validation ----------
@pytest.mark.parametrize("body", [{}, {"message": ""}, {"message": "   "}, {"message": "x" * 501}, {"message": "x" * 2001}, {"message": 5}, {"message": None},
                                  {"message": "hi", "quick_prompt": "teach_me_a_phrase"}, {"quick_prompt": "teach_me_a_phrase"},
                                  {"message": "hi", "role": "tutor"}, {"message": "hi", "user_id": 1}, {"message": "hi", "xp": 100}, {"message": "hi", "facts": ["x"]},
                                  {"message": "hi", "client_id": "bad id!"}, {"message": "hi", "client_id": "x" * 65}, {"message": "hi", "client_id": ""}])
def test_message_validation_stores_nothing(client, body):
    t = teen(client)
    cid = new_conv(t)
    assert t.post(f"/api/tutor/conversations/{cid}/messages", json=body).status_code == 422
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 0


def test_the_longest_allowed_message_works(client):
    t = teen(client)
    assert send(t, new_conv(t), "z" * settings.AI_MAX_MESSAGE_CHARS).status_code == 200


def test_ids_must_be_integers(client):
    t = teen(client)
    assert t.get("/api/tutor/conversations/abc").status_code == 422
    assert t.post("/api/tutor/conversations/abc/messages", json={"message": "x"}).status_code == 422


# ---------- ownership and isolation ----------
def test_conversations_belong_to_their_owner(client, client2):
    a, b = teen(client, "a@example.com"), teen(client2, "b@example.com")
    cid = new_conv(a)
    send(a, cid, "private words")
    for r in (b.get(f"/api/tutor/conversations/{cid}"), b.get(f"/api/tutor/conversations/{cid}/messages"), send(b, cid, "hello"), b.get("/api/tutor/conversations/99999")):
        assert r.status_code == 404
    assert r.json() == b.get(f"/api/tutor/conversations/{cid}").json()           # a foreign id looks exactly like a missing one
    assert b.get("/api/tutor/conversations").json()["conversations"] == []
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 2         # b added nothing to a's conversation
    assert "private words" not in json.dumps(b.get("/api/tutor/conversations").json())


def test_the_database_keeps_messages_in_their_owners_conversation(client, client2):
    import sqlite3
    a, b = teen(client, "a@example.com"), teen(client2, "b@example.com")
    cid = new_conv(a)
    with db() as conn:
        b_id = conn.execute("SELECT id FROM users WHERE email = 'b@example.com'").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO tutor_messages(conversation_id, user_id, seq, role, content, created_at) VALUES (?, ?, 1, 'learner', 'x', 't')", (cid, b_id))


# ---------- provider failure and bad output ----------
def test_a_provider_failure_stores_nothing_and_can_be_retried(client, monkeypatch):
    t = teen(client)
    cid = new_conv(t)
    failing = use(monkeypatch, Failing())
    r = send(t, cid, "hello")
    assert r.status_code == 502 and "try again" in r.json()["detail"] and failing.calls == 1
    assert "provider_error" not in r.text
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 0
    assert t.get(f"/api/tutor/conversations/{cid}").json()["conversation"]["message_count"] == 0
    use(monkeypatch, Recorder())
    assert send(t, cid, "hello").status_code == 200 and t.get(f"/api/tutor/conversations/{cid}").json()["conversation"]["message_count"] == 2


@pytest.mark.parametrize("value", ["", "   ", None, 5, ["a"], {"a": 1}])
def test_unusable_provider_output_is_an_error_not_a_stored_reply(client, monkeypatch, value):
    t = teen(client)
    use(monkeypatch, Fixed(value))
    assert send(t, new_conv(t)).status_code == 502
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 0


def test_provider_output_is_cleaned_and_bounded(client, monkeypatch):
    t = teen(client)
    cid = new_conv(t)
    use(monkeypatch, Fixed("hello\x00\x07 there " + "z" * 5000))
    reply = send(t, cid).json()["reply"]["content"]
    assert len(reply) <= settings.AI_MAX_REPLY_CHARS and "\x00" not in reply and "\x07" not in reply and reply.startswith("hello there")


def test_a_slow_provider_times_out(client, monkeypatch):
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "1")
    t = teen(client)
    use(monkeypatch, Slow())
    started = time.time()
    assert send(t, new_conv(t)).status_code == 502
    assert time.time() - started < 2.9


# ---------- replay safety ----------
def test_a_replayed_message_is_not_stored_or_answered_twice(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    cid = new_conv(t)
    first = send(t, cid, "hello", client_id="msg-1").json()
    second = send(t, cid, "hello", client_id="msg-1").json()
    assert second["replayed"] is True and second["reply"] == first["reply"] and second["message"] == first["message"] and second["facts"] == first["facts"]
    assert len(rec.tutor) == 1
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 2
    assert send(t, cid, "hello again", client_id="msg-2").json()["message"]["seq"] == 3


def test_a_client_id_is_per_conversation(client):
    t = teen(client)
    a, b = new_conv(t), new_conv(t)
    assert send(t, a, "x", client_id="same").json()["replayed"] is False
    assert send(t, b, "x", client_id="same").json()["replayed"] is False


def test_a_client_id_cannot_replay_someone_elses_message(client, client2):
    a, b = teen(client, "a@example.com"), teen(client2, "b@example.com")
    ca, cb = new_conv(a), new_conv(b)
    send(a, ca, "secret", client_id="shared")
    r = send(b, cb, "mine", client_id="shared")
    assert r.status_code == 200 and r.json()["replayed"] is False and r.json()["message"]["content"] == "mine"


# ---------- children: bounded helper questions only, built-in provider only ----------
def test_a_child_gets_helper_questions(client):
    k = child(client)
    r = k.post("/api/tutor/conversations", json={})
    assert {q["key"] for q in r.json()["quick_prompts"]} == set(QUICK_PROMPTS)
    assert r.json()["conversation"]["mode"] == "child"


@pytest.mark.parametrize("body", [{"message": "tell me a story"}, {}, {"quick_prompt": "tell_me_a_story"}, {"quick_prompt": ""}, {"message": "hi", "quick_prompt": "teach_me_a_phrase"}])
def test_a_child_cannot_send_free_text(client, body):
    k = child(client)
    cid = new_conv(k)
    assert k.post(f"/api/tutor/conversations/{cid}/messages", json=body).status_code == 422
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 0


def test_a_child_helper_question_is_answered_from_the_built_in_provider_without_personal_facts(client, monkeypatch):
    rec = use(monkeypatch, Recorder())
    k = child(client)
    for a in activities(k)[:2]:
        answer(k, a["id"], wrong_options(a["id"])[0])
    cid = new_conv(k)
    r = k.post(f"/api/tutor/conversations/{cid}/messages", json={"quick_prompt": "teach_me_a_phrase"}).json()
    assert r["facts"] == [] and r["reply"]["provider"] == "mock" and "Here is a new phrase" in r["reply"]["content"] and rec.calls == 0       # the injected provider was never used
    assert r["message"]["content"] == QUICK_PROMPTS["teach_me_a_phrase"] and r["message"]["quick_prompt"] == "teach_me_a_phrase"
    again = k.post(f"/api/tutor/conversations/{cid}/messages", json={"quick_prompt": "what_does_it_mean"}).json()
    assert "means" in again["reply"]["content"] and k.post(f"/api/tutor/conversations/{cid}/messages", json={"quick_prompt": "say_it_again"}).json()["reply"]["content"].startswith("Say it slowly")


def test_a_child_never_reaches_an_external_model(client, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "llm")
    monkeypatch.setattr(main, "provider", lambda: "groq")
    async def boom(*a, **k):
        raise AssertionError("a child's request must never reach an external model")
    monkeypatch.setattr(main, "call_llm", boom)
    k = child(client)
    assert k.post(f"/api/tutor/conversations/{new_conv(k)}/messages", json={"quick_prompt": "teach_me_a_phrase"}).status_code == 200


def test_a_child_context_is_age_filtered(client):
    k = child(client)
    sit = next(s for s in k.get("/api/situations").json()["situations"])
    assert k.post("/api/tutor/conversations", json={"situation_id": sit["id"]}).status_code == 201


def test_a_learner_who_grows_up_can_use_free_text_in_an_old_conversation(client):
    k = child(client)
    cid = new_conv(k)
    assert k.post(f"/api/tutor/conversations/{cid}/messages", json={"message": "hi"}).status_code == 422
    k.put("/api/profile", json=profile(30))
    assert send(k, cid, "hi").status_code == 200


def test_a_learner_who_becomes_a_child_loses_free_text(client):
    t = teen(client)
    cid = new_conv(t)
    assert send(t, cid, "hi").status_code == 200
    t.put("/api/profile", json=profile(8))
    assert send(t, cid, "hi").status_code == 422 and t.post(f"/api/tutor/conversations/{cid}/messages", json={"quick_prompt": "teach_me_a_phrase"}).status_code == 200


# ---------- the optional real provider ----------
def test_the_llm_provider_is_used_for_teens_when_asked_for_and_configured(client, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "llm")
    seen = {}
    monkeypatch.setattr(main, "provider", lambda: "groq")

    async def fake(system, messages):
        seen["system"], seen["messages"] = system, messages
        return "Real model says hello \x00there"
    monkeypatch.setattr(main, "call_llm", fake)
    t = teen(client)
    t.post("/api/confidence", json={"topic": "food", "score": 30})
    body = send(t, new_conv(t), "How do I order food?").json()
    assert body["reply"]["provider"] == "llm" and body["reply"]["content"] == "Real model says hello there"
    assert "Hindi" in seen["system"] and "A1" in seen["system"] and "Self-rated confidence in" in seen["system"] and "Never reveal" in seen["system"]
    assert seen["messages"][-1] == {"role": "user", "content": "How do I order food?"} and seen["messages"][0]["role"] == "user"
    assert "@example.com" not in json.dumps(seen)


def test_asking_for_the_llm_without_a_key_falls_back_to_the_built_in_provider(client, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "llm")
    monkeypatch.setattr(main, "provider", lambda: None)
    t = teen(client)
    assert send(t, new_conv(t)).json()["reply"]["provider"] == "mock"


def test_a_failing_llm_is_a_clean_error(client, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "llm")
    monkeypatch.setattr(main, "provider", lambda: "groq")

    async def broken(system, messages):
        raise RuntimeError("secret upstream detail sk-12345")
    monkeypatch.setattr(main, "call_llm", broken)
    t = teen(client)
    r = send(t, new_conv(t))
    assert r.status_code == 502 and "sk-12345" not in r.text and "upstream" not in r.text


def test_the_llm_adapter_formats_its_request(monkeypatch):
    from backend.ai.base import TutorRequest
    captured = {}

    async def fake(system, messages):
        captured["system"], captured["messages"] = system, messages
        return "ok"
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", fake)
    req = TutorRequest(mode="adult", language="Hindi", cefr="A2", message="q", facts=("f1", "f2"), history=(("tutor", "first"), ("learner", "a"), ("tutor", "b")))
    assert llm.LLMProvider().tutor_reply(req) == "ok"
    assert "- f1" in captured["system"] and "- f2" in captured["system"]
    assert captured["messages"] == [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}, {"role": "user", "content": "q"}]       # starts with the user


def test_provider_selection_rules(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setattr(main, "provider", lambda: "groq")
    assert registry.configured().name == "mock"
    monkeypatch.setenv("AI_PROVIDER", "nonsense")
    assert registry.configured().name == "mock"
    monkeypatch.setenv("AI_PROVIDER", "LLM")
    assert registry.configured().name == "llm"
    monkeypatch.setattr(main, "provider", lambda: None)
    assert registry.configured().name == "mock"
    assert registry.offline().name == "mock"


# ---------- the schema ----------
def test_tutor_constraints(client):
    import sqlite3
    t = teen(client)
    cid = new_conv(t)
    with db() as conn:
        uid = conn.execute("SELECT user_id FROM tutor_conversations WHERE id = ?", (cid,)).fetchone()[0]
        ins = "INSERT INTO tutor_messages(conversation_id, user_id, seq, role, content, provider, created_at) VALUES (?, ?, ?, ?, ?, ?, 't')"
        conn.execute(ins, (cid, uid, 1, "learner", "x", None))
        for args in ((cid, uid, 1, "learner", "dup seq", None), (cid, uid, 2, "tutor", "no provider", None), (cid, uid, 3, "learner", "has provider", "mock"),
                     (cid, uid, 4, "robot", "bad role", None), (cid, uid, 0, "learner", "bad seq", None), (cid, uid, 5, "learner", "   ", None), (cid, uid, 6, "learner", "x" * 2001, None)):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(ins, args)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE tutor_conversations SET message_count = 201 WHERE id = ?", (cid,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE tutor_conversations SET lesson_id = 1, situation_id = 1 WHERE id = ?", (cid,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO tutor_message_facts VALUES (?, 9, 'weakness', 'x')", (1,))
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 0 and conn.execute("SELECT COUNT(*) FROM tutor_conversations").fetchone()[0] == 0


def test_a_full_conversation_does_not_call_the_provider(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_MAX_MESSAGES_PER_CONVERSATION", 2)
    rec = use(monkeypatch, Recorder())
    t = teen(client)
    cid = new_conv(t)
    assert send(t, cid).status_code == 200
    assert send(t, cid).status_code == 409 and len(rec.tutor) == 1


def test_a_child_prompt_carries_no_learner_facts(client, monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(registry, "offline", lambda: rec)
    k = child(client)
    for _ in range(3):
        for a in activities(k)[:6]:
            answer(k, a["id"], wrong_options(a["id"])[0])
    k.post("/api/confidence", json={"topic": "food", "score": 20})
    k.post(f"/api/tutor/conversations/{new_conv(k)}/messages", json={"quick_prompt": "teach_me_a_phrase"})
    assert rec.tutor[-1].facts == () and rec.tutor[-1].mode == "child" and rec.tutor[-1].quick_prompt == "teach_me_a_phrase"


def test_a_topic_without_content_for_the_age_group_is_refused(client, client2):
    k, t = child(client), teen(client2, "t@example.com")
    assert t.post("/api/tutor/conversations", json={"topic": "college"}).status_code == 201
    assert k.post("/api/tutor/conversations", json={"topic": "college"}).status_code == 422


def test_the_llm_adapter_keeps_the_answer_secret_until_it_is_allowed(monkeypatch):
    from backend.ai.base import RoleplayFeedbackRequest, RoleplayTurnRequest
    seen = []

    async def fake(system, messages):
        seen.append((system, messages))
        return '{"vocabulary_feedback": "v", "grammar_feedback": "g", "hint": "h", "encouragement": "e", "next_step": "n"}' if "JSON" in system else "In character."
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", fake)
    sit = {"title": "Auto", "partner_name": "Raju", "partner_role": "driver", "setting": "Gate", "goal": "go"}
    base = dict(mode="adult", language="Hindi", cefr="A1", situation=sit, objective="o", learner_text="my reply", verdict="incorrect", attempt_no=1, hint="It is 3 words long.")
    p = llm.LLMProvider()
    assert p.roleplay_reply(RoleplayTurnRequest(**base, revealed=None)) == "In character."
    open_system = seen[-1][0]
    assert "Do NOT reveal" in open_system and "model answer" not in open_system and "It is 3 words long." in open_system and "Raju" in open_system
    assert seen[-1][1] == [{"role": "user", "content": "my reply"}]
    p.roleplay_reply(RoleplayTurnRequest(**{**base, "verdict": "correct", "hint": None}, revealed="Namaste", next_objective="Ask the price"))
    assert "Do NOT reveal" not in seen[-1][0] and "Namaste" in seen[-1][0] and "Ask the price" in seen[-1][0]
    fb = p.roleplay_feedback(RoleplayFeedbackRequest("adult", "Hindi", "A1", sit, 7, 5, 2, 3, missed=({"objective": "o", "answer": "Namaste"},)))
    assert fb["next_step"] == "n" and "no pronunciation data" in seen[-1][0] and "Namaste" in seen[-1][0]

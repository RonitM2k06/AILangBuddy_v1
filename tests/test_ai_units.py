"""Units under the AI features: output cleaning, the deterministic built-in provider, the repository scoping, and the bounded-prompt helper."""
import pytest

from backend import settings
from backend.ai.base import AiError, FEEDBACK_FIELDS, RoleplayFeedbackRequest, RoleplayTurnRequest, TutorRequest, clean, clean_feedback
from backend.ai.mock import MockProvider, QUICK_PROMPTS
from backend.ai import runner
from backend.db import connect
from backend.repositories import roleplay as rp_repo, tutor as tutor_repo
from backend.tutor import service as tutor_service

PHRASES = ({"text": "नमस्ते", "pronunciation": "Namaste", "meaning": "Hello"}, {"text": "धन्यवाद", "pronunciation": "Dhanyavaad", "meaning": "Thank you"})


# ---------- clean ----------
def test_clean_strips_control_characters_trims_and_truncates():
    assert clean("  hi\x00 there\x07 ") == "hi there"
    assert clean("a\nb") == "a\nb"
    assert len(clean("x" * 5000)) == settings.AI_MAX_REPLY_CHARS
    assert clean("x" * 50, 10) == "x" * 10


@pytest.mark.parametrize("bad", ["", "   ", "\x00\x01", None, 5, ["x"], {"a": 1}, b"bytes"])
def test_clean_rejects_unusable_output(bad):
    with pytest.raises(AiError):
        clean(bad)


def test_clean_feedback_needs_every_field():
    good = {k: f"text {k}" for k in FEEDBACK_FIELDS}
    assert clean_feedback(good) == good
    for k in FEEDBACK_FIELDS:
        with pytest.raises(AiError):
            clean_feedback({kk: v for kk, v in good.items() if kk != k})
    with pytest.raises(AiError):
        clean_feedback("text")
    assert all(len(v) <= 400 for v in clean_feedback({k: "z" * 900 for k in FEEDBACK_FIELDS}).values())


def test_the_runner_turns_any_failure_into_a_safe_error():
    assert runner.run(lambda x: x + 1, 1) == 2
    with pytest.raises(AiError) as e:
        runner.run(lambda: 1 / 0)
    assert e.value.code == "provider_error"
    with pytest.raises(AiError) as e:
        runner.run(lambda: (_ for _ in ()).throw(AiError("empty_response")))
    assert e.value.code == "empty_response"


# ---------- the built-in provider ----------
def tutor(**kw):
    base = dict(mode="teen", language="Hindi", cefr="A1", message="hello", facts=(), history=(), phrases=PHRASES)
    return TutorRequest(**{**base, **kw})


def test_the_built_in_tutor_is_deterministic_and_labels_facts_apart_from_advice():
    p = MockProvider()
    req = tutor(message="I need a hint", facts=("Weak topic: Food (1 of 6 answers were correct)",), context_title="Food")
    a = p.tutor_reply(req)
    assert a == p.tutor_reply(req) and a.startswith("From your records: Weak topic: Food")
    assert "Advice (generated, not a record):" in a and "in “Food”" in a and "level A1" in a


@pytest.mark.parametrize("message,needle", [("any hint?", "one phrase at a time"), ("why was it wrong", "first word that differs"), ("how do I pronounce it", "Speaking out loud"),
                                            ("hello there", "short daily session")])
def test_the_built_in_tutor_reads_the_intent(message, needle):
    assert needle in MockProvider().tutor_reply(tutor(message=message))


def test_the_built_in_tutor_never_invents_records():
    reply = MockProvider().tutor_reply(tutor(facts=()))
    assert "I don't have any practice records for you yet" in reply
    assert "%" not in reply and "correct" not in reply.split("Advice")[0]


def test_the_built_in_tutor_cycles_through_phrases():
    p = MockProvider()
    assert "Namaste" in p.tutor_reply(tutor(turn_index=0)) and "Dhanyavaad" in p.tutor_reply(tutor(turn_index=1)) and "Namaste" in p.tutor_reply(tutor(turn_index=2))


def test_child_helper_replies():
    p = MockProvider()
    assert "Here is a new phrase" in p.tutor_reply(tutor(mode="child", quick_prompt="teach_me_a_phrase", turn_index=0, message="x"))
    assert p.tutor_reply(tutor(mode="child", quick_prompt="say_it_again", turn_index=1)).startswith("Say it slowly: Namaste")
    assert p.tutor_reply(tutor(mode="child", quick_prompt="what_does_it_mean", turn_index=1)) == "नमस्ते means “Hello”."
    assert "don't have a new phrase" in p.tutor_reply(tutor(mode="child", phrases=(), quick_prompt="teach_me_a_phrase"))
    assert set(QUICK_PROMPTS) == {"teach_me_a_phrase", "say_it_again", "what_does_it_mean"}


def turn_req(**kw):
    base = dict(mode="teen", language="Hindi", cefr="A1", situation={"title": "Auto", "partner_name": "Raju", "partner_role": "driver", "setting": "x", "goal": "y"},
                objective="Say hello", learner_text="x", verdict="incorrect", attempt_no=1, hint="It is 2 words long.", revealed=None)
    return RoleplayTurnRequest(**{**base, **kw})


def test_the_built_in_character_voices_the_servers_verdict():
    p = MockProvider()
    assert p.roleplay_reply(turn_req()) == "Raju: Hmm, I didn't quite catch that. It is 2 words long."
    assert p.roleplay_reply(turn_req(verdict="correct", hint=None, attempt_no=2, next_objective="Ask the price")) == "Raju: Bilkul theek! That works. Next: Ask the price"
    assert p.roleplay_reply(turn_req(verdict="correct", hint=None, next_objective=None)).endswith("That was the last one!")
    assert p.roleplay_reply(turn_req(revealed="Namaste", hint=None, attempt_no=3)) == "Raju: No worries, let's move on. A natural way to say it: Namaste"
    assert p.roleplay_reply(turn_req(situation={"title": "t", "partner_name": None})).startswith("Helper:")


def test_the_built_in_feedback_uses_only_the_evidence():
    p = MockProvider()
    sit = {"title": "Auto"}
    perfect = p.roleplay_feedback(RoleplayFeedbackRequest("teen", "Hindi", "A1", sit, 7, 7, 0, 7))
    assert "every step" in perfect["vocabulary_feedback"] and "Excellent" in perfect["encouragement"] and "another situation" in perfect["next_step"]
    mixed = p.roleplay_feedback(RoleplayFeedbackRequest("teen", "Hindi", "A1", sit, 7, 5, 2, 3, missed=({"objective": "o", "answer": "Namaste"},)))
    assert "Namaste" in mixed["vocabulary_feedback"] and "Good effort" in mixed["encouragement"] and "again" in mixed["next_step"]
    poor = p.roleplay_feedback(RoleplayFeedbackRequest("teen", "Hindi", "A1", sit, 7, 1, 6, 0))
    assert "hard at first" in poor["encouragement"]
    assert "can't judge grammar" in perfect["grammar_feedback"]
    assert "pronunciation" not in " ".join(perfect.values()).lower()


# ---------- the bounded prompt ----------
def test_bounded_drops_the_oldest_history_first():
    hist = tuple(("learner" if i % 2 == 0 else "tutor", f"{i}:" + "z" * 400) for i in range(10))
    req = tutor(history=hist, message="m")
    out = tutor_service._bounded(req)
    assert out.history == hist                                                         # fits: nothing dropped
    old = settings.AI_MAX_PROMPT_CHARS
    try:
        settings.AI_MAX_PROMPT_CHARS = 1000
        out = tutor_service._bounded(req)
        assert 0 < len(out.history) < 10 and out.history == hist[-len(out.history):]
        assert len(out.message) + sum(len(t) for _, t in out.history) + sum(len(p["text"]) + len(p["meaning"]) + len(p["pronunciation"]) for p in out.phrases) <= 1000
    finally:
        settings.AI_MAX_PROMPT_CHARS = old


# ---------- repositories are scoped by owner ----------
def test_repositories_never_return_another_learners_rows(db_path):
    with connect(db_path) as conn:
        a, b = [conn.execute("INSERT INTO users(handle, display_name) VALUES (?, ?)", (f"u{i}", f"U{i}")).lastrowid for i in range(2)]
        lang = conn.execute("SELECT id FROM languages WHERE code = 'hi'").fetchone()[0]
        cid = tutor_repo.create_conversation(conn, a, lang, "A1", "teen", None, None, None, "t", "2026-09-01 09:00:00")
        mid = tutor_repo.insert_message(conn, cid, a, 1, "tutor", "reply", None, None, "mock", "2026-09-01 09:00:00")
        tutor_repo.insert_message(conn, cid, a, 2, "learner", "mine", None, "cid-1", None, "2026-09-01 09:00:01")
        tutor_repo.insert_facts(conn, mid, [("context", "fact")])
        assert tutor_repo.get_conversation(conn, a, cid) and tutor_repo.get_conversation(conn, b, cid) is None
        assert tutor_repo.list_conversations(conn, b, 10) == [] and tutor_repo.list_messages(conn, b, cid, 0, 10) == [] and tutor_repo.last_messages(conn, b, cid, 5) == []
        assert tutor_repo.facts_for(conn, b, mid) == [] and tutor_repo.facts_for(conn, a, mid) == [{"kind": "context", "text": "fact"}]
        assert tutor_repo.find_by_client_id(conn, b, cid, "cid-1") is None and tutor_repo.find_by_client_id(conn, a, cid, "cid-1")
        assert tutor_repo.count_conversations(conn, b) == 0 and tutor_repo.count_learner_messages(conn, b, cid) == 0 and tutor_repo.count_learner_messages(conn, a, cid) == 1
        assert tutor_repo.bump(conn, b, cid, 2, 100, "t") is False and tutor_repo.bump(conn, a, cid, 2, 100, "t") is True
        assert tutor_repo.bump(conn, a, cid, 2, 3, "t") is False                      # over the cap: refused
        sit = conn.execute("SELECT id, language_id FROM situations LIMIT 1").fetchone()
        rid = rp_repo.create_session(conn, a, sit["id"], sit["language_id"], "A1", "teen", 5, "2026-09-01 09:00:00")
        assert rp_repo.get_session(conn, a, rid) and rp_repo.get_session(conn, b, rid) is None
        assert rp_repo.list_sessions(conn, b, 10) == [] and rp_repo.turns(conn, b, rid) == [] and rp_repo.get_feedback(conn, b, rid) is None
        assert rp_repo.complete_session(conn, b, rid, 1, 4, "t") is False and rp_repo.complete_session(conn, a, rid, 1, 4, "t") is True
        assert rp_repo.complete_session(conn, a, rid, 1, 4, "t") is False             # once


# ---------- each guard holds on its own ----------
def _two_users_with_a_roleplay(conn):
    a, b = [conn.execute("INSERT INTO users(handle, display_name) VALUES (?, ?)", (f"r{i}", f"R{i}")).lastrowid for i in range(2)]
    sit = conn.execute("SELECT id, language_id FROM situations WHERE slug = 'emergency' AND language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()
    steps = [r[0] for r in conn.execute("SELECT id FROM situation_steps WHERE situation_id = ? ORDER BY sort_order", (sit["id"],))]
    rid = rp_repo.create_session(conn, a, sit["id"], sit["language_id"], "A1", "teen", len(steps), "2026-09-01 09:00:00")
    return a, b, sit, steps, rid


def test_roleplay_turns_feedback_and_resume_are_scoped_to_their_owner(db_path):
    with connect(db_path) as conn:
        a, b, sit, steps, rid = _two_users_with_a_roleplay(conn)
        rp_repo.insert_turn(conn, rid, a, sit["id"], steps[0], 1, 1, "hello", "text", None, "correct", "correct", None, "reply", "mock", "cid-1", "2026-09-01 09:00:01")
        assert len(rp_repo.turns(conn, a, rid)) == 1 and rp_repo.turns(conn, b, rid) == []
        assert rp_repo.find_turn_by_client_id(conn, a, rid, "cid-1") and rp_repo.find_turn_by_client_id(conn, b, rid, "cid-1") is None
        assert rp_repo.get_active_for_situation(conn, a, sit["id"]) == rid and rp_repo.get_active_for_situation(conn, b, sit["id"]) is None
        rp_repo.complete_session(conn, a, rid, 1, 6, "2026-09-01 09:10:00")
        f = {"steps_total": 7, "steps_correct": 1, "steps_missed": 6, "first_try_correct": 1, "voice_turns": 0, "correctness_text": "x", "vocabulary_feedback": "v",
             "grammar_feedback": "g", "hint": "h", "encouragement": "e", "next_step": "n", "pronunciation_note": "p", "provider": "mock"}
        rp_repo.insert_feedback(conn, rid, a, f, "t")
        assert rp_repo.get_feedback(conn, a, rid)["steps_correct"] == 1 and rp_repo.get_feedback(conn, b, rid) is None


def test_the_ledger_does_not_offer_a_credited_situation_again(db_path):
    from backend.repositories import gamification as game
    with connect(db_path) as conn:
        a, b, sit, steps, rid = _two_users_with_a_roleplay(conn)
        rp_repo.complete_session(conn, a, rid, 5, 2, "2026-09-01 09:10:00")
        offered = [s for s in game.uncredited_sources(conn, a) if s["kind"] == "situation"]
        assert [s["source_id"] for s in offered] == [sit["id"]] and game.uncredited_sources(conn, b) == []
        game.insert_event(conn, a, "situation", sit["id"], 25, "2026-09-01 09:10:00", "2026-09-01", "t")
        assert [s for s in game.uncredited_sources(conn, a) if s["kind"] == "situation"] == []


def test_schema_refuses_replays_and_inconsistent_roleplay_rows(db_path):
    import sqlite3
    with connect(db_path) as conn:
        a, b, sit, steps, rid = _two_users_with_a_roleplay(conn)
        lang = conn.execute("SELECT id FROM languages WHERE code = 'hi'").fetchone()[0]
        cid = tutor_repo.create_conversation(conn, a, lang, "A1", "teen", None, None, None, "t", "2026-09-01 09:00:00")
        tutor_repo.insert_message(conn, cid, a, 1, "learner", "one", None, "same", None, "t")
        with pytest.raises(sqlite3.IntegrityError):
            tutor_repo.insert_message(conn, cid, a, 3, "learner", "again", None, "same", None, "t")                   # a replayed client id is not a new message
        rp_repo.insert_turn(conn, rid, a, sit["id"], steps[0], 1, 1, "x", "text", None, "incorrect", "no", "h", "r", "mock", "t1", "t")
        with pytest.raises(sqlite3.IntegrityError):
            rp_repo.insert_turn(conn, rid, a, sit["id"], steps[0], 2, 2, "x", "text", None, "incorrect", "no", "h", "r", "mock", "t1", "t")      # nor a replayed turn
        ins = ("INSERT INTO roleplay_turns(session_id, user_id, situation_id, step_id, turn_no, attempt_no, learner_text, input_mode, speaking_session_id, verdict, resolved, "
               "character_reply, provider, created_at) VALUES (?, ?, ?, ?, 5, 1, 'x', ?, ?, 'incorrect', 'no', 'r', 'mock', 't')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(ins, (rid, a, sit["id"], steps[0], "voice", None))                                         # voice without a spoken session
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(ins, (rid, a, sit["id"], steps[0], "text", 1))                                             # text with one
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE roleplay_sessions SET status = 'completed', completed_at = 't' WHERE id = ?", (rid,))      # completed without counts
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE roleplay_sessions SET steps_correct = 3, steps_missed = 4 WHERE id = ?", (rid,))          # counts on an active session

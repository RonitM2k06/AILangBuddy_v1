"""Mumbai's Marathi learning, end to end on the server: the curriculum through A2 (0031, 0032), server roleplays and listening (0033), speaking
capabilities, Marathi answer grading, and the content review record (0034). Hindi is checked alongside wherever a shared path changed, so a
Marathi rule can never leak into Hindi. Everything runs on the test database with the built-in (offline) providers: no network."""
import json
import re

import pytest

from backend import main, settings
from backend.adaptive import lexicon, semantic
from backend.ai import registry
from backend.ai.mock import MockProvider
from backend.db import connect
from backend.speaking import service as speaking_service, stt
from backend.textnorm import answer_key, normalize

from .adm import admin, ok  # noqa: F401  (admin: fixture)
from .conftest import register

MR = "(SELECT id FROM languages WHERE code = 'mr')"
HI = "(SELECT id FROM languages WHERE code = 'hi')"
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
HINDI_ROMAN = re.compile(r"\b(hai|hain|kya|kahan|kidhar|mujhe|chahiye|kitna|dijiye|bhaiya|achha|accha|shukriya|namaste)\b", re.I)
HINDI_DEVA = ("है", "क्या", "कहाँ", "मुझे", "चाहिए", "कितना", "दीजिए", "भैया", "।")
A1_SLUGS = ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk", "numbers-money", "time-days", "about-me", "help-health"]
A2_SLUGS = ["yesterday", "plans", "favours", "likes", "comparing", "travel", "shop-problems", "work-study", "home-problems", "long-conversation"]


def db():
    return connect(main.DB_PATH)


def learner(client, email, level="A1", dob="2000-05-20", target="mr"):
    register(client, email)
    r = client.put("/api/profile", json={"native_language": "en", "target_language": target, "cefr_level": level, "date_of_birth": dob})
    assert r.status_code == 200, r.text
    return client


# =====================================================================================================================
# the curriculum through A2
# =====================================================================================================================
def test_the_curriculum_counts_by_level(client):
    with db() as conn:
        def count(sql):
            return dict(conn.execute(sql).fetchall())
        assert count(f"SELECT cefr_code, COUNT(*) FROM lessons WHERE language_id = {MR} AND status = 'published' GROUP BY cefr_code") == {"A1": 11, "A2": 10, "B1": 6}
        assert count(f"SELECT l.cefr_code, COUNT(*) FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE e.language_id = {MR} GROUP BY l.cefr_code") == {"A1": 33, "A2": 30, "B1": 18}
        assert count(f"SELECT cefr_code, COUNT(*) FROM grammar_topics WHERE language_id = {MR} GROUP BY cefr_code") == {"A1": 4, "A2": 5, "B1": 5}
        assert count(f"SELECT cefr_code, COUNT(*) FROM situations WHERE language_id = {MR} AND status = 'published' GROUP BY cefr_code") == {"A1": 8, "A2": 4, "B1": 2}
        assert count(f"SELECT cefr_code, COUNT(*) FROM listening_activities WHERE language_id = {MR} AND status = 'published' GROUP BY cefr_code") == {"A1": 22, "A2": 20, "B1": 12}
        kinds = count(f"SELECT kind, COUNT(*) FROM exercises WHERE language_id = {MR} GROUP BY kind")
        assert kinds == {"multiple_choice": 27, "translation": 27, "fill_blank": 27}
        for (lid,) in conn.execute(f"SELECT id FROM lessons WHERE language_id = {MR}"):
            ks = {r[0] for r in conn.execute("SELECT kind FROM exercises WHERE lesson_id = ?", (lid,))}
            assert ks == {"multiple_choice", "translation", "fill_blank"}, lid          # every lesson: meaning, translation, a missing word
            assert conn.execute("SELECT COUNT(*) FROM lesson_vocabulary WHERE lesson_id = ?", (lid,)).fetchone()[0] >= 6


def test_an_a2_learner_gets_both_levels_in_order_and_an_a1_learner_only_a1(client, client2):
    a2 = learner(client, "a2@example.com", level="A2")
    got = a2.get("/api/lessons").json()["lessons"]
    assert [l["slug"] for l in got] == A1_SLUGS + A2_SLUGS and [l["cefr_level"] for l in got] == ["A1"] * 11 + ["A2"] * 10
    a1 = learner(client2, "a1@example.com", level="A1")
    assert [l["slug"] for l in a1.get("/api/lessons").json()["lessons"]] == A1_SLUGS


def test_the_marathi_content_is_marathi(client):
    """No Hindi words, no Hindi danda, no Hindi item in a Marathi lesson, situation or listening activity (the database also forbids it)."""
    with db() as conn:
        rows = conn.execute(f"SELECT text, pronunciation FROM vocabulary_items WHERE language_id = {MR}").fetchall()
        prompts = [r[0] for r in conn.execute(f"SELECT prompt FROM situation_steps WHERE language_id = {MR} AND kind IN ('choose_response', 'conversation') AND prompt NOT LIKE 'You %'")]
        answers = [r[0] for r in conn.execute(f"SELECT a.answer_text FROM situation_step_answers a JOIN situation_steps s ON s.id = a.step_id WHERE s.language_id = {MR}")]
    assert len(rows) == 199                                                            # A1 82, A2 73, B1 44
    for text, roman in rows:
        assert DEVANAGARI.search(text) and roman, text
        assert not any(h in text for h in HINDI_DEVA), text
        assert not HINDI_ROMAN.search(roman), roman
    for line in prompts + answers:
        assert not HINDI_ROMAN.search(line), line


def test_an_a2_lesson_teaches_its_grammar_and_both_gendered_forms(client):
    a2 = learner(client, "a2@example.com", level="A2")
    lid = next(l["id"] for l in a2.get("/api/lessons").json()["lessons"] if l["slug"] == "yesterday")
    lesson = a2.get(f"/api/lessons/{lid}").json()["lesson"]
    assert [g["title"] for g in lesson["grammar"]] == ["The past: “gelo / gele” and “kela”"]
    phrases = {v["pronunciation"]: v for v in lesson["vocabulary"] if v["kind"] == "phrase"}
    assert "Kaal mi Juhula gelo hoto." in phrases and phrases["Kaal mi Juhula gele hote."]["meaning"].endswith("(said by a woman)")


def test_the_office_lessons_and_situation_are_not_for_children(client):
    kid = learner(client, "kid@example.com", level="A2", dob="2018-01-01")
    slugs = [l["slug"] for l in kid.get("/api/lessons").json()["lessons"]]
    assert "college" not in slugs and "work-study" not in slugs and len(slugs) == 19
    assert "college" not in [s["slug"] for s in kid.get("/api/situations").json()["situations"]]


def test_a_lesson_is_completed_only_when_every_exercise_is_right(client):
    c = learner(client, "done@example.com", level="A2")
    lid = next(l["id"] for l in c.get("/api/lessons").json()["lessons"] if l["slug"] == "travel")
    exercises = c.get(f"/api/lessons/{lid}").json()["lesson"]["exercises"]
    for n, ex in enumerate(exercises):
        if ex["kind"] == "multiple_choice":
            with db() as conn:
                aid = conn.execute("SELECT id FROM exercise_answers WHERE exercise_id = ? AND is_correct = 1", (ex["id"],)).fetchone()[0]
            r = c.post(f"/api/exercises/{ex['id']}/attempts", json={"answer_id": aid})
        else:
            with db() as conn:
                key = conn.execute("SELECT answer_text FROM exercise_answers WHERE exercise_id = ? AND is_correct = 1", (ex["id"],)).fetchone()[0]
            r = c.post(f"/api/exercises/{ex['id']}/attempts", json={"text": key})
        status = r.json()["lesson_progress"]["status"]
        assert status == ("completed" if n == len(exercises) - 1 else "in_progress"), (n, status)


# =====================================================================================================================
# grading typed answers
# =====================================================================================================================
def _exercise(lesson_slug, kind):
    with db() as conn:
        return conn.execute(f"SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = ? AND l.language_id = {MR} AND e.kind = ?",
                            (lesson_slug, kind)).fetchone()[0]


@pytest.mark.parametrize("typed,correct", [
    ("Don tikita dya.", True), ("don tikita dya", True), ("DON TIKITA DYA!!", True), ("  Don   tikita, dya. ", True),   # case, punctuation, spaces
    ("दोन तिकिटं द्या.", True), ("दोन तिकिटं द्या", True),                                                      # Devanagari
    ("Don tikitaa dyaa.", True), ("Donn tikita dya", True),                                                      # documented romanisation variants
    ("Do ticket dena.", False), ("Don tikita.", False), ("Tikita dya.", False), ("Teen tikita dya.", False),       # Hindi, incomplete, wrong number
])
def test_a_marathi_translation_accepts_documented_variants_and_nothing_else(client, typed, correct):
    c = learner(client, "grade@example.com", level="A2")
    r = c.post(f"/api/exercises/{_exercise('travel', 'translation')}/attempts", json={"text": typed})
    assert r.status_code == 200 and r.json()["correct"] is correct, typed


@pytest.mark.parametrize("typed,correct", [("zhale", True), ("jhale", True), ("zale", True), ("Zhale.", True), ("zala", False), ("hua", False)])
def test_zh_jh_and_z_are_one_letter_in_romanised_marathi(client, typed, correct):
    c = learner(client, "zh@example.com")
    with db() as conn:
        lid = conn.execute(f"SELECT id FROM lessons WHERE slug = 'food' AND language_id = {MR}").fetchone()[0]
        ex = conn.execute("SELECT id FROM exercises WHERE lesson_id = ? AND kind = 'fill_blank'", (lid,)).fetchone()[0]
    assert c.post(f"/api/exercises/{ex}/attempts", json={"text": typed}).json()["correct"] is correct


@pytest.mark.parametrize("body,field", [({"text": ""}, "text"), ({"text": "   "}, "text"), ({"text": "x" * 501}, "text"), ({}, "text"),
                                        ({"text": "Don tikita dya.", "answer_id": 1}, "text")])
def test_bad_answers_are_refused(client, body, field):
    c = learner(client, "bad@example.com", level="A2")
    r = c.post(f"/api/exercises/{_exercise('travel', 'translation')}/attempts", json=body)
    assert r.status_code == 422


def test_hindi_answers_are_still_compared_exactly():
    """The Marathi folding never applies to Hindi: Hindi's key is exactly the old normalisation."""
    for text in ("Kitne paise honge?", "Kitney paise honge", "Namastey", "नमस्ते, आप कैसे हैं?", "Jhaal", "zaroor"):
        assert answer_key(text, "hi") == normalize(text) == answer_key(text, None)
    assert answer_key("Kitne paise honge", "hi") != answer_key("Kitney paise honge", "hi")
    assert answer_key("jhale", "mr") == answer_key("zale", "mr") == answer_key("zhale", "mr")


def test_a_hindi_exercise_still_refuses_a_variant_spelling(client):
    c = learner(client, "hindi@example.com", target="hi")
    with db() as conn:
        ex = conn.execute(f"SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = 'greetings' AND l.language_id = {HI} AND e.kind = 'translation'").fetchone()[0]
    assert c.post(f"/api/exercises/{ex}/attempts", json={"text": "Namaste, aap kaise hain?"}).json()["correct"] is True
    assert c.post(f"/api/exercises/{ex}/attempts", json={"text": "Namastey, aap kaisey hain?"}).json()["correct"] is False


# ---------- the semantic grader (roleplay) ----------
@pytest.mark.parametrize("said,accepted,match", [
    ("kuthe ahe station?", "Station kuthe aahe?", True),                  # word order, a long vowel, a function word
    ("Station kute aahe", "Station kuthe aahe?", True),                   # a documented spelling variant
    ("स्टेशन कुठं आहे?", "स्टेशन कुठे आहे?", True),                          # Devanagari variant
    ("Ek cutting chaha dya", "Ek cutting chaha.", True),                  # a polite extra word ("dya" is one of three key words more)
    ("Station kahan hai?", "Station kuthe aahe?", False),                 # Hindi is not Marathi
    ("Ek vadapav", "Shevatcha bhaav sanga.", False),                      # a different idea
    ("aahe aahe aahe", "Station kuthe aahe?", False),                     # function words alone mean nothing
])
def test_the_marathi_semantic_grader(said, accepted, match):
    g = semantic.grade("mr", said, [accepted])
    assert g.supported and g.semantic_match is match, (said, g)


def test_marathi_and_hindi_lexicons_are_separate():
    assert lexicon.SUPPORTED == {"hi", "mr", "kn", "ta", "fr", "bn", "te", "ur", "ks", "doi"} and lexicon.for_language("es") is None   # kn, ta, fr: their own learning tests
    assert semantic.grade("es", "metro", ["metro"]).supported is False
    assert not semantic.grade("hi", "Station kuthe aahe", ["Station kahan hai?"]).semantic_match     # Marathi words are not Hindi synonyms
    hi, mr = lexicon.for_language("hi"), lexicon.for_language("mr")
    assert hi.stop_roman == lexicon.STOP_ROMAN_CANON and hi.group_roman == lexicon.GROUP_ROMAN       # Hindi's data is exactly what it was
    assert "aahe" not in {w for w in lexicon.STOP_ROMAN} and mr.canon_roman("zhale") == mr.canon_roman("jhale")


# =====================================================================================================================
# server roleplays (situations)
# =====================================================================================================================
def _start(c, slug):
    with db() as conn:
        sid = conn.execute(f"SELECT id FROM situations WHERE slug = ? AND language_id = {MR}", (slug,)).fetchone()[0]
    r = c.post("/api/roleplay/sessions", json={"situation_id": sid})
    assert r.status_code in (200, 201), r.text
    return r.json()["session"]


def _key(slug):
    with db() as conn:
        sid = conn.execute(f"SELECT id FROM situations WHERE slug = ? AND language_id = {MR}", (slug,)).fetchone()[0]
        out = []
        for st in conn.execute("SELECT id, kind, item_id FROM situation_steps WHERE situation_id = ? ORDER BY sort_order", (sid,)).fetchall():
            if st["kind"] == "learn_phrase":
                out.append(conn.execute("SELECT pronunciation FROM vocabulary_items WHERE id = ?", (st["item_id"],)).fetchone()[0])
            else:
                out.append(conn.execute("SELECT answer_text FROM situation_step_answers WHERE step_id = ? AND is_correct = 1 ORDER BY sort_order", (st["id"],)).fetchone()[0])
        return out


def test_a_marathi_learner_discovers_marathi_situations_only(client, client2):
    a2 = learner(client, "rp@example.com", level="A2")
    got = a2.get("/api/situations").json()["situations"]
    with db() as conn:
        ids = {r[0] for r in conn.execute(f"SELECT id FROM situations WHERE language_id = {MR} AND cefr_code IN ('A1', 'A2')")}
    assert {s["id"] for s in got} == ids and len(got) == 12                              # B1 is above an A2 learner's level
    hindi = learner(client2, "hindi@example.com", target="hi")
    assert all(s["id"] not in ids for s in hindi.get("/api/situations").json()["situations"])
    with db() as conn:
        hindi_sid = conn.execute(f"SELECT id FROM situations WHERE language_id = {HI} LIMIT 1").fetchone()[0]
    assert a2.post("/api/roleplay/sessions", json={"situation_id": hindi_sid}).status_code == 404


def test_a_marathi_roleplay_runs_offline_in_marathi_from_start_to_feedback(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())                     # the built-in provider: no network
    c = learner(client, "taxi@example.com")
    s = _start(c, "transport")
    assert "Shinde kaka: Namaskar!" in s["scene"] and "Namaste" not in s["scene"]
    assert s["current"]["objective"].startswith("Say this in Marathi: “")
    replies = []
    for n, answer in enumerate(_key("transport")):
        variant = answer.lower().replace("aa", "a") if n == 0 else answer                 # the first in a romanisation variant
        r = c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": variant})
        assert r.status_code == 200 and r.json()["turn"]["verdict"] == "correct", (variant, r.text)
        replies.append(r.json()["turn"]["character"])
    assert any(p in " ".join(replies) for p in ("Chhan!", "Ekdum barobar!", "Shabbas!"))
    for hindi in ("Achha", "Bilkul", "Shabaash", "Namaste"):
        assert hindi not in " ".join(replies), hindi
    done = c.post(f"/api/roleplay/sessions/{s['id']}/complete")
    assert done.status_code == 200
    fb = c.get(f"/api/roleplay/sessions/{s['id']}/feedback")
    assert fb.status_code == 200
    assert c.get("/api/roleplay/sessions").json()["sessions"][0]["status"] == "completed"


def test_a_wrong_marathi_reply_gets_hints_then_the_answer_never_a_false_pass(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, "hint@example.com")
    s = _start(c, "food")
    turns = [c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": t}).json()["turn"] for t in ("Kitna hua?", "zzz", "Ek chai")]
    assert [t["verdict"] for t in turns] == ["incorrect", "incorrect", "incorrect"]
    assert turns[0]["hint"] and turns[1]["hint"] and "model_answer" not in turns[0] and turns[2]["model_answer"]
    assert turns[0]["grading"]["method"] != "exact" and turns[0]["grading"]["semantic_match"] is False
    assert "not available for this language" not in (turns[0]["grading"]["explanation"] or "")       # Marathi is graded, not skipped


def test_a_hindi_roleplay_is_unchanged(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, "delhi@example.com", target="hi")
    with db() as conn:
        sid = conn.execute(f"SELECT id FROM situations WHERE slug = 'transport' AND language_id = {HI}").fetchone()[0]
        first = conn.execute("SELECT v.pronunciation FROM situation_steps st JOIN vocabulary_items v ON v.id = st.item_id WHERE st.situation_id = ? ORDER BY st.sort_order LIMIT 1", (sid,)).fetchone()[0]
    s = c.post("/api/roleplay/sessions", json={"situation_id": sid}).json()["session"]
    assert "Raju bhaiya: Namaste!" in s["scene"]
    t = c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": first}).json()["turn"]
    assert t["verdict"] == "correct" and "Achha!" in t["character"]


# =====================================================================================================================
# listening
# =====================================================================================================================
def test_marathi_listening_plays_marathi_and_records_progress(client):
    c = learner(client, "listen@example.com", level="A2")
    acts = c.get("/api/listening").json()["activities"]
    assert len(acts) == 42 and {a["mode"] for a in acts} == {"choose_meaning", "choose_phrase"}
    a = c.get(f"/api/listening/{acts[0]['id']}").json()["activity"]
    assert a["audio"]["kind"] == "browser_tts" and a["audio"]["locale"] == "mr-IN" and DEVANAGARI.search(a["audio"]["speak_text"])
    assert len(a["options"]) == 3
    with db() as conn:
        right = conn.execute("SELECT o.id FROM listening_options o JOIN listening_activities a ON a.id = o.activity_id AND a.item_id = o.item_id WHERE a.id = ?", (a["id"],)).fetchone()[0]
    wrong = next(o["id"] for o in a["options"] if o["id"] != right)
    assert c.post(f"/api/listening/{a['id']}/attempts", json={"option_id": wrong, "plays": 1}).json()["correct"] is False
    r = c.post(f"/api/listening/{a['id']}/attempts", json={"option_id": right, "plays": 2}).json()
    assert r["correct"] is True and DEVANAGARI.search(r["heard"]["text"]) and r["heard"]["meaning"]
    assert c.get("/api/listening/progress").json()["progress"]["attempts"] == 2


def test_hindi_listening_is_unchanged(client):
    c = learner(client, "hilisten@example.com", target="hi")
    acts = c.get("/api/listening").json()["activities"]
    assert len(acts) == 15 and c.get(f"/api/listening/{acts[0]['id']}").json()["activity"]["audio"]["locale"] == "hi-IN"


# =====================================================================================================================
# speaking: prompts and what can be done with Marathi
# =====================================================================================================================
def test_marathi_speaking_prompts_cover_both_levels(client):
    c = learner(client, "speak@example.com", level="A2")
    prompts = c.get("/api/speaking/prompts").json()["prompts"]
    romans = {p["item"]["pronunciation"] for p in prompts}
    assert len(prompts) >= 90 and "Don tikita dya." in romans and "Namaskar, kase aahat?" in romans
    assert all(DEVANAGARI.search(p["item"]["text"]) for p in prompts)


def test_capabilities_say_what_is_possible_before_recording(client, monkeypatch):
    c = learner(client, "caps@example.com")
    monkeypatch.setattr(speaking_service, "STT_FACTORY", lambda: None)
    caps = c.get("/api/speaking/prompts").json()["capabilities"]
    assert caps == {"language": "mr", "language_name": "Marathi", "locale": "mr-IN", "transcription": "not_configured", "pronunciation": "not_configured",
                    "alternatives": ["typed"]}

    class HindiOnly(stt.MockSttProvider):
        capabilities = stt.SttCapabilities(mime_types=stt._ALL_AUDIO, languages=frozenset({"hi"}))
    monkeypatch.setattr(speaking_service, "STT_FACTORY", lambda: HindiOnly())
    caps = c.get("/api/speaking/prompts").json()["capabilities"]
    assert caps["transcription"] == "unsupported_language" and caps["alternatives"] == ["typed"]
    monkeypatch.setattr(speaking_service, "STT_FACTORY", lambda: stt.MockSttProvider())
    assert c.get("/api/speaking/prompts").json()["capabilities"]["transcription"] == "available"


def test_a_recording_in_a_language_the_engine_lacks_is_not_transcribed(client, monkeypatch):
    class HindiOnly(stt.MockSttProvider):
        capabilities = stt.SttCapabilities(mime_types=stt._ALL_AUDIO, languages=frozenset({"hi"}))
    monkeypatch.setattr(speaking_service, "STT_FACTORY", lambda: HindiOnly())
    from . import spk
    c = learner(client, "nostt@example.com")
    item = spk.prompt_items(c)[0]["item"]["id"]
    sid = spk.create(c, item)["id"]
    up = spk.upload(c, sid, spk.audio("नमस्कार"))
    assert up.status_code == 200, up.text
    s = spk.transcribe(c, sid).json()["session"]
    assert s["stage"] == "failed" and s["error"]["code"] == "unsupported_language" and not s.get("transcript")


def test_whisper_is_declared_to_handle_hindi_and_marathi_only_by_its_published_list():
    caps = stt.GroqWhisperProvider("k").capabilities
    assert caps.supports_language("mr-IN") and caps.supports_language("hi-IN") and not caps.supports_language("xx-IN")


# =====================================================================================================================
# the content review record
# =====================================================================================================================
def test_the_review_record_says_ai_assisted_and_pending_for_marathi(client, client2):
    c = learner(client, "review@example.com")
    body = c.get("/api/content-review").json()
    assert body == {"language": "mr", "review": {"language": "mr", "editorial_status": "ai_assisted_review", "native_review_status": "pending",
                                                  "last_editorial_reviewed_at": "2026-10-18", "known_limitations": body["review"]["known_limitations"]}}
    assert "not yet checked by a native Marathi speaker" in body["review"]["known_limitations"]
    hindi = learner(client2, "hireview@example.com", target="hi")
    assert hindi.get("/api/content-review").json() == {"language": "hi", "review": None}            # nothing recorded: nothing claimed


def test_the_review_record_needs_a_learner(client, client2):
    assert client.get("/api/content-review").status_code == 401
    register(client2, "noprofile@example.com")
    assert client2.get("/api/content-review").json() == {"language": None, "review": None}


@pytest.mark.parametrize("sql", [
    "UPDATE content_reviews SET native_review_status = 'native_reviewed'",
    "UPDATE content_reviews SET editorial_status = 'ai_validated'",
    "UPDATE content_reviews SET last_editorial_reviewed_at = 'yesterday'",
    f"INSERT INTO content_reviews(language_id, editorial_status, native_review_status) VALUES ({MR}, 'none', 'pending')",
])
def test_the_review_record_only_holds_known_values(client, sql):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        with db() as conn:
            conn.execute(sql)


# =====================================================================================================================
# the admin CMS: Marathi content through its whole lifecycle
# =====================================================================================================================
def test_an_admin_sees_marathi_situations_and_listening(admin):
    assert ok(admin.get("/api/admin/content/situations?language=mr"))["total"] == 14
    assert ok(admin.get("/api/admin/content/listening?language=mr"))["total"] == 54
    assert ok(admin.get("/api/admin/content/lessons?language=mr&cefr=A2"))["total"] == 10


def test_an_admin_can_retire_and_restore_a_marathi_lesson(admin, client2):
    learner_c = learner(client2, "retire@example.com", level="A2")
    with db() as conn:
        lid = conn.execute(f"SELECT id FROM lessons WHERE slug = 'travel' AND language_id = {MR}").fetchone()[0]
    rev = ok(admin.get(f"/api/admin/content/lessons/{lid}"))["revision"]
    rev = ok(admin.post(f"/api/admin/unpublish/lesson/{lid}", {"revision": rev}))["revision"]
    assert "travel" not in [l["slug"] for l in learner_c.get("/api/lessons").json()["lessons"]]
    rev = ok(admin.post(f"/api/admin/archive/lesson/{lid}", {"revision": rev}))["revision"]
    rev = ok(admin.post(f"/api/admin/restore/lesson/{lid}", {"revision": rev}))["revision"]
    ok(admin.post(f"/api/admin/publish/lesson/{lid}", {"revision": rev}))
    assert "travel" in [l["slug"] for l in learner_c.get("/api/lessons").json()["lessons"]]


def test_the_whole_catalogue_passes_the_content_sweep(admin):
    sweep = ok(admin.get("/api/admin/validate/all"))
    assert sweep["ok"] is True and sweep["published_errors"] == 0
    assert sweep["checked"] == {"lesson": 157, "situation": 111, "listening_activity": 315}               # with Kannada and Tamil


# =====================================================================================================================
# the rest of the journey: plan, recommendations, adaptive practice, confidence
# =====================================================================================================================
def _marathi_ids(table):
    with db() as conn:
        return {r[0] for r in conn.execute(f"SELECT id FROM {table} WHERE language_id = {MR}")}


def test_the_plan_and_recommendations_point_to_marathi_content_only(client):
    c = learner(client, "plan@example.com", level="A2")
    tasks = c.post("/api/daily-plan/generate").json()["plan"]["tasks"]
    recs = c.get("/api/recommendations").json()["recommendations"]
    tables = {"lesson": "lessons", "situation": "situations", "listening_activity": "listening_activities", "listening": "listening_activities"}
    targets = [t["target"] for t in tasks] + [r["target"] for r in recs if r.get("target")]
    assert targets
    for t in targets:
        assert t["id"] in _marathi_ids(tables[t["type"]]), t


def test_adaptive_practice_after_wrong_answers_uses_marathi_items(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, "adapt@example.com")
    with db() as conn:
        exs = [r[0] for r in conn.execute(f"SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = 'food' AND l.language_id = {MR} AND e.kind = 'translation'")]
    for _ in range(4):
        assert c.post(f"/api/exercises/{exs[0]}/attempts", json={"text": "wrong answer"}).json()["correct"] is False
    micro = c.get("/api/ai/micro-lessons").json()
    lessons = micro["micro_lessons"]
    assert lessons and "vadapav" in lessons[0]["question"].lower()                      # a drill on the Marathi phrase answered wrongly
    for m in lessons:                                                                   # a feminine form never doubles a wrong option
        texts = [normalize(o["text"].removesuffix(" (said by a woman)")) for o in m.get("options", [])]
        assert len(texts) == len(set(texts)), m["options"]
    text = json.dumps(micro, ensure_ascii=False)
    assert "Hindi" not in text and "Namaste" not in text
    with db() as conn:
        marathi_items = {r[0] for r in conn.execute(f"SELECT id FROM vocabulary_items WHERE language_id = {MR}")}
    for m in lessons:
        item = m.get("item") or {}
        if "id" in item:
            assert item["id"] in marathi_items, m
    weak = c.get("/api/weaknesses").json()["weaknesses"]
    assert weak and all(w.get("item", {}).get("id") in marathi_items or w["rule"] == "low_topic_accuracy" for w in weak)


# =====================================================================================================================
# B1 (migration 0035)
# =====================================================================================================================
B1_SLUGS = ["obligations", "if-when", "can-cant", "opinions", "complaints", "what-happened"]


def test_a_b1_learner_gets_all_three_levels_and_an_a2_learner_none_of_b1(client, client2):
    b1 = learner(client, "b1@example.com", level="B1")
    got = b1.get("/api/lessons").json()["lessons"]
    assert [l["slug"] for l in got] == A1_SLUGS + A2_SLUGS + B1_SLUGS
    assert [s["slug"] for s in b1.get("/api/situations").json()["situations"]][-2:] == ["water-complaint", "late-for-meeting"]
    assert len(b1.get("/api/listening").json()["activities"]) == 54
    a2 = learner(client2, "a2only@example.com", level="A2")
    assert not set(B1_SLUGS) & {l["slug"] for l in a2.get("/api/lessons").json()["lessons"]}
    with db() as conn:
        b1_lesson = conn.execute(f"SELECT id FROM lessons WHERE slug = 'opinions' AND language_id = {MR}").fetchone()[0]
    assert a2.get(f"/api/lessons/{b1_lesson}").status_code == 404                     # above their level: it does not exist for them


def test_b1_lessons_teach_their_grammar_and_grade_like_the_rest(client):
    c = learner(client, "b1grade@example.com", level="B1")
    lid = next(l["id"] for l in c.get("/api/lessons").json()["lessons"] if l["slug"] == "if-when")
    lesson = c.get(f"/api/lessons/{lid}").json()["lesson"]
    assert [g["title"] for g in lesson["grammar"]] == ["If … then: “jar … tar”"]
    ex = next(e for e in lesson["exercises"] if e["kind"] == "translation")
    for typed, correct in (("Vel milala tar mi phone karin.", True), ("vel milaala tar mee phone kareen", True), ("वेळ मिळाला तर मी फोन करीन", True),
                           ("Vel milala to main phone karunga", False), ("Vel milala tar", False)):
        assert c.post(f"/api/exercises/{ex['id']}/attempts", json={"text": typed}).json()["correct"] is correct, typed


def test_a_b1_roleplay_runs_in_marathi(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, "b1rp@example.com", level="B1")
    s = _start(c, "water-complaint")
    assert "Joshi kaka: Namaskar!" in s["scene"] and s["situation"]["title"] == "Complain about the water"
    for answer in _key("water-complaint"):
        assert c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": answer}).json()["turn"]["verdict"] == "correct"
    assert c.post(f"/api/roleplay/sessions/{s['id']}/complete").status_code == 200

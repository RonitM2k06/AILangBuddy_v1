"""Bengaluru's Kannada learning on the server (migrations 0037, 0038): the curriculum through B1, server roleplays and listening, typed-answer and semantic
grading in Roman letters and Kannada script, the speaking word check, speaking capabilities, and the content review record. Hindi and Marathi
are checked alongside wherever a shared path changed, so a Kannada rule can never leak into them. Everything runs on the test database with
the built-in (offline) providers: no network."""
import json
import re

import pytest

from backend import main
from backend.adaptive import lexicon, semantic
from backend.ai import registry
from backend.ai.mock import MockProvider
from backend.db import connect
from backend.speaking import content_match, service as speaking_service, stt
from backend.textnorm import answer_key, normalize

from .adm import admin, ok  # noqa: F401  (admin: fixture)
from .conftest import register

KN = "(SELECT id FROM languages WHERE code = 'kn')"
KANNADA = re.compile(r"[ಀ-೿]")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
HINDI_ROMAN = re.compile(r"\b(hai|hain|kya|kahan|kidhar|mujhe|chahiye|kitna|dijiye|bhaiya|achha|accha|shukriya|namaste)\b", re.I)
A1_SLUGS = ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk", "numbers-money", "help-health"]
A2_SLUGS = ["yesterday", "plans", "favours", "likes", "comparing", "travel", "shop-problems", "work-study", "home-problems", "long-conversation"]
B1_SLUGS = ["obligations", "if-when", "can-cant", "opinions", "complaints", "what-happened"]


def db():
    return connect(main.DB_PATH)


def learner(client, email, level="A1", dob="2000-05-20", target="kn"):
    register(client, email)
    r = client.put("/api/profile", json={"native_language": "en", "target_language": target, "cefr_level": level, "date_of_birth": dob})
    assert r.status_code == 200, r.text
    return client


# =====================================================================================================================
# the curriculum
# =====================================================================================================================
def test_kannada_is_a_target_from_a1_to_b1(client):
    with db() as conn:
        assert sorted(r[0] for r in conn.execute(f"SELECT cefr_code FROM language_levels WHERE language_id = {KN}")) == ["A1", "A2", "B1"]
    register(client, "b2kn@example.com")
    r = client.put("/api/profile", json={"native_language": "en", "target_language": "kn", "cefr_level": "B2", "date_of_birth": "2000-05-20"})
    assert r.status_code == 422                                                            # no B2 Kannada content: not offered


def test_the_curriculum_counts(client):
    with db() as conn:
        def one(sql):
            return conn.execute(sql).fetchone()[0]
        def by_level(table):
            return dict(conn.execute(f"SELECT cefr_code, COUNT(*) FROM {table} WHERE language_id = {KN} GROUP BY cefr_code").fetchall())
        assert by_level("lessons") == {"A1": 9, "A2": 10, "B1": 6} and one(f"SELECT COUNT(*) FROM lessons WHERE language_id = {KN} AND status <> 'published'") == 0
        assert dict(conn.execute(f"SELECT kind, COUNT(*) FROM exercises WHERE language_id = {KN} GROUP BY kind").fetchall()) == {
            "multiple_choice": 25, "translation": 25, "fill_blank": 25}
        assert by_level("grammar_topics") == {"A1": 3, "A2": 5, "B1": 4}
        assert by_level("situations") == {"A1": 8, "A2": 4, "B1": 2}
        assert by_level("listening_activities") == {"A1": 18, "A2": 20, "B1": 12}
        assert by_level("vocabulary_items") == {"A1": 66, "A2": 70, "B1": 42}             # A1: 48 phrases (and 1 feminine form), 18 words
        for (lid,) in conn.execute(f"SELECT id FROM lessons WHERE language_id = {KN}"):
            assert conn.execute("SELECT COUNT(*) FROM lesson_vocabulary WHERE lesson_id = ?", (lid,)).fetchone()[0] >= 7
            assert {r[0] for r in conn.execute("SELECT kind FROM exercises WHERE lesson_id = ?", (lid,))} == {"multiple_choice", "translation", "fill_blank"}


def test_a_learner_gets_the_kannada_lessons_of_their_level_in_order(client, client2):
    c = learner(client, "lessons@example.com")
    assert [l["slug"] for l in c.get("/api/lessons").json()["lessons"]] == A1_SLUGS
    b1 = learner(client2, "b1@example.com", level="B1")
    got = b1.get("/api/lessons").json()["lessons"]
    assert [l["slug"] for l in got] == A1_SLUGS + A2_SLUGS + B1_SLUGS and [l["cefr_level"] for l in got] == ["A1"] * 9 + ["A2"] * 10 + ["B1"] * 6


def test_the_kannada_content_is_kannada(client):
    """Kannada script, never Devanagari, and no Hindi in a Kannada lesson, situation or listening activity."""
    with db() as conn:
        rows = conn.execute(f"SELECT text, pronunciation FROM vocabulary_items WHERE language_id = {KN}").fetchall()
        lines = [r[0] for r in conn.execute(f"SELECT prompt FROM situation_steps WHERE language_id = {KN} AND kind IN ('choose_response', 'conversation')")]
        lines += [r[0] for r in conn.execute(f"SELECT a.answer_text FROM situation_step_answers a JOIN situation_steps s ON s.id = a.step_id WHERE s.language_id = {KN}")]
        lines += [r[0] for r in conn.execute(f"SELECT prompt FROM exercises WHERE language_id = {KN}")]
    for text, roman in rows:
        assert KANNADA.search(text) and not DEVANAGARI.search(text) and roman, text
        assert not HINDI_ROMAN.search(roman), roman
    for line in lines:
        assert not HINDI_ROMAN.search(line) and not DEVANAGARI.search(line), line
    assert any("in Kannada? (Roman letters or Kannada script.)" in l for l in lines) and not any("Devanagari" in l for l in lines)


def test_the_first_week_lessons_are_the_packs_phrases_and_the_gendered_one_has_both_forms(client):
    with db() as conn:
        romans = [r[0] for r in conn.execute(f"SELECT v.pronunciation FROM lesson_vocabulary lv JOIN vocabulary_items v ON v.id = lv.item_id "
                                              f"JOIN lessons l ON l.id = lv.lesson_id WHERE l.slug = 'greetings' AND l.language_id = {KN} ORDER BY lv.sort_order")]
    assert romans[:6] == ["Namaskara, hegiddira?", "Nanna hesaru Alex.", "Nimma hesarenu?", "Naanu illi hosaba.", "Naanu illi hosabalu.", "Tumba dhanyavaadagalu!"]


def test_the_office_lesson_and_situation_are_not_for_children(client):
    with db() as conn:
        for table, link in (("lessons", "lesson_age_groups"), ("situations", "situation_age_groups")):
            col = "lesson_id" if table == "lessons" else "situation_id"
            groups = {r[0] for r in conn.execute(f"SELECT g.code FROM {link} x JOIN age_groups g ON g.id = x.age_group_id JOIN {table} t ON t.id = x.{col} "
                                                  f"WHERE t.slug = 'college' AND t.language_id = {KN}")}
            assert groups == {"teen", "adult"}, table


def test_a_lesson_is_completed_only_when_every_exercise_is_right(client):
    c = learner(client, "done@example.com")
    lid = next(l["id"] for l in c.get("/api/lessons").json()["lessons"] if l["slug"] == "food")
    exercises = c.get(f"/api/lessons/{lid}").json()["lesson"]["exercises"]
    for n, ex in enumerate(exercises):
        with db() as conn:
            if ex["kind"] == "multiple_choice":
                body = {"answer_id": conn.execute("SELECT id FROM exercise_answers WHERE exercise_id = ? AND is_correct = 1", (ex["id"],)).fetchone()[0]}
            else:
                body = {"text": conn.execute("SELECT answer_text FROM exercise_answers WHERE exercise_id = ? AND is_correct = 1", (ex["id"],)).fetchone()[0]}
        r = c.post(f"/api/exercises/{ex['id']}/attempts", json=body)
        assert r.json()["lesson_progress"]["status"] == ("completed" if n == len(exercises) - 1 else "in_progress")


# =====================================================================================================================
# grading typed answers
# =====================================================================================================================
def _exercise(slug, kind):
    with db() as conn:
        return conn.execute(f"SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = ? AND l.language_id = {KN} AND e.kind = ?",
                            (slug, kind)).fetchone()[0]


@pytest.mark.parametrize("typed,correct", [
    ("Ille nillisi.", True), ("ille nillisi", True), ("ILLE NILLISI!", True), ("  Ille,  nillisi ", True),        # case, punctuation, spaces
    ("ಇಲ್ಲೇ ನಿಲ್ಲಿಸಿ.", True), ("ಇಲ್ಲೇ ನಿಲ್ಲಿಸಿ", True), ("ಇಲ್ಲೆ ನಿಲ್ಲಿಸಿ", True),                            # Kannada script, a short vowel sign
    ("Ile nilisi", True), ("Ille nilisi.", True),                                                              # documented romanisation variants
    ("Yahin rok do.", False), ("Ille.", False), ("Nillisi ille ille", False), ("इल्ले निल्लिसि", False),        # Hindi, incomplete, Devanagari
])
def test_a_kannada_translation_accepts_documented_variants_and_nothing_else(client, typed, correct):
    c = learner(client, "grade@example.com")
    r = c.post(f"/api/exercises/{_exercise('transport', 'translation')}/attempts", json={"text": typed})
    assert r.status_code == 200 and r.json()["correct"] is correct, typed


@pytest.mark.parametrize("typed,correct", [("neeru", True), ("Neeru.", True), ("niru", True), ("neer", False), ("paani", False)])
def test_a_kannada_fill_in_accepts_a_long_vowel_written_short(client, typed, correct):
    c = learner(client, "fill@example.com")
    assert c.post(f"/api/exercises/{_exercise('food', 'fill_blank')}/attempts", json={"text": typed}).json()["correct"] is correct


def test_the_kannada_folding_never_reaches_hindi_or_marathi():
    for text in ("Kitne paise honge?", "Thoda kam karo", "नमस्ते, आप कैसे हैं?", "thanda", "dhanyavaad"):
        assert answer_key(text, "hi") == normalize(text) == answer_key(text, None)
    assert answer_key("thumba", "kn") == answer_key("tumba", "kn") and answer_key("aithu", "kn") == answer_key("aaytu", "kn")
    assert answer_key("thoda", "mr") != answer_key("toda", "mr")                     # Marathi keeps its own rules: "th" is not folded there
    assert answer_key("ಮೆಜೆಸ್ಟಿಕ್‌ಗೆ", "kn") == answer_key("ಮೆಜೆಸ್ಟಿಕ್ಗೆ", "kn")              # the zero-width non-joiner of loanwords is ignored


@pytest.mark.parametrize("said,accepted,match", [
    ("ellide metro station", "Metro station ellide?", True),                  # word order
    ("Thumba jaasti aithu", "Tumba jaasti aaytu.", True),                     # documented spelling variants
    ("ಮೆಟ್ರೋ ಸ್ಟೇಷನ್ ಎಲ್ಲಿದೆ", "ಮೆಟ್ರೋ ಸ್ಟೇಷನ್ ಎಲ್ಲಿದೆ?", True),                # Kannada script
    ("Swalpa kadime maadi sir", "Swalpa kadime maadi.", True),                 # polite address is not a key word
    ("Station kahan hai?", "Metro station ellide?", False),                    # Hindi is not Kannada
    ("Ondu dose kodi", "Swalpa kadime maadi.", False),                         # a different idea
    ("swalpa swalpa swalpa", "Swalpa kadime maadi.", False),                   # a function word alone means nothing
])
def test_the_kannada_semantic_grader(said, accepted, match):
    g = semantic.grade("kn", said, [accepted])
    assert g.supported and g.semantic_match is match, (said, g)


def test_a_kannada_answer_is_compared_in_its_own_script():
    assert semantic.grade("kn", "ಮೆಟ್ರೋ ಸ್ಟೇಷನ್ ಎಲ್ಲಿದೆ", ["Metro station ellide?"]).supported is False   # no Kannada-script answer to compare with
    assert semantic.grade("kn", "मेट्रो स्टेशन", ["ಮೆಟ್ರೋ ಸ್ಟೇಷನ್ ಎಲ್ಲಿದೆ?"]).semantic_match is False


def test_the_lexicons_stay_separate():
    assert lexicon.SUPPORTED == {"hi", "mr", "kn", "ta", "fr", "bn", "te", "ur", "ks", "doi"} and lexicon.for_language("gu") is None
    hi, mr, kn = (lexicon.for_language(c) for c in ("hi", "mr", "kn"))
    assert hi.stop_roman == lexicon.STOP_ROMAN_CANON and hi.group_roman == lexicon.GROUP_ROMAN                 # Hindi's data is exactly what it was
    assert hi.native is lexicon.has_devanagari and mr.native is lexicon.has_devanagari and kn.native is lexicon.has_kannada
    assert not semantic.grade("hi", "Metro station ellide", ["Metro station kahan hai?"]).semantic_match
    assert not semantic.grade("mr", "Metro station ellide", ["Metro station kuthe aahe?"]).semantic_match


# =====================================================================================================================
# speaking: the word check reads Kannada script; capabilities
# =====================================================================================================================
def test_the_speaking_word_check_compares_kannada_with_kannada():
    m = content_match.compare("ಮೀಟರ್ ಹಾಕಿ.", "Meter haaki.", "ಮೀಟರ್ ಹಾಕಿ")
    assert (m.script, m.matched, m.missing) == ("kannada", 2, ())
    m = content_match.compare("ಮೀಟರ್ ಹಾಕಿ.", "Meter haaki.", "meter haaki")
    assert (m.script, m.matched) == ("latin", 2)
    m = content_match.compare("मीटर से चलोगे?", "Meter se chaloge?", "मीटर से चलोगे")                  # Hindi unchanged
    assert (m.script, m.matched) == ("devanagari", 3)


def test_kannada_speaking_prompts_and_capabilities(client, monkeypatch):
    c = learner(client, "speak@example.com")
    body = c.get("/api/speaking/prompts").json()
    assert len(body["prompts"]) >= 40 and all(KANNADA.search(p["item"]["text"]) for p in body["prompts"])
    monkeypatch.setattr(speaking_service, "STT_FACTORY", lambda: None)
    caps = c.get("/api/speaking/prompts").json()["capabilities"]
    assert caps == {"language": "kn", "language_name": "Kannada", "locale": "kn-IN", "transcription": "not_configured", "pronunciation": "not_configured",
                    "alternatives": ["typed"]}
    assert stt.GroqWhisperProvider("k").capabilities.supports_language("kn-IN")           # Whisper's published list includes Kannada


# =====================================================================================================================
# server roleplays and listening
# =====================================================================================================================
def _sid(slug):
    with db() as conn:
        return conn.execute(f"SELECT id FROM situations WHERE slug = ? AND language_id = {KN}", (slug,)).fetchone()[0]


def _key(slug):
    with db() as conn:
        out = []
        for st in conn.execute("SELECT id, kind, item_id FROM situation_steps WHERE situation_id = ? ORDER BY sort_order", (_sid(slug),)).fetchall():
            if st["kind"] == "learn_phrase":
                out.append(conn.execute("SELECT pronunciation FROM vocabulary_items WHERE id = ?", (st["item_id"],)).fetchone()[0])
            else:
                out.append(conn.execute("SELECT answer_text FROM situation_step_answers WHERE step_id = ? AND is_correct = 1 ORDER BY sort_order", (st["id"],)).fetchone()[0])
        return out


def test_a_kannada_learner_discovers_kannada_situations_only(client, client2):
    c = learner(client, "rp@example.com")
    got = c.get("/api/situations").json()["situations"]
    with db() as conn:
        ids = {r[0] for r in conn.execute(f"SELECT id FROM situations WHERE language_id = {KN}")}
        a1_ids = {r[0] for r in conn.execute(f"SELECT id FROM situations WHERE language_id = {KN} AND cefr_code = 'A1'")}
        marathi_sid = conn.execute("SELECT id FROM situations WHERE language_id = (SELECT id FROM languages WHERE code = 'mr') LIMIT 1").fetchone()[0]
    assert {s["id"] for s in got} == a1_ids and len(got) == 8                         # an A1 learner: A1 only
    assert c.post("/api/roleplay/sessions", json={"situation_id": marathi_sid}).status_code == 404
    hindi = learner(client2, "hindi@example.com", target="hi")
    assert all(s["id"] not in ids for s in hindi.get("/api/situations").json()["situations"])


def test_a_kannada_roleplay_runs_offline_in_kannada(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())                     # the built-in provider: no network
    c = learner(client, "auto@example.com")
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid("transport")}).json()["session"]
    assert "Manju: Namaskara!" in s["scene"] and "Namaste" not in s["scene"]
    assert s["current"]["objective"].startswith("Say this in Kannada: “")
    replies = []
    for n, answer in enumerate(_key("transport")):
        typed = answer.lower().replace("aa", "a") if n == 1 else answer                    # one answer in a romanisation variant
        r = c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": typed})
        assert r.status_code == 200 and r.json()["turn"]["verdict"] == "correct", (typed, r.text)
        replies.append(r.json()["turn"]["character"])
    assert any(p in " ".join(replies) for p in ("Chennaagide!", "Sakkath!", "Bhale!"))
    assert not any(h in " ".join(replies) for h in ("Achha", "Shabaash", "Chhan", "Namaste"))
    assert c.post(f"/api/roleplay/sessions/{s['id']}/complete").status_code == 200
    assert c.get(f"/api/roleplay/sessions/{s['id']}/feedback").status_code == 200


def test_a_wrong_kannada_reply_is_graded_never_a_false_pass(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, "hint@example.com")
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid("food")}).json()["session"]
    turns = [c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": t}).json()["turn"] for t in ("Kitna hua?", "zzz", "Ek chai")]
    assert [t["verdict"] for t in turns] == ["incorrect", "incorrect", "incorrect"] and turns[2]["model_answer"]
    assert "not available for this language" not in (turns[0]["grading"]["explanation"] or "")       # Kannada is graded, not skipped


def test_kannada_listening_plays_kannada_or_nothing(client):
    c = learner(client, "listen@example.com")
    acts = c.get("/api/listening").json()["activities"]
    assert len(acts) == 18 and {a["mode"] for a in acts} == {"choose_meaning", "choose_phrase"}
    a = c.get(f"/api/listening/{acts[0]['id']}").json()["activity"]
    assert a["audio"]["kind"] == "browser_tts" and a["audio"]["locale"] == "kn-IN" and KANNADA.search(a["audio"]["speak_text"])
    assert len(a["options"]) == 3
    with db() as conn:
        right = conn.execute("SELECT o.id FROM listening_options o JOIN listening_activities a ON a.id = o.activity_id AND a.item_id = o.item_id WHERE a.id = ?", (a["id"],)).fetchone()[0]
    r = c.post(f"/api/listening/{a['id']}/attempts", json={"option_id": right, "plays": 1}).json()
    assert r["correct"] is True and KANNADA.search(r["heard"]["text"]) and r["heard"]["meaning"]


# =====================================================================================================================
# review record, admin, plan
# =====================================================================================================================
def test_the_review_record_says_ai_assisted_and_pending_for_kannada(client):
    c = learner(client, "review@example.com")
    body = c.get("/api/content-review").json()
    assert body["language"] == "kn" and body["review"]["editorial_status"] == "ai_assisted_review" and body["review"]["native_review_status"] == "pending"
    assert "not yet checked by a native Kannada speaker" in body["review"]["known_limitations"]


def test_an_admin_sees_and_validates_kannada_content(admin):
    assert ok(admin.get("/api/admin/content/lessons?language=kn"))["total"] == 25 and ok(admin.get("/api/admin/content/lessons?language=kn&cefr=B1"))["total"] == 6
    assert ok(admin.get("/api/admin/content/situations?language=kn"))["total"] == 14
    assert ok(admin.get("/api/admin/content/listening?language=kn"))["total"] == 50
    sweep = ok(admin.get("/api/admin/validate/all"))
    assert sweep["ok"] is True and sweep["published_errors"] == 0


def test_the_plan_points_to_kannada_content_only(client):
    c = learner(client, "plan@example.com")
    tasks = c.post("/api/daily-plan/generate").json()["plan"]["tasks"]
    tables = {"lesson": "lessons", "situation": "situations", "listening_activity": "listening_activities", "listening": "listening_activities"}
    assert tasks
    with db() as conn:
        for t in [t["target"] for t in tasks]:
            ids = {r[0] for r in conn.execute(f"SELECT id FROM {tables[t['type']]} WHERE language_id = {KN}")}
            assert t["id"] in ids, t
    assert "Hindi" not in json.dumps(tasks)


# =====================================================================================================================
# A2 and B1 (migration 0038)
# =====================================================================================================================
def test_the_upper_levels_teach_their_grammar_and_grade_like_the_rest(client):
    with db() as conn:
        notes = {r[0]: r[1] for r in conn.execute(f"SELECT slug, cefr_code FROM grammar_topics WHERE language_id = {KN}")}
    assert {k for k, v in notes.items() if v == "B1"} == {"having-to", "if-and-when", "can-and-cant", "what-someone-said"}
    c = learner(client, "b1grade@example.com", level="B1")
    ex = _exercise("if-when", "translation")
    assert c.post(f"/api/exercises/{ex}/attempts", json={"text": "Male bandre naanu baralla."}).json()["correct"] is True
    assert c.post(f"/api/exercises/{ex}/attempts", json={"text": "ಮಳೆ ಬಂದ್ರೆ ನಾನು ಬರಲ್ಲ"}).json()["correct"] is True
    assert c.post(f"/api/exercises/{ex}/attempts", json={"text": "Baarish hui toh nahi aaunga"}).json()["correct"] is False


def test_an_a2_learner_gets_a2_situations_and_none_of_b1(client):
    c = learner(client, "a2rp@example.com", level="A2")
    slugs = {s["slug"] for s in c.get("/api/situations").json()["situations"]}
    assert {"flat-problem", "bus-to-mysuru", "exchange-shirt", "plan-a-trip"} <= slugs and not slugs & {"water-complaint", "late-for-meeting"}


def test_a_b1_roleplay_runs_in_kannada(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, "b1rp@example.com", level="B1")
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid("water-complaint")}).json()["session"]
    assert "Mr Rao: Namaskara!" in s["scene"]
    for answer in _key("water-complaint"):
        r = c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": answer})
        assert r.json()["turn"]["verdict"] == "correct", answer

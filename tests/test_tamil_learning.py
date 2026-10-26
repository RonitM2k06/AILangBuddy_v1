"""Chennai's and Puducherry's Tamil learning on the server (migrations 0040-0042, 0045): the curriculum through B1, server roleplays and listening, typed-answer and semantic
grading in Roman letters and Tamil script, the speaking word check, speaking capabilities, and the content review record. Hindi and Marathi
(and Kannada) are checked alongside wherever a shared path changed, so a Tamil rule can never leak into them. Everything runs on the test database with
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

TA = "(SELECT id FROM languages WHERE code = 'ta')"
TAMIL = re.compile(r"[\u0B80-\u0BFF]")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
HINDI_ROMAN = re.compile(r"\b(hai|hain|kya|kahan|kidhar|mujhe|chahiye|kitna|dijiye|bhaiya|achha|accha|shukriya|namaste)\b", re.I)
A1_SLUGS = ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk", "numbers-money", "help-health", "time-days", "about-me"]
A2_SLUGS = ["yesterday", "plans", "favours", "likes", "comparing", "travel", "shop-problems", "work-study", "home-problems", "long-conversation", "puducherry"]
B1_SLUGS = ["obligations", "if-when", "can-cant", "opinions", "complaints", "what-happened"]


def db():
    return connect(main.DB_PATH)


def learner(client, email, level="A1", dob="2000-05-20", target="ta"):
    register(client, email)
    r = client.put("/api/profile", json={"native_language": "en", "target_language": target, "cefr_level": level, "date_of_birth": dob})
    assert r.status_code == 200, r.text
    return client


# =====================================================================================================================
# the curriculum
# =====================================================================================================================
def test_tamil_is_a_target_from_a1_to_b1(client):
    with db() as conn:
        assert sorted(r[0] for r in conn.execute(f"SELECT cefr_code FROM language_levels WHERE language_id = {TA}")) == ["A1", "A2", "B1"]
    register(client, "b2ta@example.com")
    r = client.put("/api/profile", json={"native_language": "en", "target_language": "ta", "cefr_level": "B2", "date_of_birth": "2000-05-20"})
    assert r.status_code == 422                                                            # no B2 Tamil content: not offered


def test_the_curriculum_counts(client):
    with db() as conn:
        def one(sql):
            return conn.execute(sql).fetchone()[0]
        def by_level(table):
            return dict(conn.execute(f"SELECT cefr_code, COUNT(*) FROM {table} WHERE language_id = {TA} GROUP BY cefr_code").fetchall())
        assert by_level("lessons") == {"A1": 11, "A2": 11, "B1": 6} and one(f"SELECT COUNT(*) FROM lessons WHERE language_id = {TA} AND status <> 'published'") == 0
        assert dict(conn.execute(f"SELECT kind, COUNT(*) FROM exercises WHERE language_id = {TA} GROUP BY kind").fetchall()) == {
            "multiple_choice": 28, "translation": 28, "fill_blank": 28}
        assert by_level("grammar_topics") == {"A1": 3, "A2": 5, "B1": 4}
        assert by_level("situations") == {"A1": 11, "A2": 7, "B1": 3}
        assert by_level("listening_activities") == {"A1": 22, "A2": 22, "B1": 12}
        assert by_level("vocabulary_items") == {"A1": 79, "A2": 77, "B1": 42}             # A1: 57 phrases (none gendered), 22 words
        for (lid,) in conn.execute(f"SELECT id FROM lessons WHERE language_id = {TA}"):
            assert conn.execute("SELECT COUNT(*) FROM lesson_vocabulary WHERE lesson_id = ?", (lid,)).fetchone()[0] >= 7
            assert {r[0] for r in conn.execute("SELECT kind FROM exercises WHERE lesson_id = ?", (lid,))} == {"multiple_choice", "translation", "fill_blank"}


def test_a_learner_gets_the_tamil_lessons_of_their_level_in_order(client, client2):
    c = learner(client, "lessons@example.com")
    assert [l["slug"] for l in c.get("/api/lessons").json()["lessons"]] == A1_SLUGS
    b1 = learner(client2, "b1@example.com", level="B1")
    got = b1.get("/api/lessons").json()["lessons"]
    assert [l["slug"] for l in got] == A1_SLUGS + A2_SLUGS + B1_SLUGS and [l["cefr_level"] for l in got] == ["A1"] * 11 + ["A2"] * 11 + ["B1"] * 6


def test_the_tamil_content_is_tamil(client):
    """Tamil script, never Devanagari, and no Hindi in a Tamil lesson, situation or listening activity."""
    with db() as conn:
        rows = conn.execute(f"SELECT text, pronunciation FROM vocabulary_items WHERE language_id = {TA}").fetchall()
        lines = [r[0] for r in conn.execute(f"SELECT prompt FROM situation_steps WHERE language_id = {TA} AND kind IN ('choose_response', 'conversation')")]
        lines += [r[0] for r in conn.execute(f"SELECT a.answer_text FROM situation_step_answers a JOIN situation_steps s ON s.id = a.step_id WHERE s.language_id = {TA}")]
        lines += [r[0] for r in conn.execute(f"SELECT prompt FROM exercises WHERE language_id = {TA}")]
    for text, roman in rows:
        assert TAMIL.search(text) and not DEVANAGARI.search(text) and roman, text
        assert not HINDI_ROMAN.search(roman), roman
    for line in lines:
        assert not HINDI_ROMAN.search(line) and not DEVANAGARI.search(line), line
    assert any("in Tamil? (Roman letters or Tamil script.)" in l for l in lines) and not any("Devanagari" in l for l in lines)


def test_the_first_week_lessons_are_the_packs_phrases(client):
    with db() as conn:
        romans = [r[0] for r in conn.execute(f"SELECT v.pronunciation FROM lesson_vocabulary lv JOIN vocabulary_items v ON v.id = lv.item_id "
                                              f"JOIN lessons l ON l.id = lv.lesson_id WHERE l.slug = 'greetings' AND l.language_id = {TA} ORDER BY lv.sort_order")]
    assert romans == ["Vanakkam, eppadi irukeenga?", "En peru Alex.", "Unga peru enna?", "Naan inga pudhusaa vandhirukken.", "Romba nandri!", "Peru", "Nandri"]


def test_the_office_lesson_and_situation_are_not_for_children(client):
    with db() as conn:
        for table, link in (("lessons", "lesson_age_groups"), ("situations", "situation_age_groups")):
            col = "lesson_id" if table == "lessons" else "situation_id"
            groups = {r[0] for r in conn.execute(f"SELECT g.code FROM {link} x JOIN age_groups g ON g.id = x.age_group_id JOIN {table} t ON t.id = x.{col} "
                                                  f"WHERE t.slug = 'college' AND t.language_id = {TA}")}
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
        return conn.execute(f"SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = ? AND l.language_id = {TA} AND e.kind = ?",
                            (slug, kind)).fetchone()[0]


@pytest.mark.parametrize("typed,correct", [
    ("Inga niruthunga.", True), ("inga niruthunga", True), ("INGA NIRUTHUNGA!", True), ("  Inga,  niruthunga ", True),   # case, punctuation, spaces
    ("இங்க நிறுத்துங்க.", True), ("இங்க நிறுத்துங்க", True),                                                       # Tamil script
    ("Inga nirutunga", True), ("Ingga niruthunga.", True),                                                       # documented romanisation variants
    ("Yahin rok do.", False), ("Inga.", False), ("Niruthunga inga inga", False), ("इंगा निरुत्तुंगा", False),        # Hindi, incomplete, Devanagari
])
def test_a_tamil_translation_accepts_documented_variants_and_nothing_else(client, typed, correct):
    c = learner(client, "grade@example.com")
    r = c.post(f"/api/exercises/{_exercise('transport', 'translation')}/attempts", json={"text": typed})
    assert r.status_code == 200 and r.json()["correct"] is correct, typed


@pytest.mark.parametrize("typed,correct", [("thanni", True), ("Thanni.", True), ("tanni", True), ("thani", True), ("paani", False), ("neeru", False)])
def test_a_tamil_fill_in_accepts_documented_variants(client, typed, correct):
    c = learner(client, "fill@example.com")
    assert c.post(f"/api/exercises/{_exercise('food', 'fill_blank')}/attempts", json={"text": typed}).json()["correct"] is correct


def test_the_tamil_folding_never_reaches_hindi_and_keeps_zh():
    for text in ("Kitne paise honge?", "Thoda kam karo", "नमस्ते, आप कैसे हैं?", "thanda", "dhanyavaad"):
        assert answer_key(text, "hi") == normalize(text) == answer_key(text, None)
    assert answer_key("thanni", "ta") == answer_key("tanni", "ta") and answer_key("dhooram", "ta") == answer_key("dooram", "ta")
    assert answer_key("mazhai", "ta") != answer_key("malai", "ta")                   # rain is not a hill: "zh" is not folded
    assert answer_key("thoda", "mr") != answer_key("toda", "mr")                     # Marathi keeps its own rules


@pytest.mark.parametrize("said,accepted,match", [
    ("enga irukku metro station", "Metro station enga irukku?", True),         # word order
    ("Rombha athigam", "Romba adhigam.", True),                                # documented spelling variants
    ("மெட்ரோ ஸ்டேஷன் எங்க இருக்கு", "மெட்ரோ ஸ்டேஷன் எங்க இருக்கு?", True),     # Tamil script
    ("Konjam koraichukonga sir", "Konjam koraichukonga.", True),               # polite address is not a key word
    ("Station kahan hai?", "Metro station enga irukku?", False),               # Hindi is not Tamil
    ("Rendu idli kudunga", "Konjam koraichukonga.", False),                    # a different idea
    ("konjam konjam konjam", "Konjam koraichukonga.", False),                  # a function word alone means nothing
])
def test_the_tamil_semantic_grader(said, accepted, match):
    g = semantic.grade("ta", said, [accepted])
    assert g.supported and g.semantic_match is match, (said, g)


def test_a_tamil_answer_is_compared_in_its_own_script():
    assert semantic.grade("ta", "மெட்ரோ ஸ்டேஷன் எங்க இருக்கு", ["Metro station enga irukku?"]).supported is False   # no Tamil-script answer to compare with
    assert semantic.grade("ta", "ಮೆಟ್ರೋ ಸ್ಟೇಷನ್", ["மெட்ரோ ஸ்டேஷன் எங்க இருக்கு?"]).semantic_match is False


def test_the_lexicons_stay_separate():
    assert lexicon.SUPPORTED == {"hi", "mr", "kn", "ta", "fr", "bn", "te", "ur", "ks", "doi"} and lexicon.for_language("gu") is None
    hi, kn, ta = (lexicon.for_language(c) for c in ("hi", "kn", "ta"))
    assert hi.stop_roman == lexicon.STOP_ROMAN_CANON and hi.group_roman == lexicon.GROUP_ROMAN                 # Hindi's data is exactly what it was
    assert ta.native is lexicon.has_tamil and kn.native is lexicon.has_kannada and hi.native is lexicon.has_devanagari
    assert not semantic.grade("kn", "Metro station enga irukku", ["Metro station ellide?"]).semantic_match
    assert not semantic.grade("ta", "Metro station ellide", ["Metro station enga irukku?"]).semantic_match


# =====================================================================================================================
# speaking: the word check reads Tamil script; capabilities
# =====================================================================================================================
def test_the_speaking_word_check_compares_tamil_with_tamil():
    m = content_match.compare("மீட்டர் போடுங்க.", "Meter podunga.", "மீட்டர் போடுங்க")
    assert (m.script, m.matched, m.missing) == ("tamil", 2, ())
    m = content_match.compare("மீட்டர் போடுங்க.", "Meter podunga.", "meter podunga")
    assert (m.script, m.matched) == ("latin", 2)
    m = content_match.compare("ಮೀಟರ್ ಹಾಕಿ.", "Meter haaki.", "ಮೀಟರ್ ಹಾಕಿ")                                # Kannada unchanged
    assert (m.script, m.matched) == ("kannada", 2)


def test_tamil_speaking_prompts_and_capabilities(client, monkeypatch):
    c = learner(client, "speak@example.com")
    body = c.get("/api/speaking/prompts").json()
    assert len(body["prompts"]) >= 40 and all(TAMIL.search(p["item"]["text"]) for p in body["prompts"])
    monkeypatch.setattr(speaking_service, "STT_FACTORY", lambda: None)
    caps = c.get("/api/speaking/prompts").json()["capabilities"]
    assert caps == {"language": "ta", "language_name": "Tamil", "locale": "ta-IN", "transcription": "not_configured", "pronunciation": "not_configured",
                    "alternatives": ["typed"]}
    assert stt.GroqWhisperProvider("k").capabilities.supports_language("ta-IN")           # Whisper's published list includes Tamil


# =====================================================================================================================
# server roleplays and listening
# =====================================================================================================================
def _sid(slug):
    with db() as conn:
        return conn.execute(f"SELECT id FROM situations WHERE slug = ? AND language_id = {TA}", (slug,)).fetchone()[0]


def _key(slug):
    with db() as conn:
        out = []
        for st in conn.execute("SELECT id, kind, item_id FROM situation_steps WHERE situation_id = ? ORDER BY sort_order", (_sid(slug),)).fetchall():
            if st["kind"] == "learn_phrase":
                out.append(conn.execute("SELECT pronunciation FROM vocabulary_items WHERE id = ?", (st["item_id"],)).fetchone()[0])
            else:
                out.append(conn.execute("SELECT answer_text FROM situation_step_answers WHERE step_id = ? AND is_correct = 1 ORDER BY sort_order", (st["id"],)).fetchone()[0])
        return out


def test_a_tamil_learner_discovers_tamil_situations_only(client, client2):
    c = learner(client, "rp@example.com")
    got = c.get("/api/situations").json()["situations"]
    with db() as conn:
        ids = {r[0] for r in conn.execute(f"SELECT id FROM situations WHERE language_id = {TA}")}
        a1_ids = {r[0] for r in conn.execute(f"SELECT id FROM situations WHERE language_id = {TA} AND cefr_code = 'A1'")}
        kannada_sid = conn.execute("SELECT id FROM situations WHERE language_id = (SELECT id FROM languages WHERE code = 'kn') LIMIT 1").fetchone()[0]
    assert {s["id"] for s in got} == a1_ids and len(got) == 11                        # an A1 learner: A1 only
    assert c.post("/api/roleplay/sessions", json={"situation_id": kannada_sid}).status_code == 404
    hindi = learner(client2, "hindi@example.com", target="hi")
    assert all(s["id"] not in ids for s in hindi.get("/api/situations").json()["situations"])


def test_a_tamil_roleplay_runs_offline_in_tamil(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())                     # the built-in provider: no network
    c = learner(client, "auto@example.com")
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid("transport")}).json()["session"]
    assert "Murugan: Vanakkam!" in s["scene"] and "Namaste" not in s["scene"]
    assert s["current"]["objective"].startswith("Say this in Tamil: “")
    replies = []
    for n, answer in enumerate(_key("transport")):
        typed = answer.lower().replace("aa", "a") if n == 1 else answer                    # one answer in a romanisation variant
        r = c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": typed})
        assert r.status_code == 200 and r.json()["turn"]["verdict"] == "correct", (typed, r.text)
        replies.append(r.json()["turn"]["character"])
    assert any(p in " ".join(replies) for p in ("Semma!", "Romba nalla!", "Super!"))
    assert not any(h in " ".join(replies) for h in ("Achha", "Shabaash", "Chhan", "Sakkath", "Namaste"))
    assert c.post(f"/api/roleplay/sessions/{s['id']}/complete").status_code == 200
    assert c.get(f"/api/roleplay/sessions/{s['id']}/feedback").status_code == 200


def test_a_wrong_tamil_reply_is_graded_never_a_false_pass(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, "hint@example.com")
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid("food")}).json()["session"]
    turns = [c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": t}).json()["turn"] for t in ("Kitna hua?", "zzz", "Ek chai")]
    assert [t["verdict"] for t in turns] == ["incorrect", "incorrect", "incorrect"] and turns[2]["model_answer"]
    assert "not available for this language" not in (turns[0]["grading"]["explanation"] or "")       # Tamil is graded, not skipped


def test_tamil_listening_plays_tamil_or_nothing(client):
    c = learner(client, "listen@example.com")
    acts = c.get("/api/listening").json()["activities"]
    assert len(acts) == 22 and {a["mode"] for a in acts} == {"choose_meaning", "choose_phrase"}
    a = c.get(f"/api/listening/{acts[0]['id']}").json()["activity"]
    assert a["audio"]["kind"] == "browser_tts" and a["audio"]["locale"] == "ta-IN" and TAMIL.search(a["audio"]["speak_text"])
    assert len(a["options"]) == 3
    with db() as conn:
        right = conn.execute("SELECT o.id FROM listening_options o JOIN listening_activities a ON a.id = o.activity_id AND a.item_id = o.item_id WHERE a.id = ?", (a["id"],)).fetchone()[0]
    r = c.post(f"/api/listening/{a['id']}/attempts", json={"option_id": right, "plays": 1}).json()
    assert r["correct"] is True and TAMIL.search(r["heard"]["text"]) and r["heard"]["meaning"]


# =====================================================================================================================
# review record, admin, plan
# =====================================================================================================================
def test_the_review_record_says_ai_assisted_and_pending_for_tamil(client):
    c = learner(client, "review@example.com")
    body = c.get("/api/content-review").json()
    assert body["language"] == "ta" and body["review"]["editorial_status"] == "ai_assisted_review" and body["review"]["native_review_status"] == "pending"
    assert "not yet checked by a native Tamil speaker" in body["review"]["known_limitations"]


def test_an_admin_sees_and_validates_tamil_content(admin):
    assert ok(admin.get("/api/admin/content/lessons?language=ta"))["total"] == 28 and ok(admin.get("/api/admin/content/lessons?language=ta&cefr=B1"))["total"] == 6
    assert ok(admin.get("/api/admin/content/situations?language=ta"))["total"] == 21
    assert ok(admin.get("/api/admin/content/listening?language=ta"))["total"] == 56
    sweep = ok(admin.get("/api/admin/validate/all"))
    assert sweep["ok"] is True and sweep["published_errors"] == 0


def test_the_plan_points_to_tamil_content_only(client):
    c = learner(client, "plan@example.com")
    tasks = c.post("/api/daily-plan/generate").json()["plan"]["tasks"]
    tables = {"lesson": "lessons", "situation": "situations", "listening_activity": "listening_activities", "listening": "listening_activities"}
    assert tasks
    with db() as conn:
        for t in [t["target"] for t in tasks]:
            ids = {r[0] for r in conn.execute(f"SELECT id FROM {tables[t['type']]} WHERE language_id = {TA}")}
            assert t["id"] in ids, t
    assert "Hindi" not in json.dumps(tasks)


# =====================================================================================================================
# A2 and B1 (migration 0038)
# =====================================================================================================================
def test_the_upper_levels_teach_their_grammar_and_grade_like_the_rest(client):
    with db() as conn:
        notes = {r[0]: r[1] for r in conn.execute(f"SELECT slug, cefr_code FROM grammar_topics WHERE language_id = {TA}")}
    assert {k for k, v in notes.items() if v == "B1"} == {"having-to", "if-and-when", "can-and-cant", "what-someone-said"}
    c = learner(client, "b1grade@example.com", level="B1")
    ex = _exercise("if-when", "translation")
    assert c.post(f"/api/exercises/{ex}/attempts", json={"text": "Mazhai vandhaa naan vara maatten."}).json()["correct"] is True
    assert c.post(f"/api/exercises/{ex}/attempts", json={"text": "மழை வந்தா நான் வர மாட்டேன்"}).json()["correct"] is True
    assert c.post(f"/api/exercises/{ex}/attempts", json={"text": "Baarish hui toh nahi aaunga"}).json()["correct"] is False


def test_an_a2_learner_gets_a2_situations_and_none_of_b1(client):
    c = learner(client, "a2rp@example.com", level="A2")
    slugs = {s["slug"] for s in c.get("/api/situations").json()["situations"]}
    assert {"flat-problem", "bus-to-puducherry", "exchange-shirt", "plan-a-trip"} <= slugs and not slugs & {"water-complaint", "late-for-meeting"}


def test_a_b1_roleplay_runs_in_tamil(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, "b1rp@example.com", level="B1")
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid("water-complaint")}).json()["session"]
    assert "Mr Rajan: Vanakkam!" in s["scene"]
    for answer in _key("water-complaint"):
        r = c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": answer})
        assert r.json()["turn"]["verdict"] == "correct", answer


# =====================================================================================================================
# more practice (migration 0042)
# =====================================================================================================================
def test_chennai_has_as_much_practice_as_mumbai(client):
    """Tamil has at least as many lessons and listening activities as Mumbai's Marathi, and more server roleplays."""
    with db() as conn:
        def count(table, code):
            return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE language_id = (SELECT id FROM languages WHERE code = '{code}') AND status = 'published'").fetchone()[0]
        for table in ("lessons", "listening_activities"):
            assert count(table, "ta") >= count(table, "mr"), table
        assert count("situations", "ta") == 21 > count("situations", "mr") == 14


@pytest.mark.parametrize("slug", ["meet-the-neighbours", "provision-store"])
def test_the_new_a1_roleplays_run_in_tamil(client, monkeypatch, slug):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, f"{slug}@example.com")
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid(slug)}).json()["session"]
    assert ": Vanakkam!" in s["scene"] and "Namaste" not in s["scene"]
    for answer in _key(slug):
        assert c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": answer}).json()["turn"]["verdict"] == "correct", answer


def test_the_new_lessons_grade_and_listen_like_the_rest(client):
    c = learner(client, "more@example.com")
    assert c.post(f"/api/exercises/{_exercise('time-days', 'translation')}/attempts", json={"text": "ippo pathu mani"}).json()["correct"] is True
    assert c.post(f"/api/exercises/{_exercise('about-me', 'fill_blank')}/attempts", json={"text": "kudumbam"}).json()["correct"] is True
    titles = {a["title"] for a in c.get("/api/listening").json()["activities"]}
    assert {"Time and Days: what does it mean?", "About Me: which phrase?"} <= titles

"""Telugu and Urdu on the server (migrations 0051, 0052), for Hyderabad: the A1 curricula, server roleplays and listening, grading in Roman
letters and in each language's own script, the speaking word check, capabilities and the review records. Hindi is checked alongside wherever a
shared path changed. Offline providers only: no network."""
import json

import pytest

from backend import main
from backend.adaptive import lexicon, semantic
from backend.ai import registry
from backend.ai.mock import MockProvider
from backend.db import connect
from backend.speaking import content_match, service as speaking_service
from backend.textnorm import answer_key, normalize

from .adm import admin, ok  # noqa: F401  (admin: fixture)
from .conftest import register
from .test_city_packs import DEVANAGARI, TELUGU, URDU

A1_SLUGS = ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk", "numbers-money", "help-health"]
LANGS = {"te": ("Telugu", TELUGU, "te-IN", 64, ("Namaskaram!", "Baagundi!", "Chaala baagundi!", "Super!"), "Srinu"),
         "ur": ("Urdu", URDU, "ur-IN", 65, ("Assalaam alaikum!", "Bahut khoob!", "Shabaash!", "Kya baat hai!"), "Salim bhai")}


def lid(code):
    return f"(SELECT id FROM languages WHERE code = '{code}')"


def db():
    return connect(main.DB_PATH)


def learner(client, email, code, level="A1"):
    register(client, email)
    r = client.put("/api/profile", json={"native_language": "en", "target_language": code, "cefr_level": level, "date_of_birth": "2000-05-20"})
    assert r.status_code == 200, r.text
    return client


def _exercise(code, slug, kind):
    with db() as conn:
        return conn.execute(f"SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = ? AND l.language_id = {lid(code)} AND e.kind = ?", (slug, kind)).fetchone()[0]


def _sid(code, slug):
    with db() as conn:
        return conn.execute(f"SELECT id FROM situations WHERE slug = ? AND language_id = {lid(code)}", (slug,)).fetchone()[0]


def _key(code, slug):
    with db() as conn:
        out = []
        for st in conn.execute("SELECT id, kind, item_id FROM situation_steps WHERE situation_id = ? ORDER BY sort_order", (_sid(code, slug),)).fetchall():
            if st["kind"] == "learn_phrase":
                out.append(conn.execute("SELECT pronunciation FROM vocabulary_items WHERE id = ?", (st["item_id"],)).fetchone()[0])
            else:
                out.append(conn.execute("SELECT answer_text FROM situation_step_answers WHERE step_id = ? AND is_correct = 1 ORDER BY sort_order", (st["id"],)).fetchone()[0])
        return out


# ---------------------------------------------------------------------------------------------------------------------
# the curricula
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("code", LANGS)
def test_the_language_is_a_target_at_a1_only(client, code):
    with db() as conn:
        assert [r[0] for r in conn.execute(f"SELECT cefr_code FROM language_levels WHERE language_id = {lid(code)}")] == ["A1"]
    register(client, f"a2{code}@example.com")
    r = client.put("/api/profile", json={"native_language": "en", "target_language": code, "cefr_level": "A2", "date_of_birth": "2000-05-20"})
    assert r.status_code == 422


@pytest.mark.parametrize("code", LANGS)
def test_the_curriculum_counts(client, code):
    with db() as conn:
        def one(sql):
            return conn.execute(sql).fetchone()[0]
        L = lid(code)
        assert one(f"SELECT COUNT(*) FROM lessons WHERE language_id = {L} AND status = 'published'") == 9
        assert dict(conn.execute(f"SELECT kind, COUNT(*) FROM exercises WHERE language_id = {L} GROUP BY kind").fetchall()) == {"multiple_choice": 9, "translation": 9, "fill_blank": 9}
        assert one(f"SELECT COUNT(*) FROM grammar_topics WHERE language_id = {L}") == 3
        assert one(f"SELECT COUNT(*) FROM situations WHERE language_id = {L}") == 8
        assert one(f"SELECT COUNT(*) FROM listening_activities WHERE language_id = {L}") == 18
        assert one(f"SELECT COUNT(*) FROM vocabulary_items WHERE language_id = {L}") == LANGS[code][3]       # Telugu: 46 phrases + 18 words; Urdu: + 1 feminine form


@pytest.mark.parametrize("code", LANGS)
def test_a_learner_gets_the_lessons_in_order(client, code):
    assert [l["slug"] for l in learner(client, f"order-{code}@example.com", code).get("/api/lessons").json()["lessons"]] == A1_SLUGS


@pytest.mark.parametrize("code", LANGS)
def test_the_content_is_in_its_own_script(client, code):
    script = LANGS[code][1]
    with db() as conn:
        rows = conn.execute(f"SELECT text, pronunciation FROM vocabulary_items WHERE language_id = {lid(code)}").fetchall()
    assert all(script.search(t) and not DEVANAGARI.search(t) and p and not script.search(p) for t, p in rows)


def test_the_urdu_feminine_form_is_its_own_item(client):
    with db() as conn:
        romans = [r[0] for r in conn.execute(f"SELECT v.pronunciation FROM lesson_vocabulary lv JOIN vocabulary_items v ON v.id = lv.item_id "
                                              f"JOIN lessons l ON l.id = lv.lesson_id WHERE l.slug = 'greetings' AND l.language_id = {lid('ur')} ORDER BY lv.sort_order")]
    assert romans[2:4] == ["Main yahan naya hoon.", "Main yahan nayi hoon."]


# ---------------------------------------------------------------------------------------------------------------------
# grading
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("code,typed,correct", [
    ("te", "Oka plate biryani ivvandi.", True), ("te", "oka plate biryani ivvandi", True), ("te", "ఒక ప్లేట్ బిర్యానీ ఇవ్వండి.", True),
    ("te", "Oka plate idli ivvandi.", False), ("te", "Ek plate biryani dena.", False),
    ("ur", "Ek plate biryani dena.", True), ("ur", "ek plate biryani dena", True), ("ur", "ایک پلیٹ بریانی دینا۔", True), ("ur", "ايک پليٹ بريانی دينا", True),
    ("ur", "Ek plate haleem dena.", False), ("ur", "Oka plate biryani ivvandi.", False),
])
def test_a_translation_is_accepted_in_either_script(client, code, typed, correct):
    c = learner(client, f"grade-{code}@example.com", code)
    assert c.post(f"/api/exercises/{_exercise(code, 'food', 'translation')}/attempts", json={"text": typed}).json()["correct"] is correct, typed


def test_the_foldings_stay_in_their_language():
    assert answer_key("Enta avutundi?", "te") == answer_key("Entha avutundi?", "te")
    assert answer_key("ايک", "ur") == answer_key("ایک", "ur")                              # Arabic yeh typed for Urdu yeh
    for text in ("Kitne paise honge?", "नमस्ते", "ايک"):
        assert answer_key(text, "hi") == normalize(text)                                  # Hindi unchanged
    assert lexicon.for_language("te").native("ఎంత") and not lexicon.for_language("te").native("entha")
    assert lexicon.for_language("ur").native("کتنا") and not lexicon.for_language("ur").native("kitna")


@pytest.mark.parametrize("code,said,accepted,match", [
    ("te", "oka plate biryani ivvu", "Oka plate biryani ivvandi.", True),                  # the friendly form of "please give"
    ("te", "Oka plate idli ivvandi.", "Oka plate biryani ivvandi.", False),
    ("ur", "hau, pakka", "Hau, pakka!", True), ("ur", "haan pakka", "Hau, pakka!", True),     # Hyderabad's "hau" is "haan"
    ("ur", "مرچی کم ڈالو", "مرچی کم ڈالو۔", True), ("ur", "Mirchi zyaada daalo.", "Mirchi kam daalo.", False),
])
def test_the_semantic_graders(code, said, accepted, match):
    g = semantic.grade(code, said, [accepted])
    assert g.supported and g.semantic_match is match, (said, g)


def test_the_speaking_word_check_compares_each_script():
    m = content_match.compare("ఎంత అవుతుంది?", "Entha avutundi?", "ఎంత అవుతుంది")
    assert (m.script, m.matched, m.missing) == ("telugu", 2, ())
    m = content_match.compare("کتنے پیسے ہوئے؟", "Kitne paise hue?", "کتنے پیسے ہوئے")
    assert (m.script, m.matched, m.missing) == ("urdu", 3, ())
    m = content_match.compare("मीटर से चलोगे?", "Meter se chaloge?", "मीटर से चलोगे")                        # Hindi unchanged
    assert m.script == "devanagari" and m.matched == 3


@pytest.mark.parametrize("code", LANGS)
def test_speaking_capabilities(client, monkeypatch, code):
    c = learner(client, f"speak-{code}@example.com", code)
    monkeypatch.setattr(speaking_service, "STT_FACTORY", lambda: None)
    caps = c.get("/api/speaking/prompts").json()["capabilities"]
    assert caps["language"] == code and caps["language_name"] == LANGS[code][0] and caps["locale"] == LANGS[code][2] and caps["alternatives"] == ["typed"]


# ---------------------------------------------------------------------------------------------------------------------
# roleplays and listening
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("code", LANGS)
def test_a_roleplay_runs_offline_in_its_language(client, monkeypatch, code):
    name, _, _, _, (greeting, *praise), partner = LANGS[code]
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, f"rp-{code}@example.com", code)
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid(code, "transport")}).json()["session"]
    assert f"{partner}: {greeting}" in s["scene"] and s["current"]["objective"].startswith(f"Say this in {name}: “")
    replies = []
    for answer in _key(code, "transport"):
        r = c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": answer})
        assert r.json()["turn"]["verdict"] == "correct", (answer, r.text)
        replies.append(r.json()["turn"]["character"])
    assert any(p in " ".join(replies) for p in praise)


@pytest.mark.parametrize("code", LANGS)
def test_a_learner_sees_their_languages_situations_only(client, code):
    got = {s["id"] for s in learner(client, f"sit-{code}@example.com", code).get("/api/situations").json()["situations"]}
    with db() as conn:
        assert got == {r[0] for r in conn.execute(f"SELECT id FROM situations WHERE language_id = {lid(code)}")} and len(got) == 8


@pytest.mark.parametrize("code", LANGS)
def test_listening_uses_its_own_voice_or_nothing(client, code):
    c = learner(client, f"listen-{code}@example.com", code)
    acts = c.get("/api/listening").json()["activities"]
    assert len(acts) == 18
    a = c.get(f"/api/listening/{acts[0]['id']}").json()["activity"]
    assert a["audio"]["kind"] == "browser_tts" and a["audio"]["locale"] == LANGS[code][2] and LANGS[code][1].search(a["audio"]["speak_text"])


@pytest.mark.parametrize("code", LANGS)
def test_the_review_record_says_ai_assisted_and_pending(client, code):
    body = learner(client, f"review-{code}@example.com", code).get("/api/content-review").json()
    assert body["language"] == code and body["review"]["native_review_status"] == "pending"
    assert f"not yet checked by a native {LANGS[code][0]} speaker" in body["review"]["known_limitations"]


def test_an_admin_sees_and_validates_the_content(admin):
    for code in LANGS:
        assert ok(admin.get(f"/api/admin/content/lessons?language={code}"))["total"] == 9
        assert ok(admin.get(f"/api/admin/content/situations?language={code}"))["total"] == 8
    sweep = ok(admin.get("/api/admin/validate/all"))
    assert sweep["ok"] is True and sweep["published_errors"] == 0


@pytest.mark.parametrize("code", LANGS)
def test_the_plan_points_to_its_languages_content_only(client, code):
    tasks = learner(client, f"plan-{code}@example.com", code).post("/api/daily-plan/generate").json()["plan"]["tasks"]
    tables = {"lesson": "lessons", "situation": "situations", "listening_activity": "listening_activities", "listening": "listening_activities"}
    with db() as conn:
        for t in [t["target"] for t in tasks]:
            assert t["id"] in {r[0] for r in conn.execute(f"SELECT id FROM {tables[t['type']]} WHERE language_id = {lid(code)}")}, t
    assert tasks and "Hindi" not in json.dumps(tasks)

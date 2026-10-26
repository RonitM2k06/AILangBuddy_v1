"""Bengali on the server (migrations 0048, 0049), for Kolkata: the curriculum from A1 to B1, server roleplays and listening, grading in Roman letters and Bengali
script, the speaking word check, capabilities and the review record. Hindi is checked alongside wherever a shared path changed, so a Bengali
rule can never leak into it. Offline providers only: no network."""
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
from .test_city_packs import BENGALI, DEVANAGARI

BN = "(SELECT id FROM languages WHERE code = 'bn')"
A1_SLUGS = ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk", "numbers-money", "help-health"]
A2_SLUGS = ["yesterday", "plans", "favours", "likes", "comparing", "travel", "shop-problems", "work-study", "home-problems", "long-conversation"]
B1_SLUGS = ["obligations", "if-when", "can-cant", "opinions", "complaints", "what-happened"]


def db():
    return connect(main.DB_PATH)


def learner(client, email, level="A1"):
    register(client, email)
    r = client.put("/api/profile", json={"native_language": "en", "target_language": "bn", "cefr_level": level, "date_of_birth": "2000-05-20"})
    assert r.status_code == 200, r.text
    return client


def _exercise(slug, kind):
    with db() as conn:
        return conn.execute(f"SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = ? AND l.language_id = {BN} AND e.kind = ?", (slug, kind)).fetchone()[0]


def _sid(slug):
    with db() as conn:
        return conn.execute(f"SELECT id FROM situations WHERE slug = ? AND language_id = {BN}", (slug,)).fetchone()[0]


def _key(slug):
    with db() as conn:
        out = []
        for st in conn.execute("SELECT id, kind, item_id FROM situation_steps WHERE situation_id = ? ORDER BY sort_order", (_sid(slug),)).fetchall():
            if st["kind"] == "learn_phrase":
                out.append(conn.execute("SELECT pronunciation FROM vocabulary_items WHERE id = ?", (st["item_id"],)).fetchone()[0])
            else:
                out.append(conn.execute("SELECT answer_text FROM situation_step_answers WHERE step_id = ? AND is_correct = 1 ORDER BY sort_order", (st["id"],)).fetchone()[0])
        return out


# ---------------------------------------------------------------------------------------------------------------------
# the curriculum
# ---------------------------------------------------------------------------------------------------------------------
def test_bengali_is_a_target_from_a1_to_b1(client):
    with db() as conn:
        assert sorted(r[0] for r in conn.execute(f"SELECT cefr_code FROM language_levels WHERE language_id = {BN}")) == ["A1", "A2", "B1"]
    register(client, "b2bn@example.com")
    r = client.put("/api/profile", json={"native_language": "en", "target_language": "bn", "cefr_level": "B2", "date_of_birth": "2000-05-20"})
    assert r.status_code == 422                                                            # no B2 Bengali content: not offered


def test_the_curriculum_counts(client):
    with db() as conn:
        def one(sql):
            return conn.execute(sql).fetchone()[0]
        def by_level(table):
            return dict(conn.execute(f"SELECT cefr_code, COUNT(*) FROM {table} WHERE language_id = {BN} GROUP BY cefr_code").fetchall())
        assert by_level("lessons") == {"A1": 9, "A2": 10, "B1": 6} and one(f"SELECT COUNT(*) FROM lessons WHERE language_id = {BN} AND status <> 'published'") == 0
        assert dict(conn.execute(f"SELECT kind, COUNT(*) FROM exercises WHERE language_id = {BN} GROUP BY kind").fetchall()) == {"multiple_choice": 25, "translation": 25, "fill_blank": 25}
        assert by_level("grammar_topics") == {"A1": 3, "A2": 5, "B1": 4}
        assert by_level("situations") == {"A1": 8, "A2": 4, "B1": 2}
        assert by_level("listening_activities") == {"A1": 18, "A2": 20, "B1": 12}
        assert by_level("vocabulary_items") == {"A1": 64, "A2": 70, "B1": 42}             # A1: 46 phrases (none gendered) + 18 words
        for (lid,) in conn.execute(f"SELECT id FROM lessons WHERE language_id = {BN}"):
            assert {r[0] for r in conn.execute("SELECT kind FROM exercises WHERE lesson_id = ?", (lid,))} == {"multiple_choice", "translation", "fill_blank"}


def test_a_learner_gets_the_bengali_lessons_of_their_level_in_order(client, client2):
    assert [l["slug"] for l in learner(client, "order@example.com").get("/api/lessons").json()["lessons"]] == A1_SLUGS
    got = learner(client2, "b1@example.com", level="B1").get("/api/lessons").json()["lessons"]
    assert [l["slug"] for l in got] == A1_SLUGS + A2_SLUGS + B1_SLUGS and [l["cefr_level"] for l in got] == ["A1"] * 9 + ["A2"] * 10 + ["B1"] * 6


def test_the_bengali_content_is_in_bengali_script(client):
    with db() as conn:
        rows = conn.execute(f"SELECT text, pronunciation FROM vocabulary_items WHERE language_id = {BN}").fetchall()
    assert all(BENGALI.search(t) and not DEVANAGARI.search(t.replace("।", "")) and p and not BENGALI.search(p) for t, p in rows)


# ---------------------------------------------------------------------------------------------------------------------
# grading
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("typed,correct", [
    ("Ekta egg roll din.", True), ("ekta egg roll din", True), ("একটা এগ রোল দিন।", True), ("একটা এগ রোল দিন", True),
    ("Ek plate momo din.", False), ("Ek egg roll dena.", False),
])
def test_a_bengali_translation_is_accepted_in_either_script(client, typed, correct):
    c = learner(client, "grade@example.com")
    assert c.post(f"/api/exercises/{_exercise('food', 'translation')}/attempts", json={"text": typed}).json()["correct"] is correct, typed


def test_romanisation_variants_fold_together():
    assert answer_key("Kemon achen?", "bn") == answer_key("Kemon achhen?", "bn")
    assert answer_key("Soja jan", "bn") == answer_key("Shoja jan", "bn")
    assert answer_key("কেমন আছেন?", "bn") == normalize("কেমন আছেন?")
    for text in ("Kitne paise honge?", "नमस्ते", "achhe"):
        assert answer_key(text, "hi") == normalize(text)                                  # Hindi unchanged
    assert lexicon.for_language("bn").native("একটা") and not lexicon.for_language("bn").native("ekta")


@pytest.mark.parametrize("said,accepted,match", [
    ("ekta egg roll dao", "Ekta egg roll din.", True),                                  # the friendly form of "please give"
    ("ekta egg roll din dada", "Ekta egg roll din.", True),                             # polite address carries no meaning
    ("একটা এগ রোল দাও", "একটা এগ রোল দিন।", True),
    ("meter-er beshi debo", "Na, meter-er beshi debo na.", False),                       # "na" (not) matters: will give is not won't give
    ("Ek plate momo din.", "Ekta egg roll din.", False),
    ("Egg roll dijiye", "Ekta egg roll din.", False),                                    # Hindi is not Bengali
])
def test_the_bengali_semantic_grader(said, accepted, match):
    g = semantic.grade("bn", said, [accepted])
    assert g.supported and g.semantic_match is match, (said, g)


def test_the_speaking_word_check_compares_bengali_script():
    m = content_match.compare("কত লাগবে?", "Koto lagbe?", "কত লাগবে")
    assert (m.script, m.matched, m.missing) == ("bengali", 2, ())
    m = content_match.compare("কত লাগবে?", "Koto lagbe?", "koto lagbe")
    assert (m.script, m.matched) == ("latin", 2)
    m = content_match.compare("मीटर से चलोगे?", "Meter se chaloge?", "मीटर से चलोगे")                        # Hindi unchanged
    assert m.script == "devanagari" and m.matched == 3


def test_bengali_speaking_capabilities(client, monkeypatch):
    c = learner(client, "speak@example.com")
    monkeypatch.setattr(speaking_service, "STT_FACTORY", lambda: None)
    caps = c.get("/api/speaking/prompts").json()["capabilities"]
    assert caps["language"] == "bn" and caps["language_name"] == "Bengali" and caps["locale"] == "bn-IN" and caps["alternatives"] == ["typed"]


# ---------------------------------------------------------------------------------------------------------------------
# roleplays and listening
# ---------------------------------------------------------------------------------------------------------------------
def test_a_bengali_roleplay_runs_offline_in_bengali(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, "rp@example.com")
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid("transport")}).json()["session"]
    assert "Bapi da: Nomoshkar!" in s["scene"] and s["current"]["objective"].startswith("Say this in Bengali: “")
    replies = []
    for answer in _key("transport"):
        r = c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": answer})
        assert r.json()["turn"]["verdict"] == "correct", (answer, r.text)
        replies.append(r.json()["turn"]["character"])
    assert any(p in " ".join(replies) for p in ("Darun!", "Khub bhalo!", "Besh!")) and "Achha" not in " ".join(replies)


def test_a_bengali_learner_sees_bengali_situations_of_their_level(client, client2):
    a1 = {s["id"] for s in learner(client, "sit@example.com").get("/api/situations").json()["situations"]}
    b1 = {s["id"] for s in learner(client2, "sitb1@example.com", level="B1").get("/api/situations").json()["situations"]}
    with db() as conn:
        assert a1 == {r[0] for r in conn.execute(f"SELECT id FROM situations WHERE language_id = {BN} AND cefr_code = 'A1'")} and len(a1) == 8
        assert b1 == {r[0] for r in conn.execute(f"SELECT id FROM situations WHERE language_id = {BN}")} and len(b1) == 14


@pytest.mark.parametrize("slug", ["flat-problem", "train-to-bolpur", "exchange-shirt", "plan-a-trip", "water-complaint", "late-for-meeting"])
def test_every_a2_and_b1_roleplay_runs_offline(client, monkeypatch, slug):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, f"{slug}@example.com", level="B1")
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid(slug)}).json()["session"]
    for answer in _key(slug):
        r = c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": answer})
        assert r.json()["turn"]["verdict"] == "correct", (slug, answer, r.text)


def test_bengali_listening_uses_a_bengali_voice_or_nothing(client):
    c = learner(client, "listen@example.com")
    acts = c.get("/api/listening").json()["activities"]
    assert len(acts) == 18                                                                # A1 only, for an A1 learner
    a = c.get(f"/api/listening/{acts[0]['id']}").json()["activity"]
    assert a["audio"]["kind"] == "browser_tts" and a["audio"]["locale"] == "bn-IN" and BENGALI.search(a["audio"]["speak_text"])


def test_the_review_record_says_ai_assisted_and_pending_for_bengali(client):
    body = learner(client, "review@example.com").get("/api/content-review").json()
    assert body["language"] == "bn" and body["review"]["native_review_status"] == "pending" and "not yet checked by a native Bengali speaker" in body["review"]["known_limitations"]


def test_an_admin_sees_and_validates_bengali_content(admin):
    assert ok(admin.get("/api/admin/content/lessons?language=bn"))["total"] == 25
    assert ok(admin.get("/api/admin/content/situations?language=bn"))["total"] == 14
    sweep = ok(admin.get("/api/admin/validate/all"))
    assert sweep["ok"] is True and sweep["published_errors"] == 0


def test_the_plan_points_to_bengali_content_only(client):
    c = learner(client, "plan@example.com")
    tasks = c.post("/api/daily-plan/generate").json()["plan"]["tasks"]
    tables = {"lesson": "lessons", "situation": "situations", "listening_activity": "listening_activities", "listening": "listening_activities"}
    with db() as conn:
        for t in [t["target"] for t in tasks]:
            assert t["id"] in {r[0] for r in conn.execute(f"SELECT id FROM {tables[t['type']]} WHERE language_id = {BN}")}, t
    assert tasks and "Hindi" not in json.dumps(tasks)

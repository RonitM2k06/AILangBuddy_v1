"""French on the server (migration 0044), for Puducherry: the A1 curriculum, server roleplays and listening, grading with or without accents,
the speaking word check, capabilities and the review record. Hindi is checked alongside wherever a shared path changed. Offline providers
only: no network."""
import json

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
from .test_city_packs import FRENCH

FR = "(SELECT id FROM languages WHERE code = 'fr')"
A1_SLUGS = ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk", "numbers-money", "help-health"]


def db():
    return connect(main.DB_PATH)


def learner(client, email, level="A1"):
    register(client, email)
    r = client.put("/api/profile", json={"native_language": "en", "target_language": "fr", "cefr_level": level, "date_of_birth": "2000-05-20"})
    assert r.status_code == 200, r.text
    return client


def _exercise(slug, kind):
    with db() as conn:
        return conn.execute(f"SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = ? AND l.language_id = {FR} AND e.kind = ?", (slug, kind)).fetchone()[0]


def _sid(slug):
    with db() as conn:
        return conn.execute(f"SELECT id FROM situations WHERE slug = ? AND language_id = {FR}", (slug,)).fetchone()[0]


def _key(slug):
    with db() as conn:
        out = []
        for st in conn.execute("SELECT id, kind, item_id FROM situation_steps WHERE situation_id = ? ORDER BY sort_order", (_sid(slug),)).fetchall():
            if st["kind"] == "learn_phrase":
                out.append(conn.execute("SELECT text FROM vocabulary_items WHERE id = ?", (st["item_id"],)).fetchone()[0])
            else:
                out.append(conn.execute("SELECT answer_text FROM situation_step_answers WHERE step_id = ? AND is_correct = 1 ORDER BY sort_order", (st["id"],)).fetchone()[0])
        return out


# ---------------------------------------------------------------------------------------------------------------------
# the curriculum
# ---------------------------------------------------------------------------------------------------------------------
def test_french_is_a_target_at_a1_only(client):
    with db() as conn:
        assert [r[0] for r in conn.execute(f"SELECT cefr_code FROM language_levels WHERE language_id = {FR}")] == ["A1"]
    register(client, "a2fr@example.com")
    r = client.put("/api/profile", json={"native_language": "en", "target_language": "fr", "cefr_level": "A2", "date_of_birth": "2000-05-20"})
    assert r.status_code == 422


def test_the_curriculum_counts(client):
    with db() as conn:
        def one(sql):
            return conn.execute(sql).fetchone()[0]
        assert one(f"SELECT COUNT(*) FROM lessons WHERE language_id = {FR} AND status = 'published'") == 9
        assert dict(conn.execute(f"SELECT kind, COUNT(*) FROM exercises WHERE language_id = {FR} GROUP BY kind").fetchall()) == {"multiple_choice": 9, "translation": 9, "fill_blank": 9}
        assert one(f"SELECT COUNT(*) FROM grammar_topics WHERE language_id = {FR}") == 3
        assert one(f"SELECT COUNT(*) FROM situations WHERE language_id = {FR}") == 8
        assert one(f"SELECT COUNT(*) FROM listening_activities WHERE language_id = {FR}") == 18
        assert one(f"SELECT COUNT(*) FROM vocabulary_items WHERE language_id = {FR}") == 66                 # 46 phrases + 2 feminine forms + 18 words


def test_a_learner_gets_the_french_lessons_in_order(client):
    assert [l["slug"] for l in learner(client, "order@example.com").get("/api/lessons").json()["lessons"]] == A1_SLUGS


def test_items_keep_their_accents_and_their_typed_form(client):
    with db() as conn:
        rows = conn.execute(f"SELECT text, pronunciation FROM vocabulary_items WHERE language_id = {FR}").fetchall()
    assert all(FRENCH.search(t) for t, _ in rows)
    accented = {t: p for t, p in rows if t != p}
    assert accented["Le petit-déjeuner est à quelle heure ?"] == "Le petit-dejeuner est a quelle heure ?" and len(accented) >= 15


def test_a_gendered_phrase_has_its_feminine_form(client):
    with db() as conn:
        romans = [r[0] for r in conn.execute(f"SELECT v.pronunciation FROM lesson_vocabulary lv JOIN vocabulary_items v ON v.id = lv.item_id "
                                              f"JOIN lessons l ON l.id = lv.lesson_id WHERE l.slug = 'greetings' AND l.language_id = {FR} ORDER BY lv.sort_order")]
    assert romans[2:4] == ["Je suis nouveau ici.", "Je suis nouvelle ici."]


# ---------------------------------------------------------------------------------------------------------------------
# grading
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("typed,correct", [
    ("L'addition, s'il vous plaît.", True), ("L'addition, s'il vous plait.", True), ("l addition s il vous plait", True), ("L'ADDITION, S'IL VOUS PLAÎT !", True),
    ("L'adition, s'il vous plait.", False), ("L'addition.", False), ("Bill de dijiye.", False),
])
def test_a_french_translation_is_accepted_with_or_without_accents_and_nothing_else(client, typed, correct):
    c = learner(client, "grade@example.com")
    assert c.post(f"/api/exercises/{_exercise('food', 'translation')}/attempts", json={"text": typed}).json()["correct"] is correct, typed


def test_the_translation_prompt_says_accents_are_optional(client):
    with db() as conn:
        prompts = [r[0] for r in conn.execute(f"SELECT prompt FROM exercises WHERE language_id = {FR} AND kind = 'translation'")]
    assert prompts and all(p.endswith("in French? (Accents are optional.)") for p in prompts)


@pytest.mark.parametrize("typed,correct", [("dimanche", True), ("Dimanche !", True), ("lundi", False)])
def test_a_french_fill_in(client, typed, correct):
    c = learner(client, "fill@example.com")
    assert c.post(f"/api/exercises/{_exercise('smalltalk', 'fill_blank')}/attempts", json={"text": typed}).json()["correct"] is correct


@pytest.mark.parametrize("said,accepted,match", [
    ("ou est la promenade", "Excusez-moi, où est la promenade ?", True),            # no accents, no politeness
    ("la promenade, où est ?", "Excusez-moi, où est la promenade ?", True),          # word order
    ("Un cafe et un croissant", "Un café et un croissant, s'il vous plaît.", True),
    ("Ou est la gare ?", "Excusez-moi, où est la promenade ?", False),                # a different place
    ("Promenade kahan hai?", "Excusez-moi, où est la promenade ?", False),          # Hindi is not French
])
def test_the_french_semantic_grader(said, accepted, match):
    g = semantic.grade("fr", said, [accepted])
    assert g.supported and g.semantic_match is match, (said, g)


def test_the_french_folding_stays_french():
    assert answer_key("Où est la bibliothèque ?", "fr") == answer_key("ou est la bibliotheque", "fr")
    for text in ("Kitne paise honge?", "नमस्ते", "café"):
        assert answer_key(text, "hi") == normalize(text)                                  # Hindi unchanged
    assert lexicon.for_language("fr").native("café") is False


def test_the_speaking_word_check_ignores_accents():
    m = content_match.compare("Où est la bibliothèque ?", "Ou est la bibliotheque ?", "ou est la bibliotheque")
    assert (m.script, m.matched, m.missing) == ("latin", 4, ())
    m = content_match.compare("मीटर से चलोगे?", "Meter se chaloge?", "meter se chaloge")                     # Hindi in Roman letters unchanged
    assert (m.script, m.matched) == ("latin", 3)


def test_french_speaking_capabilities(client, monkeypatch):
    c = learner(client, "speak@example.com")
    monkeypatch.setattr(speaking_service, "STT_FACTORY", lambda: None)
    caps = c.get("/api/speaking/prompts").json()["capabilities"]
    assert caps["language"] == "fr" and caps["language_name"] == "French" and caps["locale"] == "fr-FR" and caps["alternatives"] == ["typed"]
    assert stt.GroqWhisperProvider("k").capabilities.supports_language("fr-FR")


# ---------------------------------------------------------------------------------------------------------------------
# roleplays and listening
# ---------------------------------------------------------------------------------------------------------------------
def test_a_french_roleplay_runs_offline_in_french(client, monkeypatch):
    monkeypatch.setattr(registry, "FACTORY", lambda: MockProvider())
    c = learner(client, "rp@example.com")
    s = c.post("/api/roleplay/sessions", json={"situation_id": _sid("transport")}).json()["session"]
    assert "Monsieur Pierre: Bonjour!" in s["scene"] and s["current"]["objective"].startswith("Say this in French: “")
    replies = []
    for n, answer in enumerate(_key("transport")):
        typed = answer.lower() if n == 0 else answer                                      # one answer in lower case, accents kept or not
        r = c.post(f"/api/roleplay/sessions/{s['id']}/turns", json={"text": typed})
        assert r.json()["turn"]["verdict"] == "correct", (typed, r.text)
        replies.append(r.json()["turn"]["character"])
    assert any(p in " ".join(replies) for p in ("Très bien !", "Parfait !", "Bravo !")) and "Achha" not in " ".join(replies)


def test_a_french_learner_sees_french_situations_only(client):
    c = learner(client, "sit@example.com")
    got = {s["id"] for s in c.get("/api/situations").json()["situations"]}
    with db() as conn:
        assert got == {r[0] for r in conn.execute(f"SELECT id FROM situations WHERE language_id = {FR}")} and len(got) == 8


def test_french_listening_uses_a_french_voice_or_nothing(client):
    c = learner(client, "listen@example.com")
    acts = c.get("/api/listening").json()["activities"]
    assert len(acts) == 18
    a = c.get(f"/api/listening/{acts[0]['id']}").json()["activity"]
    assert a["audio"]["kind"] == "browser_tts" and a["audio"]["locale"] == "fr-FR" and FRENCH.search(a["audio"]["speak_text"])


def test_the_review_record_says_ai_assisted_and_pending_for_french(client):
    body = learner(client, "review@example.com").get("/api/content-review").json()
    assert body["language"] == "fr" and body["review"]["native_review_status"] == "pending" and "not yet checked by a native French speaker" in body["review"]["known_limitations"]


def test_an_admin_sees_and_validates_french_content(admin):
    assert ok(admin.get("/api/admin/content/lessons?language=fr"))["total"] == 9
    assert ok(admin.get("/api/admin/content/situations?language=fr"))["total"] == 8
    sweep = ok(admin.get("/api/admin/validate/all"))
    assert sweep["ok"] is True and sweep["published_errors"] == 0


def test_the_plan_points_to_french_content_only(client):
    c = learner(client, "plan@example.com")
    tasks = c.post("/api/daily-plan/generate").json()["plan"]["tasks"]
    tables = {"lesson": "lessons", "situation": "situations", "listening_activity": "listening_activities", "listening": "listening_activities"}
    with db() as conn:
        for t in [t["target"] for t in tasks]:
            assert t["id"] in {r[0] for r in conn.execute(f"SELECT id FROM {tables[t['type']]} WHERE language_id = {FR}")}, t
    assert tasks and "Hindi" not in json.dumps(tasks)

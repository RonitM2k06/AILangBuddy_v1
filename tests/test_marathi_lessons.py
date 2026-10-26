"""Marathi in the server curriculum (migration 0031): Marathi is a target language at A1 and A2, with 7 published A1 lessons generated from the
Mumbai Marathi First Week pack. A Marathi learner gets exactly those lessons, answers are graded in Roman letters or Devanagari, progress is
recorded, the content passes every content check, and admins manage it like any other language. Hindi learners are unaffected. Marathi
situations and listening activities do not exist yet, and the API says so with empty lists (docs/ARCHITECTURE.md section 33)."""
import re

import pytest

from backend import main
from backend.admin import validation
from backend.db import connect

from .adm import admin, ok  # noqa: F401  (admin: fixture)
from .conftest import register
from .test_city_packs import PACKS as FIRST_WEEK

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
PROFILE = {"native_language": "en", "target_language": "mr", "cefr_level": "A1", "date_of_birth": "2000-05-20"}
SLUGS = ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk"]
MR = "(SELECT id FROM languages WHERE code = 'mr')"
L = "/api/admin/content/lessons"


def db():
    return connect(main.DB_PATH)


def as_learner(client, email, **profile):
    register(client, email)
    r = client.put("/api/profile", json={**PROFILE, **profile})
    assert r.status_code == 200, r.text
    return client


@pytest.fixture
def marathi(client):
    return as_learner(client, "mr@example.com")


def lessons(c):
    return c.get("/api/lessons").json()["lessons"]


def detail(c, slug):
    lid = next(l["id"] for l in lessons(c) if l["slug"] == slug)
    return c.get(f"/api/lessons/{lid}").json()["lesson"]


def answer_key(exercise_id):
    with db() as conn:
        return [r[0] for r in conn.execute("SELECT answer_text FROM exercise_answers WHERE exercise_id = ? AND is_correct = 1", (exercise_id,))]


# =====================================================================================================================
# the catalogue
# =====================================================================================================================
def test_marathi_is_a_target_language_at_a1_and_a2(client):
    combos = {c["language"]: c["levels"] for c in client.get("/api/language-levels").json()["language_levels"]}
    assert combos["mr"] == ["A1", "A2", "B1"]
    as_learner(client, "a2@example.com", cefr_level="A2")
    assert client.get("/api/profile").json()["profile"]["target_language"] == "mr"
    assert client.put("/api/profile", json={**PROFILE, "cefr_level": "B1"}).status_code == 200    # B1: migration 0035
    assert client.put("/api/profile", json={**PROFILE, "cefr_level": "B2"}).status_code == 422    # only the levels the catalogue offers


# =====================================================================================================================
# a Marathi learner's lessons
# =====================================================================================================================
def test_a_marathi_learner_gets_the_seven_marathi_lessons_in_order(marathi):
    got = lessons(marathi)
    assert [l["slug"] for l in got][:7] == SLUGS and len(got) == 11          # the First Week lessons first, then the A1 additions (0032)
    with db() as conn:
        ids = {r[0] for r in conn.execute(f"SELECT id FROM lessons WHERE language_id = {MR} AND cefr_code = 'A1'")}
    assert {l["id"] for l in got} == ids and all(l["cefr_level"] == "A1" for l in got)


def test_the_lessons_are_the_first_week_pack(marathi):
    for day, slug in zip(FIRST_WEEK["mumbai:mr"], SLUGS):
        lesson = detail(marathi, slug)
        assert (lesson["description"], lesson["situation"], lesson["tip"]) == (day["desc"], day["situation"], day["tip"])
        expected = []
        for p in day["phrases"]:
            expected.append((p["hi"], p["roman"], p["en"], p["natural"]))
            if p.get("fem"):
                expected.append((p["fem"]["hi"], p["fem"]["roman"], p["en"] + " (said by a woman)", p["natural"]))
        phrases = [(v["text"], v["pronunciation"], v["meaning"], v["natural"]) for v in lesson["vocabulary"] if v["kind"] == "phrase"]
        assert phrases == expected
        words = [v for v in lesson["vocabulary"] if v["kind"] == "word"]
        assert len(words) == {1: 3, 2: 1}.get(day["day"], 2) and all(DEVANAGARI.search(w["text"]) and w["meaning"] and w["examples"] for w in words)
        assert [e["kind"] for e in lesson["exercises"]] == ["multiple_choice", "translation", "fill_blank"]
        assert all("।" not in v["text"] for v in lesson["vocabulary"])                 # Marathi, not Hindi punctuation
    assert [g["title"] for g in detail(marathi, "transport")["grammar"]] == ["Polite requests: verbs ending in -a", "Yes/no questions with “ka?”"]


def test_a_hindi_learner_still_gets_only_the_hindi_lessons(client):
    hindi = as_learner(client, "hi@example.com", target_language="hi")
    got = lessons(hindi)
    with db() as conn:
        hindi_ids = [r[0] for r in conn.execute("SELECT id FROM lessons WHERE language_id = (SELECT id FROM languages WHERE code = 'hi') ORDER BY sort_order")]
    assert [l["id"] for l in got] == hindi_ids and len(got) == 7
    with db() as conn:
        marathi_id = conn.execute(f"SELECT id FROM lessons WHERE language_id = {MR} LIMIT 1").fetchone()[0]
    assert hindi.get(f"/api/lessons/{marathi_id}").status_code == 404                # another language's lesson does not exist for them


def test_the_office_lesson_is_not_for_children(client):
    child = as_learner(client, "child@example.com", date_of_birth="2019-01-01")
    assert [l["slug"] for l in lessons(child)][:6] == [s for s in SLUGS if s != "college"] and "college" not in [l["slug"] for l in lessons(child)]


# =====================================================================================================================
# answering and progress
# =====================================================================================================================
@pytest.mark.parametrize("typed,correct", [("Kasa kay?", True), ("कसं काय?", True), ("kasa kay", True), ("KASA KAY!", True),
                                           ("Kaise ho?", False), ("Namaste", False)])
def test_a_translation_is_accepted_in_roman_letters_or_devanagari(marathi, typed, correct):
    ex = next(e for e in detail(marathi, "greetings")["exercises"] if e["kind"] == "translation")
    r = marathi.post(f"/api/exercises/{ex['id']}/attempts", json={"text": typed})
    assert r.status_code == 200 and r.json()["correct"] is correct
    assert r.json()["correct_answers"] == ["Kasa kay?", "कसं काय?"]


def test_completing_a_marathi_lesson_is_recorded(marathi):
    lesson = detail(marathi, "food")
    for ex in lesson["exercises"]:
        if ex["kind"] == "multiple_choice":
            with db() as conn:
                aid = conn.execute("SELECT id FROM exercise_answers WHERE exercise_id = ? AND is_correct = 1", (ex["id"],)).fetchone()[0]
            r = marathi.post(f"/api/exercises/{ex['id']}/attempts", json={"answer_id": aid})
        else:
            r = marathi.post(f"/api/exercises/{ex['id']}/attempts", json={"text": answer_key(ex["id"])[0]})
        assert r.status_code == 200 and r.json()["correct"] is True
    assert r.json()["lesson_progress"]["status"] == "completed"
    progress = marathi.get("/api/progress/lessons").json()["progress"]
    assert [p["lesson_id"] for p in progress] == [lesson["id"]] and progress[0]["status"] == "completed" and progress[0]["title"] == "Food"
    assert detail(marathi, "food")["progress"]["status"] == "completed"


def test_a_fill_in_answer_completes_the_real_phrase(marathi):
    with db() as conn:
        rows = conn.execute(f"""SELECT e.prompt, a.answer_text, v.pronunciation FROM exercises e JOIN exercise_answers a ON a.exercise_id = e.id
                                JOIN vocabulary_items v ON v.id = e.item_id WHERE e.kind = 'fill_blank' AND e.language_id = {MR}""").fetchall()
    assert len(rows) == 27                                                             # A1 11, A2 10, B1 6
    for prompt, answer, roman in rows:
        assert re.search(r"“([^”]*____[^”]*)”", prompt).group(1).replace("____", answer) == roman


# =====================================================================================================================
# content checks and the CMS
# =====================================================================================================================
def test_the_marathi_content_passes_every_content_check(client):
    report = validation.sweep(main.DB_PATH)
    assert report["ok"] is True and report["published_errors"] == 0
    with db() as conn:
        marathi_lessons = {f"lesson:{r[0]}" for r in conn.execute(f"SELECT id FROM lessons WHERE language_id = {MR}")}
        marathi_items = {f"vocabulary:{r[0]}" for r in conn.execute(f"SELECT id FROM vocabulary_items WHERE language_id = {MR}")}
    assert not [f for f in report["findings"] if f["entity"] in marathi_lessons | marathi_items]
    with db() as conn:
        assert conn.execute(f"""SELECT COUNT(*) FROM vocabulary_items v WHERE v.language_id = {MR} AND NOT EXISTS
                                (SELECT 1 FROM vocabulary_translations t WHERE t.item_id = v.id AND t.language_id = (SELECT id FROM languages WHERE code = 'en'))""").fetchone()[0] == 0


def test_an_admin_sees_the_marathi_content(admin):
    assert ok(admin.get(L + "?language=mr"))["total"] == 27 and ok(admin.get(L + "?language=mr&status=published"))["total"] == 27
    assert ok(admin.get("/api/admin/content/vocabulary?language=mr"))["total"] == 199                 # 0031's 50, 0032's 105 and 0035's 44
    first = ok(admin.get(L + "?language=mr&limit=1"))["items"][0]
    lesson = ok(admin.get(f"{L}/{first['id']}"))
    assert lesson["language"]["code"] == "mr" and len(lesson["exercises"]) == 3 and lesson["vocabulary"]


def test_an_admin_can_write_and_publish_a_marathi_lesson_that_learners_then_get(admin, client2):
    with db() as conn:
        item = conn.execute(f"SELECT id FROM vocabulary_items WHERE language_id = {MR} AND pronunciation = 'Kiti zhale?'").fetchone()[0]
    lesson = ok(admin.post(L, {"slug": "market-extra", "language": "mr", "cefr": "A1", "title": "At the market", "description": "More market phrases.",
                               "topics": ["shopping"]}), 201)
    lesson = ok(admin.put(f"{L}/{lesson['id']}/vocabulary", {"revision": lesson["revision"], "item_ids": [item]}))
    ex = {"kind": "translation", "prompt": "How would you ask “How much is it?” in Marathi?", "item_id": item, "difficulty": 2,
          "answers": [{"text": "Kiti zhale?", "is_correct": True}, {"text": "किती झाले?", "is_correct": True}]}
    rev = ok(admin.post(f"{L}/{lesson['id']}/exercises", {"revision": lesson["revision"], **ex}), 201)["revision"]
    assert ok(admin.post(f"/api/admin/validate/lesson/{lesson['id']}", {}))["ok"] is True                     # the dry run agrees before publishing
    published = ok(admin.post(f"/api/admin/publish/lesson/{lesson['id']}", {"revision": rev}))
    assert published["status"] == "published" and published["warnings"] == []
    learner = as_learner(client2, "newmr@example.com")
    assert [l["slug"] for l in lessons(learner)][-1] == "market-extra"


def test_a_marathi_lesson_cannot_use_hindi_vocabulary(admin):
    with db() as conn:
        hindi_item = conn.execute("SELECT id FROM vocabulary_items WHERE language_id = (SELECT id FROM languages WHERE code = 'hi') LIMIT 1").fetchone()[0]
    lesson = ok(admin.post(L, {"slug": "mixed", "language": "mr", "cefr": "A1", "title": "Mixed", "description": "No.", "topics": ["food"]}), 201)
    r = admin.put(f"{L}/{lesson['id']}/vocabulary", {"revision": lesson["revision"], "item_ids": [hindi_item]})
    assert r.status_code == 422 and "different language" in r.text


# =====================================================================================================================
# situations and listening are Marathi's own (0033; the full flows: tests/test_marathi_learning.py)
# =====================================================================================================================
def test_marathi_situations_and_listening_are_marathi_not_hindi(marathi):
    with db() as conn:
        sits = {r[0] for r in conn.execute(f"SELECT id FROM situations WHERE language_id = {MR} AND cefr_code = 'A1'")}
        acts = {r[0] for r in conn.execute(f"SELECT id FROM listening_activities WHERE language_id = {MR} AND cefr_code = 'A1'")}
    assert {s["id"] for s in marathi.get("/api/situations").json()["situations"]} == sits and len(sits) == 8
    assert {a["id"] for a in marathi.get("/api/listening").json()["activities"]} == acts and len(acts) == 22

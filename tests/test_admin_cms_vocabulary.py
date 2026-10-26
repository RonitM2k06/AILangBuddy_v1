"""Phase 13D: vocabulary, translations, topics and the read-only reference data."""
import pytest

from backend import main
from backend.admin import audit
from backend.db import connect

from . import adm
from .adm import Api, admin, audit_rows, item_ids, new_lesson, ok, register_browser  # noqa: F401

V = "/api/admin/content/vocabulary"
T = "/api/admin/content/topics"


def vrow(i):
    with connect(main.DB_PATH) as conn:
        return dict(conn.execute("SELECT * FROM vocabulary_items WHERE id = ?", (i,)).fetchone())


def tr(i, lang):
    with connect(main.DB_PATH) as conn:
        r = conn.execute("SELECT meaning, natural FROM vocabulary_translations WHERE item_id = ? AND language_id = (SELECT id FROM languages WHERE code = ?)", (i, lang)).fetchone()
        return dict(r) if r else None


def new_word(admin, text="naya-shabd", **over):
    return ok(admin.post(V, {"language": "hi", "cefr": "A1", "kind": "word", "text": text, "pronunciation": "naya shabd", **over}), 201)


# ---------- create ----------
def test_create_with_translations_audits_each_part(admin, audit_rows):
    v = ok(admin.post(V, {"language": "hi", "cefr": "A1", "kind": "phrase", "text": "kaise ho", "pronunciation": "kaise ho",
                          "translations": [{"language": "en", "meaning": "How are you?", "natural": "How's it going?"}, {"language": "es", "meaning": "¿Cómo estás?"}]}), 201)
    assert (v["language"], v["cefr"], v["kind"], v["text"], v["referenced"], v["used_by_published"]) == ("hi", "A1", "phrase", "kaise ho", False, False)
    assert v["translations"] == [{"language": "en", "meaning": "How are you?", "natural": "How's it going?"}, {"language": "es", "meaning": "¿Cómo estás?", "natural": None}]
    assert v["usage"] == {"lessons": 0, "situations": 0, "listening_activities": 0}
    events = [(e["action"], e["entity_type"], e["entity_key"]) for e in audit_rows()]
    assert events == [("create", "vocabulary", None), ("create", "vocabulary_translation", "en"), ("create", "vocabulary_translation", "es")]
    assert "How are you" not in str([e["meta_json"] for e in audit_rows()])


@pytest.mark.parametrize("over", [{"language": "xx"}, {"cefr": "C2"}, {"kind": "sentence"}, {"text": " "}, {"text": "bad\x00"}, {"text": "x" * 301}, {"pronunciation": "p\x01"},
                                  {"translations": [{"language": "en", "meaning": "a"}, {"language": "en", "meaning": "b"}]}, {"translations": [{"language": "hi", "meaning": "same language"}]},
                                  {"translations": [{"language": "zz", "meaning": "x"}]}, {"translations": [{"language": "en", "meaning": " "}]}])
def test_create_rejects_bad_input_and_leaves_nothing(admin, audit_rows, over):
    r = admin.post(V, {"language": "hi", "cefr": "A1", "kind": "word", "text": "probe", **over})
    assert r.status_code == 422
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM vocabulary_items WHERE text = 'probe'").fetchone()[0] == 0
    assert audit_rows() == []


def test_create_refuses_a_duplicate_text(admin):
    new_word(admin, "dup-word")
    r = admin.post(V, {"language": "hi", "cefr": "A1", "kind": "word", "text": "dup-word"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "text_taken"
    assert admin.post(V, {"language": "hi", "cefr": "A1", "kind": "word", "text": "dup-word", "x": 1}).status_code == 422


# ---------- read ----------
def test_list_filters_search_and_paginate(admin):
    new_word(admin, "zebra-shabd")
    page = ok(admin.get(V))
    assert page["total"] == 1130 and set(page["items"][0])     # 53 Hindi + 199 Marathi (0031, 0032, 0035) + 178 Kannada (0037, 0038) + 198 Tamil (0040-0045) + 66 French (0044) + 176 Bengali (0048, 0049) + 64 Telugu (0051) + 65 Urdu (0052) + 65 Kashmiri (0055) + 65 Dogri (0056) + the new word == {"id", "language", "cefr", "kind", "text", "pronunciation", "has_english"}
    assert ok(admin.get(V + "?q=zebra"))["items"][0]["has_english"] is False
    assert ok(admin.get(V + "?language=hi&cefr=A1&kind=word&q=zebra"))["total"] == 1 and ok(admin.get(V + "?language=es"))["total"] == 0 and ok(admin.get(V + "?kind=phrase"))["total"] >= 1
    assert ok(admin.get(V + "?q=Paani"))["total"] >= 1                                                         # the pronunciation guide is searched too
    p1, p2 = ok(admin.get(V + "?limit=10&offset=0")), ok(admin.get(V + "?limit=10&offset=10"))
    assert len(p1["items"]) == 10 and not {i["id"] for i in p1["items"]} & {i["id"] for i in p2["items"]}
    assert sum(i["has_english"] for i in ok(admin.get(V + "?language=hi&limit=100"))["items"]) == 53       # every seeded Hindi item, not the new word
    marathi = ok(admin.get(V + "?language=mr&limit=100"))
    assert marathi["total"] == 199 and len(marathi["items"]) == 100 and all(i["has_english"] and i["language"] == "mr" for i in marathi["items"])
    assert admin.get(V + "?kind=sentence").status_code == 422 and admin.get(V + "?limit=0").status_code == 422


def test_detail_reports_translations_and_usage(admin):
    first = item_ids(1)[0]
    d = ok(admin.get(f"{V}/{first}"))
    assert d["referenced"] is True and d["used_by_published"] is True and any(t["language"] == "en" for t in d["translations"])
    assert d["usage"]["listening_activities"] >= 1 and d["usage"]["lessons"] >= 0
    assert admin.get(f"{V}/99999").status_code == 404


# ---------- update ----------
def test_an_unreferenced_item_can_be_changed_freely(admin, audit_rows):
    v = new_word(admin)
    with connect(main.DB_PATH) as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (10, 'A2') ON CONFLICT DO NOTHING")
    r = ok(admin.patch(f"{V}/{v['id']}", {"cefr": "A2", "kind": "phrase", "text": "bilkul naya", "pronunciation": "bilkul naya"}))
    assert (r["cefr"], r["kind"], r["text"]) == ("A2", "phrase", "bilkul naya")
    ev = audit_rows()[-1]
    assert (ev["action"], ev["entity_type"], ev["entity_id"]) == ("update", "vocabulary", v["id"]) and ev["meta_json"] == '{"changed_fields":["cefr","kind","pronunciation","text"]}'
    assert "bilkul" not in ev["meta_json"]


def test_a_referenced_item_keeps_its_level_kind_and_meaning_of_its_text(admin):
    first = item_ids(1)[0]
    before = vrow(first)
    with connect(main.DB_PATH) as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (10, 'A2') ON CONFLICT DO NOTHING")
    for patch in ({"cefr": "A2"}, {"kind": "phrase" if before["kind"] == "word" else "word"}, {"text": before["text"] + " badla hua"}, {"text": "bilkul alag"}):
        r = admin.patch(f"{V}/{first}", patch)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "vocabulary_in_use", patch
    assert vrow(first) == before


def test_a_referenced_item_allows_only_typo_level_text_changes_and_pronunciation(admin, audit_rows):
    first = item_ids(1)[0]
    before = vrow(first)
    shouty = before["text"].upper() + " ।" if before["text"].isascii() else before["text"] + " ।"
    r = ok(admin.patch(f"{V}/{first}", {"text": shouty, "pronunciation": "a corrected guide"}))
    assert r["text"] == shouty and r["pronunciation"] == "a corrected guide" and vrow(first)["cefr_code"] == before["cefr_code"]
    assert '"changed_fields":["pronunciation","text"]' in audit_rows()[-1]["meta_json"]


def test_unchanged_values_are_not_an_edit(admin, audit_rows):
    first = item_ids(1)[0]
    n = len(audit_rows())
    cur = vrow(first)
    ok(admin.patch(f"{V}/{first}", {"cefr": cur["cefr_code"], "kind": cur["kind"], "text": cur["text"], "pronunciation": cur["pronunciation"]}))
    assert len(audit_rows()) == n


def test_update_rejections_and_conflicts(admin):
    a, b = new_word(admin, "word-a"), new_word(admin, "word-b")
    assert admin.patch(f"{V}/{b['id']}", {"text": "word-a"}).json()["detail"]["code"] == "text_taken"
    for patch in ({"text": " "}, {"text": "x\x00"}, {"cefr": "C2"}, {"kind": "sentence"}, {"language": "es"}, {"pronunciation": "p\x01"}):
        assert admin.patch(f"{V}/{b['id']}", patch).status_code == 422
    assert admin.patch(f"{V}/99999", {"text": "x"}).status_code == 404
    assert vrow(b["id"])["text"] == "word-b"


@pytest.mark.parametrize("referrer", ["lesson_vocabulary", "exercise", "weakness"])
def test_every_kind_of_reference_locks_the_level(admin, referrer):
    v = new_word(admin, f"locked-{referrer}")
    with connect(main.DB_PATH) as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (10, 'A2') ON CONFLICT DO NOTHING")
    assert admin.patch(f"{V}/{v['id']}", {"cefr": "A2"}).status_code == 200                                  # free while nothing refers to it
    ok(admin.patch(f"{V}/{v['id']}", {"cefr": "A1"}))
    with connect(main.DB_PATH) as conn:
        if referrer == "lesson_vocabulary":
            conn.execute("INSERT INTO lesson_vocabulary(lesson_id, item_id, language_id, sort_order) VALUES ((SELECT id FROM lessons WHERE slug = 'food' AND language_id = 10), ?, 10, 99)", (v["id"],))
        elif referrer == "exercise":
            conn.execute("INSERT INTO exercises(lesson_id, language_id, kind, prompt, item_id, sort_order, difficulty) VALUES ((SELECT id FROM lessons WHERE slug = 'food' AND language_id = 10), 10, 'translation', 'p', ?, 98, 1)", (v["id"],))
        else:
            adm.item_weakness(conn, adm.add_user(conn), v["id"])
    r = admin.patch(f"{V}/{v['id']}", {"cefr": "A2"})
    assert r.status_code == 409 and ok(admin.get(f"{V}/{v['id']}"))["referenced"] is True


# ---------- translations ----------
def test_a_translation_can_always_be_added_even_to_published_content(admin, audit_rows):
    first = item_ids(1)[0]
    assert ok(admin.get(f"{V}/{first}"))["used_by_published"] is True
    r = ok(admin.put(f"{V}/{first}/translations/es", {"meaning": "agua", "natural": "el agua"}))
    assert {"language": "es", "meaning": "agua", "natural": "el agua"} in r["translations"] and tr(first, "es") == {"meaning": "agua", "natural": "el agua"}
    ev = audit_rows()[-1]
    assert (ev["action"], ev["entity_type"], ev["entity_id"], ev["entity_key"], ev["meta_json"]) == ("create", "vocabulary_translation", first, "es", "{}")


def test_editing_an_existing_translation_waits_until_published_content_lets_go(admin, audit_rows):
    first = item_ids(1)[0]
    english = tr(first, "en")
    r = admin.put(f"{V}/{first}/translations/en", {"meaning": "a different meaning"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "referenced_by_published" and tr(first, "en") == english
    same = ok(admin.put(f"{V}/{first}/translations/en", {"meaning": english["meaning"], "natural": english["natural"]}))
    assert tr(first, "en") == english and same["id"] == first                                                  # re-sending the same text is not a change
    n = len(audit_rows())
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE lessons SET status = 'draft', published_at = NULL WHERE id IN (SELECT lesson_id FROM lesson_vocabulary WHERE item_id = ?)", (first,))
        conn.execute("UPDATE exercises SET item_id = item_id WHERE item_id = ?", (first,))
        conn.execute("UPDATE situations SET status = 'draft', published_at = NULL WHERE id IN (SELECT situation_id FROM situation_steps WHERE item_id = ?)", (first,))
        conn.execute("UPDATE listening_activities SET status = 'draft', published_at = NULL WHERE item_id = ? OR id IN (SELECT activity_id FROM listening_options WHERE item_id = ?)", (first, first))
        conn.execute("UPDATE lessons SET status = 'draft', published_at = NULL WHERE id IN (SELECT lesson_id FROM exercises WHERE item_id = ?)", (first,))
    assert ok(admin.get(f"{V}/{first}"))["used_by_published"] is False
    ok(admin.put(f"{V}/{first}/translations/en", {"meaning": "a different meaning", "natural": None}))
    assert tr(first, "en") == {"meaning": "a different meaning", "natural": None}
    ev = audit_rows()[n:]
    assert len(ev) == 1 and ev[0]["action"] == "update" and ev[0]["meta_json"] == '{"changed_fields":["meaning","natural"]}' if english["natural"] else '{"changed_fields":["meaning"]}'


@pytest.mark.parametrize("lang,body,status", [("zz", {"meaning": "x"}, 422), ("hi", {"meaning": "x"}, 422), ("es", {"meaning": " "}, 422), ("es", {"meaning": "x\x00"}, 422),
                                              ("es", {"meaning": "x" * 301}, 422), ("es", {"meaning": "x", "extra": 1}, 422), ("es", {}, 422)])
def test_translation_rejections(admin, lang, body, status):
    v = new_word(admin)
    assert admin.put(f"{V}/{v['id']}/translations/{lang}", body).status_code == status
    assert tr(v["id"], "es") is None


def test_translation_404(admin):
    assert admin.put(f"{V}/99999/translations/es", {"meaning": "x"}).status_code == 404


def test_adding_english_is_what_lets_content_validate(admin):
    v = new_word(admin, "needs-english")
    lesson = new_lesson(admin)
    ok(admin.put(f"/api/admin/content/lessons/{lesson['id']}/vocabulary", {"revision": lesson["revision"], "item_ids": [item_ids(1)[0], v["id"]]}))
    findings = ok(admin.post(f"/api/admin/validate/lesson/{lesson['id']}"))["findings"]
    assert [f["code"] for f in findings] == ["vocabulary_missing_english"]
    ok(admin.put(f"{V}/{v['id']}/translations/en", {"meaning": "a new word"}))
    assert ok(admin.post(f"/api/admin/validate/lesson/{lesson['id']}"))["findings"] == []


# ---------- topics ----------
def test_topics_list_create_and_update(admin, audit_rows):
    t = ok(admin.get(T))["items"]
    assert len(t) == 8 and set(t[0]) == {"id", "slug", "name", "icon", "lessons", "situations", "listening_activities"}
    food = next(x for x in t if x["slug"] == "food")
    assert food["lessons"] >= 1 and food["situations"] >= 1 and food["listening_activities"] >= 1
    made = ok(admin.post(T, {"slug": "weather", "name": "Weather", "icon": "☀️"}), 201)
    assert (made["slug"], made["name"], made["icon"], made["lessons"]) == ("weather", "Weather", "☀️", 0)
    r = ok(admin.patch(f"{T}/{made['id']}", {"name": "The weather", "icon": "🌦️"}))
    assert (r["name"], r["icon"], r["slug"]) == ("The weather", "🌦️", "weather")
    evs = [(e["action"], e["entity_type"], e["entity_key"], e["meta_json"]) for e in audit_rows()]
    assert evs == [("create", "topic", "weather", "{}"), ("update", "topic", "weather", '{"changed_fields":["icon","name"]}')]


@pytest.mark.parametrize("body", [{"slug": "Bad Slug", "name": "n", "icon": "i"}, {"slug": "ok", "name": " ", "icon": "i"}, {"slug": "ok", "name": "n", "icon": ""}, {"slug": "ok", "name": "n\x00", "icon": "i"},
                                  {"slug": "ok", "name": "n", "icon": "x" * 17}, {"slug": "ok", "name": "x" * 61, "icon": "i"}, {"slug": "ok", "name": "n", "icon": "i", "extra": 1}])
def test_topic_create_rejections(admin, audit_rows, body):
    assert admin.post(T, body).status_code == 422 and audit_rows() == []


def test_topic_conflict_and_immutable_slug(admin):
    assert admin.post(T, {"slug": "food", "name": "Food again", "icon": "x"}).json()["detail"]["code"] == "slug_taken"
    food = next(x for x in ok(admin.get(T))["items"] if x["slug"] == "food")
    assert admin.patch(f"{T}/{food['id']}", {"slug": "meals"}).status_code == 422
    assert admin.patch(f"{T}/{food['id']}", {"name": " "}).status_code == 422 and admin.patch(f"{T}/99999", {"name": "x"}).status_code == 404


def test_a_noop_topic_edit_is_not_audited(admin, audit_rows):
    food = next(x for x in ok(admin.get(T))["items"] if x["slug"] == "food")
    ok(admin.patch(f"{T}/{food['id']}", {"name": food["name"], "icon": food["icon"]}))
    assert audit_rows() == []


# ---------- reference data ----------
def test_reference_data_is_read_only_and_complete(admin):
    langs = ok(admin.get("/api/admin/content/languages"))["items"]
    hi = next(l for l in langs if l["code"] == "hi")
    with connect(main.DB_PATH) as conn:
        expected = [r[0] for r in conn.execute("SELECT l.cefr_code FROM language_levels l JOIN cefr_levels c ON c.code = l.cefr_code WHERE l.language_id = 10 ORDER BY c.rank")]
    assert hi["cefr_levels"] == expected and "A1" in expected and set(hi) == {"code", "name", "native_name", "cefr_levels"}
    assert len(langs) == 19 and next(l for l in langs if l["code"] == "mr")["cefr_levels"] == ["A1", "A2", "B1"]     # Marathi: in the catalogue (0030), A1/A2 (0031), B1 (0035); Kannada (0036), Tamil (0039), Bengali (0047), Telugu and Urdu (0050), Kashmiri and Dogri (0054)
    assert [c["code"] for c in ok(admin.get("/api/admin/content/cefr-levels"))["items"]] == ["A1", "A2", "B1", "B2", "C1", "C2"]
    assert [(g["code"], g["min_age"], g["max_age"]) for g in ok(admin.get("/api/admin/content/age-groups"))["items"]] == [("child", 0, 9), ("teen", 10, 17), ("adult", 18, None)]
    for path in ("languages", "cefr-levels", "age-groups"):
        for method in ("post", "put", "patch", "delete"):
            assert getattr(admin, method)(f"/api/admin/content/{path}").status_code in (404, 405)
            assert getattr(admin, method)(f"/api/admin/content/{path}/1").status_code in (404, 405)


# ---------- atomicity and access ----------
def test_failing_audit_rolls_vocabulary_writes_back(admin, monkeypatch):
    v = new_word(admin, "rollback-me")
    def boom(*a, **k):
        raise audit.AuditError("down")
    monkeypatch.setattr(audit, "record", boom)
    for call in (lambda: admin.c.post(V, json={"language": "hi", "cefr": "A1", "kind": "word", "text": "ghost", "translations": [{"language": "en", "meaning": "g"}]}, headers=adm.CSRF),
                 lambda: admin.c.patch(f"{V}/{v['id']}", json={"text": "changed"}, headers=adm.CSRF),
                 lambda: admin.c.put(f"{V}/{v['id']}/translations/es", json={"meaning": "x"}, headers=adm.CSRF),
                 lambda: admin.c.post(T, json={"slug": "ghost-topic", "name": "G", "icon": "g"}, headers=adm.CSRF)):
        with pytest.raises(audit.AuditError):
            call()
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM vocabulary_items WHERE text = 'ghost'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM topics WHERE slug = 'ghost-topic'").fetchone()[0] == 0
    assert vrow(v["id"])["text"] == "rollback-me" and tr(v["id"], "es") is None


def test_routes_refuse_non_admins_and_offer_no_delete(client, admin):
    v = new_word(admin)
    for who in (Api(), register_browser("learner", "l@example.com"), register_browser("parent", "p@example.com"), adm.demo_browser()):
        assert who.get(V).status_code in (401, 403) and who.get(T).status_code in (401, 403) and who.post(V, {"language": "hi", "cefr": "A1", "kind": "word", "text": "x"}).status_code in (401, 403)
        assert who.patch(f"{V}/{v['id']}", {"text": "pwned"}).status_code in (401, 403) and who.put(f"{V}/{v['id']}/translations/es", {"meaning": "x"}).status_code in (401, 403)
    for url in (f"{V}/{v['id']}", f"{V}/{v['id']}/translations/en", f"{T}/1"):
        assert admin.delete(url).status_code in (404, 405)
    assert vrow(v["id"])["text"] == "naya-shabd"


def test_an_item_used_only_as_an_option_of_a_published_activity_counts_as_published_use(admin):
    with connect(main.DB_PATH) as conn:
        item = conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (10, 'A1', 'word', 'option-only-word')").lastrowid
        conn.execute("INSERT INTO vocabulary_translations(item_id, language_id, meaning) VALUES (?, 1, 'option only')", (item,))
        conn.execute("INSERT INTO listening_options(activity_id, language_id, item_id, sort_order) VALUES ((SELECT id FROM listening_activities WHERE slug = 'food-meaning' AND language_id = 10), 10, ?, 9)", (item,))
    assert ok(admin.get(f"{V}/{item}"))["used_by_published"] is True
    assert admin.put(f"{V}/{item}/translations/en", {"meaning": "changed"}).status_code == 409

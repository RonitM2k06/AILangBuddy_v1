"""Phase 13D: the lesson CMS (lessons, exercises, vocabulary links). Every rule is asserted from the response AND from the database."""
import pytest

from backend import main
from backend.admin import audit
from backend.db import connect

from . import adm
from .adm import Api, admin, audit_rows, item_ids, mc, new_lesson, ok, register_browser  # noqa: F401

L = "/api/admin/content/lessons"


def lesson_row(lid):
    with connect(main.DB_PATH) as conn:
        return dict(conn.execute("SELECT * FROM lessons WHERE id = ?", (lid,)).fetchone())


def body(**over):
    return {"slug": "my-lesson", "language": "hi", "cefr": "A1", "title": "My lesson", "description": "About food.", **over}


# ---------- create ----------
def test_create_makes_a_draft_at_revision_one_with_an_audit_event(admin, audit_rows):
    lesson = ok(admin.post(L, body(topics=["food", "greetings"], age_groups=["teen", "adult"], situation="At a cafe", tip="Smile")), 201)
    assert (lesson["status"], lesson["revision"], lesson["slug"], lesson["cefr"], lesson["language"]["code"]) == ("draft", 1, "my-lesson", "A1", "hi")
    assert [t["slug"] for t in lesson["topics"]] == ["food", "greetings"] and lesson["age_groups"] == ["teen", "adult"]
    assert (lesson["situation"], lesson["tip"], lesson["exercises"], lesson["vocabulary"], lesson["published_at"], lesson["archived_at"]) == ("At a cafe", "Smile", [], [], None, None)
    row = lesson_row(lesson["id"])
    assert row["status"] == "draft" and row["revision"] == 1 and row["updated_at"] and row["sort_order"] >= 1
    events = audit_rows()
    assert len(events) == 1 and (events[0]["action"], events[0]["entity_type"], events[0]["entity_id"], events[0]["entity_key"], events[0]["outcome"]) == ("create", "lesson", lesson["id"], "my-lesson", "ok")
    assert events[0]["meta_json"] == '{"revision_after":1}' and len(events[0]["request_id"]) == 32


def test_the_actor_of_every_event_is_the_signed_in_admin_never_the_body(admin, audit_rows):
    ok(admin.post(L, body()), 201)
    actor = audit_rows()[0]
    with connect(main.DB_PATH) as conn:
        me = conn.execute("SELECT id, handle FROM users WHERE email = 'admin@example.com'").fetchone()
    assert (actor["actor_user_id"], actor["actor_label"]) == (me["id"], me["handle"])
    forged = admin.post(L, body(slug="forged", actor="someone-else"))
    assert forged.status_code == 422 and len(audit_rows()) == 1
    assert admin.post(L, body(slug="forged2", actor_user_id=1)).status_code == 422


def test_create_defaults_the_position_to_the_end_of_the_level(admin):
    a, b = ok(admin.post(L, body(slug="p-a")), 201), ok(admin.post(L, body(slug="p-b")), 201)
    assert b["sort_order"] == a["sort_order"] + 1
    with connect(main.DB_PATH) as conn:
        assert a["sort_order"] == conn.execute("SELECT MAX(sort_order) FROM lessons WHERE slug <> 'p-a' AND slug <> 'p-b' AND cefr_code = 'A1' AND language_id = 10").fetchone()[0] + 1


@pytest.mark.parametrize("over,field", [
    ({"slug": "Bad Slug"}, "slug"), ({"slug": "-x"}, "slug"), ({"slug": "x" * 61}, "slug"), ({"slug": ""}, "slug"), ({"slug": "ünï"}, "slug"),
    ({"language": "xx"}, "language"), ({"cefr": "Z9"}, "cefr"), ({"cefr": "C2"}, "cefr"),
    ({"title": "   "}, "title"), ({"title": "x" * 121}, None), ({"title": "bad\x07"}, "title"), ({"title": "two\nlines"}, "title"),
    ({"description": ""}, "description"), ({"description": "bad\x00"}, "description"), ({"description": "ok\nstill ok"}, "OK"),
    ({"situation": "bad\x01"}, "situation"), ({"tip": "x" * 501}, None),
    ({"topics": ["nope"]}, "topics"), ({"topics": ["food", "food"]}, "topics"),
    ({"age_groups": ["baby"]}, "age_groups"), ({"age_groups": ["teen", "teen"]}, "age_groups"),
    ({"sort_order": 0}, None), ({"sort_order": 10000}, None),
])
def test_create_rejects_bad_input(admin, audit_rows, over, field):
    r = admin.post(L, body(**over))
    if field == "OK":
        assert r.status_code == 201
        return
    assert r.status_code == 422, r.text
    if field:
        assert any(field in e["loc"] for e in r.json()["detail"])
    assert audit_rows() == []
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM lessons WHERE slug = 'my-lesson'").fetchone()[0] == 0


def test_create_refuses_unknown_and_missing_fields(admin):
    for bad in ({**body(), "status": "published"}, {**body(), "revision": 3}, {**body(), "id": 99}, {k: v for k, v in body().items() if k != "title"}):
        assert admin.post(L, bad).status_code == 422
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM lessons WHERE status = 'published' AND slug = 'my-lesson'").fetchone()[0] == 0


def test_slug_and_position_conflicts_are_409(admin):
    ok(admin.post(L, body(slug="dup", sort_order=50)), 201)
    r = admin.post(L, body(slug="dup", sort_order=51))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "slug_taken"
    r = admin.post(L, body(slug="other", sort_order=50))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "sort_order_taken"
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM lessons WHERE slug IN ('dup', 'other')").fetchone()[0] == 1


def test_the_same_slug_is_fine_in_another_language(admin):
    with connect(main.DB_PATH) as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (2, 'A1') ON CONFLICT DO NOTHING")
    assert admin.post(L, body(slug="greetings")).status_code == 409                            # 'greetings' exists for Hindi
    assert admin.post(L, body(slug="greetings", language="es")).status_code == 201


# ---------- read ----------
def test_detail_shows_the_admin_view_including_correct_answers(admin):
    lesson = new_lesson(admin)
    assert lesson["exercises"][0]["answers"][0]["is_correct"] is True and [a["is_correct"] for a in lesson["exercises"][0]["answers"]] == [True, False, False]
    assert lesson["vocabulary"][0]["meaning_en"] and lesson["vocabulary"][0]["text"]


def test_detail_of_a_seeded_lesson_matches_the_database(admin):
    with connect(main.DB_PATH) as conn:
        lid = conn.execute("SELECT id FROM lessons WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0]
        n_ex = conn.execute("SELECT COUNT(*) FROM exercises WHERE lesson_id = ?", (lid,)).fetchone()[0]
        n_voc = conn.execute("SELECT COUNT(*) FROM lesson_vocabulary WHERE lesson_id = ?", (lid,)).fetchone()[0]
    d = ok(admin.get(f"{L}/{lid}"))
    assert (d["status"], d["slug"], len(d["exercises"]), len(d["vocabulary"])) == ("published", "food", n_ex, n_voc)
    assert all(any(a["is_correct"] for a in e["answers"]) for e in d["exercises"] if e["kind"] == "multiple_choice")


def test_detail_404(admin):
    assert admin.get(f"{L}/99999").status_code == 404
    assert admin.get(f"{L}/abc").status_code == 422


def test_list_filters_search_and_paginates(admin):
    ok(admin.post(L, body(slug="zz-draft", title="Zebra crossing")), 201)
    page = ok(admin.get(L))
    assert set(page) == {"items", "total", "limit", "offset"} and page["total"] == 158 and page["limit"] == 25      # 7 Hindi + 27 Marathi + 25 Kannada + 28 Tamil + 9 French + 25 Bengali + 9 Telugu + 9 Urdu + 9 Kashmiri + 9 Dogri + the draft
    row = next(i for i in page["items"] if i["slug"] == "zz-draft")
    assert set(row) == {"id", "slug", "title", "language", "cefr", "status", "revision", "sort_order", "updated_at", "published_at", "archived_at", "exercises", "vocabulary"}
    assert (row["status"], row["exercises"], row["vocabulary"]) == ("draft", 0, 0)
    assert ok(admin.get(L + "?status=draft"))["total"] == 1 and ok(admin.get(L + "?status=published"))["total"] == 157 and ok(admin.get(L + "?status=archived"))["total"] == 0
    assert ok(admin.get(L + "?q=zebra"))["items"][0]["slug"] == "zz-draft" and ok(admin.get(L + "?q=ZZ-DR"))["total"] == 1
    assert ok(admin.get(L + "?language=hi"))["total"] == 8 and ok(admin.get(L + "?language=mr"))["total"] == 27 and ok(admin.get(L + "?language=es"))["total"] == 0 and ok(admin.get(L + "?language=zz"))["total"] == 0
    assert ok(admin.get(L + "?cefr=A1"))["total"] == 8 + 11 + 9 + 11 + 9 + 9 + 9 + 9 + 9 + 9 and ok(admin.get(L + "?cefr=B1"))["total"] == 6 + 6 + 6 + 6 and ok(admin.get(L + "?cefr=B2"))["total"] == 0
    assert ok(admin.get(L + "?status=draft&language=hi&cefr=A1&q=zebra"))["total"] == 1
    p1, p2 = ok(admin.get(L + "?limit=3&offset=0")), ok(admin.get(L + "?limit=3&offset=3"))
    assert len(p1["items"]) == 3 and len(p2["items"]) == 3 and not {i["id"] for i in p1["items"]} & {i["id"] for i in p2["items"]} and p1["total"] == 158
    assert ok(admin.get(L + "?limit=3&offset=156"))["items"].__len__() == 2 and ok(admin.get(L + "?offset=161"))["items"] == []


def test_list_search_treats_wildcards_literally(admin):
    ok(admin.post(L, body(slug="pct", title="100% sure")), 201)
    assert ok(admin.get(L + "?q=100%25"))["total"] == 1 and ok(admin.get(L + "?q=%25"))["total"] == 1 and ok(admin.get(L + "?q=_"))["total"] == 0
    assert ok(admin.get(L + "?q=" + "%5C"))["total"] == 0


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "status=deleted", "limit=abc", "q=" + "x" * 101, "language=" + "x" * 17])
def test_list_rejects_bad_parameters(admin, query):
    assert admin.get(L + "?" + query).status_code == 422


# ---------- update ----------
def test_update_bumps_the_revision_once_and_records_the_changed_field_names(admin, audit_rows):
    lesson = new_lesson(admin)
    before = len(audit_rows())
    r = ok(admin.patch(f"{L}/{lesson['id']}", {"revision": lesson["revision"], "title": "New title", "tip": "A tip"}))
    assert (r["title"], r["tip"], r["revision"]) == ("New title", "A tip", lesson["revision"] + 1)
    assert lesson_row(lesson["id"])["revision"] == lesson["revision"] + 1
    events = audit_rows()[before:]
    assert len(events) == 1 and (events[0]["action"], events[0]["entity_type"]) == ("update", "lesson")
    assert events[0]["meta_json"] == f'{{"changed_fields":["tip","title"],"revision_after":{lesson["revision"] + 1},"revision_before":{lesson["revision"]}}}'
    assert "New title" not in events[0]["meta_json"] and "A tip" not in events[0]["meta_json"]


def test_a_stale_revision_is_refused_with_the_current_one(admin, audit_rows):
    lesson = new_lesson(admin)
    ok(admin.patch(f"{L}/{lesson['id']}", {"revision": lesson["revision"], "title": "First"}))
    n = len(audit_rows())
    r = admin.patch(f"{L}/{lesson['id']}", {"revision": lesson["revision"], "title": "Second"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "stale_revision" and r.json()["detail"]["current_revision"] == lesson["revision"] + 1
    assert lesson_row(lesson["id"])["title"] == "First" and len(audit_rows()) == n


@pytest.mark.parametrize("revision", [0, -1, 10**10])
def test_a_nonsense_revision_is_a_validation_error(admin, revision):
    lesson = new_lesson(admin)
    assert admin.patch(f"{L}/{lesson['id']}", {"revision": revision, "title": "x"}).status_code == 422


def test_a_future_revision_is_stale_too(admin):
    lesson = new_lesson(admin)
    assert admin.patch(f"{L}/{lesson['id']}", {"revision": lesson["revision"] + 5, "title": "x"}).status_code == 409


def test_the_revision_is_required(admin):
    lesson = new_lesson(admin)
    assert admin.patch(f"{L}/{lesson['id']}", {"title": "x"}).status_code == 422


def test_an_edit_that_changes_nothing_is_not_an_edit(admin, audit_rows):
    lesson = new_lesson(admin)
    n = len(audit_rows())
    r = ok(admin.patch(f"{L}/{lesson['id']}", {"revision": lesson["revision"], "title": lesson["title"], "topics": ["food"], "age_groups": [], "tip": None}))
    assert r["revision"] == lesson["revision"] and len(audit_rows()) == n and lesson_row(lesson["id"])["revision"] == lesson["revision"]
    assert admin.patch(f"{L}/{lesson['id']}", {"revision": lesson["revision"] + 1, "title": lesson["title"]}).status_code == 409          # but a stale revision still counts


def test_update_changes_each_field(admin):
    lesson = new_lesson(admin)
    rev = lesson["revision"]
    for field, value in (("slug", "renamed"), ("title", "T2"), ("description", "D2\nmore"), ("situation", "S2"), ("tip", "Tip2"), ("cefr", "A1"), ("sort_order", 77)):
        patch = {"revision": rev, field: value}
        r = ok(admin.patch(f"{L}/{lesson['id']}", patch))
        if field != "cefr":
            assert r[field] == value
        rev = r["revision"]
    r = ok(admin.patch(f"{L}/{lesson['id']}", {"revision": rev, "topics": ["greetings", "transport"], "age_groups": ["child"]}))
    assert [t["slug"] for t in r["topics"]] == ["greetings", "transport"] and r["age_groups"] == ["child"]
    r = ok(admin.patch(f"{L}/{lesson['id']}", {"revision": r["revision"], "situation": None, "tip": None, "topics": [], "age_groups": []}))
    assert (r["situation"], r["tip"], r["topics"], r["age_groups"]) == (None, None, [], [])


def test_update_cannot_change_the_language_or_status(admin):
    lesson = new_lesson(admin)
    for bad in ({"language": "es"}, {"status": "published"}, {"published_at": "2020-01-01 00:00:00"}, {"archived_at": "2020-01-01 00:00:00"}, {"id": 5}, {"language_id": 1}):
        assert admin.patch(f"{L}/{lesson['id']}", {"revision": lesson["revision"], **bad}).status_code == 422
    assert lesson_row(lesson["id"])["status"] == "draft" and lesson_row(lesson["id"])["language_id"] == 10


@pytest.mark.parametrize("patch,status", [({"slug": "Bad"}, 422), ({"title": None}, 422), ({"title": " "}, 422), ({"description": None}, 422), ({"cefr": "C2"}, 422), ({"topics": ["nope"]}, 422),
                                          ({"age_groups": ["x"]}, 422), ({"sort_order": None}, 422), ({"sort_order": 0}, 422), ({"slug": "greetings"}, 409), ({"sort_order": 1}, 409)])
def test_update_rejects_bad_values_and_changes_nothing(admin, audit_rows, patch, status):
    lesson = new_lesson(admin)
    n = len(audit_rows())
    before = lesson_row(lesson["id"])
    r = admin.patch(f"{L}/{lesson['id']}", {"revision": lesson["revision"], **patch})
    assert r.status_code == status, r.text
    assert lesson_row(lesson["id"]) == before and len(audit_rows()) == n


def test_update_404(admin):
    assert admin.patch(f"{L}/99999", {"revision": 1, "title": "x"}).status_code == 404


# ---------- published and archived content cannot be edited ----------
@pytest.mark.parametrize("status", ["published", "archived"])
def test_only_a_draft_can_be_edited_anywhere_in_the_lesson(admin, audit_rows, status):
    lesson = new_lesson(admin)
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE lessons SET status = ?, published_at = CASE WHEN ? = 'published' THEN '2026-01-01 00:00:00' END, archived_at = CASE WHEN ? = 'archived' THEN '2026-01-01 00:00:00' END WHERE id = ?",
                     (status, status, status, lesson["id"]))
    n = len(audit_rows())
    with connect(main.DB_PATH) as conn:
        before = adm.table_dump(conn)
    rev, ex = lesson["revision"], lesson["exercises"][0]
    calls = [admin.patch(f"{L}/{lesson['id']}", {"revision": rev, "title": "edited"}),
             admin.post(f"{L}/{lesson['id']}/exercises", {"revision": rev, **mc("late exercise", item_ids(1)[0])}),
             admin.patch(f"{L}/{lesson['id']}/exercises/{ex['id']}", {"revision": rev, "prompt": "edited"}),
             admin.put(f"{L}/{lesson['id']}/vocabulary", {"revision": rev, "item_ids": []})]
    for r in calls:
        assert r.status_code == 409 and r.json()["detail"]["code"] == "not_draft", r.text
    assert ("unpublish" in calls[0].json()["detail"]["message"]) is (status == "published") and ("restore" in calls[0].json()["detail"]["message"]) is (status == "archived")
    assert len(audit_rows()) == n
    with connect(main.DB_PATH) as conn:
        assert adm.table_dump(conn) == before


def test_editing_a_published_lesson_never_reaches_validation_or_the_revision(admin):
    with connect(main.DB_PATH) as conn:
        lid = conn.execute("SELECT id FROM lessons WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0]
        rev = conn.execute("SELECT revision FROM lessons WHERE id = ?", (lid,)).fetchone()[0]
    assert admin.patch(f"{L}/{lid}", {"revision": rev, "title": "hijack"}).status_code == 409
    assert lesson_row(lid)["revision"] == rev and lesson_row(lid)["title"] != "hijack"


# ---------- exercises ----------
def test_create_a_multiple_choice_exercise(admin, audit_rows):
    lesson = new_lesson(admin, exercises=0)
    it = item_ids(1)[0]
    r = ok(admin.post(f"{L}/{lesson['id']}/exercises", {"revision": lesson["revision"], **mc("Pick it", it, correct=1, texts=("a", "b", "c", "d"))}), 201)
    e = r["exercise"]
    assert r["revision"] == lesson["revision"] + 1 and (e["kind"], e["prompt"], e["item_id"], e["difficulty"], e["sort_order"]) == ("multiple_choice", "Pick it", it, 1, 1)
    assert [(a["text"], a["is_correct"], a["sort_order"]) for a in e["answers"]] == [("a", False, 1), ("b", True, 2), ("c", False, 3), ("d", False, 4)]
    last = audit_rows()[-1]
    assert (last["action"], last["entity_type"], last["entity_id"], last["entity_key"]) == ("create", "exercise", e["id"], "api-lesson")
    assert last["meta_json"] == f'{{"revision_after":{r["revision"]},"revision_before":{lesson["revision"]}}}'
    assert "Pick it" not in last["meta_json"] and "right" not in last["meta_json"]


@pytest.mark.parametrize("kind", ["translation", "fill_blank"])
def test_create_a_typed_exercise(admin, kind):
    lesson = new_lesson(admin, exercises=0)
    r = ok(admin.post(f"{L}/{lesson['id']}/exercises", {"revision": lesson["revision"], "kind": kind, "prompt": "Type it", "difficulty": 3,
                                                        "answers": [{"text": "one"}, {"text": "uno", "is_correct": True}]}), 201)
    assert [(a["text"], a["is_correct"]) for a in r["exercise"]["answers"]] == [("one", True), ("uno", True)] and r["exercise"]["difficulty"] == 3


def test_exercises_are_appended_in_order_and_positions_cannot_collide(admin):
    lesson = new_lesson(admin, exercises=2)
    assert [e["sort_order"] for e in lesson["exercises"]] == [1, 2]
    r = admin.post(f"{L}/{lesson['id']}/exercises", {"revision": lesson["revision"], **mc("x"), "sort_order": 2})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "sort_order_taken"


@pytest.mark.parametrize("over,why", [
    ({"answers": [{"text": "only", "is_correct": True}]}, "one answer"),
    ({"answers": [{"text": "a", "is_correct": False}, {"text": "b", "is_correct": False}]}, "no correct answer"),
    ({"answers": [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]}, "two correct answers"),
    ({"answers": [{"text": "Same", "is_correct": True}, {"text": "same.", "is_correct": False}]}, "duplicate answers"),
    ({"answers": [{"text": "a", "is_correct": True}, {"text": "  ", "is_correct": False}]}, "blank answer"),
    ({"answers": [{"text": "a\x00", "is_correct": True}, {"text": "b", "is_correct": False}]}, "control char in answer"),
    ({"answers": [{"text": f"a{i}", "is_correct": i == 0} for i in range(9)]}, "nine answers"),
    ({"answers": [{"id": 5, "text": "a", "is_correct": True}, {"text": "b", "is_correct": False}]}, "answer id on create"),
    ({"prompt": "  "}, "blank prompt"), ({"prompt": "x\x07"}, "control char"), ({"difficulty": 0}, "difficulty 0"), ({"difficulty": 4}, "difficulty 4"), ({"item_id": 99999}, "unknown item"),
])
def test_multiple_choice_shape_is_enforced_on_write(admin, audit_rows, over, why):
    lesson = new_lesson(admin, exercises=0)
    n = len(audit_rows())
    r = admin.post(f"{L}/{lesson['id']}/exercises", {"revision": lesson["revision"], **mc("ok"), **over})
    assert r.status_code == 422, why
    assert len(audit_rows()) == n and lesson_row(lesson["id"])["revision"] == lesson["revision"]
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM exercises WHERE lesson_id = ?", (lesson["id"],)).fetchone()[0] == 0


@pytest.mark.parametrize("answers,why", [([], "no accepted answer"), ([{"text": "a", "is_correct": False}], "an incorrect row"), ([{"text": "a"}, {"text": "A!"}], "duplicate accepted"),
                                         ([{"text": f"a{i}"} for i in range(11)], "eleven accepted")])
def test_typed_shape_is_enforced_on_write(admin, answers, why):
    lesson = new_lesson(admin, exercises=0)
    r = admin.post(f"{L}/{lesson['id']}/exercises", {"revision": lesson["revision"], "kind": "translation", "prompt": "p", "answers": answers})
    assert r.status_code == 422, why


def test_the_exercise_item_must_be_in_the_lessons_language(admin):
    lesson = new_lesson(admin, exercises=0)
    with connect(main.DB_PATH) as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (2, 'A1') ON CONFLICT DO NOTHING")
        spanish = conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (2, 'A1', 'word', 'hola-x')").lastrowid
    r = admin.post(f"{L}/{lesson['id']}/exercises", {"revision": lesson["revision"], **mc("p", spanish)})
    assert r.status_code == 422 and "different language" in r.text


def test_an_exercise_kind_cannot_be_unknown_or_changed(admin):
    lesson = new_lesson(admin)
    assert admin.post(f"{L}/{lesson['id']}/exercises", {"revision": lesson["revision"], **mc("p"), "kind": "essay"}).status_code == 422
    ex = lesson["exercises"][0]
    assert admin.patch(f"{L}/{lesson['id']}/exercises/{ex['id']}", {"revision": lesson["revision"], "kind": "translation"}).status_code == 422


def test_update_an_exercise_prompt_item_difficulty_order_and_answers(admin, audit_rows):
    lesson = new_lesson(admin)
    ex = lesson["exercises"][0]
    other = item_ids(3)[2]
    url = f"{L}/{lesson['id']}/exercises/{ex['id']}"
    r = ok(admin.patch(url, {"revision": lesson["revision"], "prompt": "New prompt", "explanation": "Because.", "item_id": other, "difficulty": 2, "sort_order": 9}))
    e = r["exercise"]
    assert (e["prompt"], e["explanation"], e["item_id"], e["difficulty"], e["sort_order"], r["revision"]) == ("New prompt", "Because.", other, 2, 9, lesson["revision"] + 1)
    ids = [a["id"] for a in e["answers"]]
    new_answers = [{"id": ids[2], "text": "third now first", "is_correct": False}, {"id": ids[0], "text": "right one", "is_correct": True}, {"id": ids[1], "text": "wrong one!", "is_correct": False},
                   {"text": "brand new", "is_correct": False}]
    r2 = ok(admin.patch(url, {"revision": r["revision"], "answers": new_answers}))
    got = r2["exercise"]["answers"]
    assert [(a["text"], a["is_correct"], a["sort_order"]) for a in got] == [("third now first", False, 1), ("right one", True, 2), ("wrong one!", False, 3), ("brand new", False, 4)]
    assert [a["id"] for a in got][:3] == [ids[2], ids[0], ids[1]] and got[3]["id"] not in ids                 # corrected in place, one added
    last = audit_rows()[-1]
    assert last["meta_json"].startswith('{"changed_fields":["answers"]') and "brand new" not in last["meta_json"]


def test_answers_can_be_corrected_but_never_removed(admin):
    lesson = new_lesson(admin)
    ex = lesson["exercises"][0]
    ids = [a["id"] for a in ex["answers"]]
    url = f"{L}/{lesson['id']}/exercises/{ex['id']}"
    r = admin.patch(url, {"revision": lesson["revision"], "answers": [{"id": ids[0], "text": "right one", "is_correct": True}, {"id": ids[1], "text": "wrong one", "is_correct": False}]})
    assert r.status_code == 422 and "cannot be removed" in r.text
    assert admin.patch(url, {"revision": lesson["revision"], "answers": [{"id": 999999, "text": "x", "is_correct": True}, {"id": ids[1], "text": "wrong one", "is_correct": False},
                                                                          {"id": ids[2], "text": "wrong two", "is_correct": False}]}).status_code == 422
    assert admin.patch(url, {"revision": lesson["revision"], "answers": [{"id": ids[0], "text": "a", "is_correct": True}, {"id": ids[0], "text": "b", "is_correct": False},
                                                                          {"id": ids[2], "text": "c", "is_correct": False}]}).status_code == 422
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM exercise_answers WHERE exercise_id = ?", (ex["id"],)).fetchone()[0] == 3


def test_an_edit_may_not_leave_the_exercise_without_exactly_one_correct_answer(admin):
    lesson = new_lesson(admin)
    ex = lesson["exercises"][0]
    ids = [a["id"] for a in ex["answers"]]
    url = f"{L}/{lesson['id']}/exercises/{ex['id']}"
    both = [{"id": ids[0], "text": "right one", "is_correct": True}, {"id": ids[1], "text": "wrong one", "is_correct": True}, {"id": ids[2], "text": "wrong two", "is_correct": False}]
    assert admin.patch(url, {"revision": lesson["revision"], "answers": both}).status_code == 422
    none = [{"id": i, "text": f"t{n}", "is_correct": False} for n, i in enumerate(ids)]
    assert admin.patch(url, {"revision": lesson["revision"], "answers": none}).status_code == 422
    swapped = [{"id": ids[0], "text": "right one", "is_correct": False}, {"id": ids[1], "text": "wrong one", "is_correct": True}, {"id": ids[2], "text": "wrong two", "is_correct": False}]
    got = ok(admin.patch(url, {"revision": lesson["revision"], "answers": swapped}))["exercise"]["answers"]
    assert [a["is_correct"] for a in got] == [False, True, False]


def test_an_exercise_of_another_lesson_is_not_found(admin):
    a, b = new_lesson(admin, "lesson-a"), new_lesson(admin, "lesson-b")
    ex_b = b["exercises"][0]
    assert admin.patch(f"{L}/{a['id']}/exercises/{ex_b['id']}", {"revision": a["revision"], "prompt": "hijack"}).status_code == 404
    assert admin.patch(f"{L}/{a['id']}/exercises/99999", {"revision": a["revision"], "prompt": "x"}).status_code == 404
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT prompt FROM exercises WHERE id = ?", (ex_b["id"],)).fetchone()[0] == ex_b["prompt"]


def test_an_exercise_edit_that_changes_nothing_does_not_bump_the_revision(admin, audit_rows):
    lesson = new_lesson(admin)
    ex = lesson["exercises"][0]
    n = len(audit_rows())
    r = ok(admin.patch(f"{L}/{lesson['id']}/exercises/{ex['id']}", {"revision": lesson["revision"], "prompt": ex["prompt"], "difficulty": ex["difficulty"], "item_id": ex["item_id"],
                                                                     "answers": [{"id": a["id"], "text": a["text"], "is_correct": a["is_correct"]} for a in ex["answers"]]}))
    assert r["revision"] == lesson["revision"] and len(audit_rows()) == n


def test_the_exercise_position_cannot_be_blank_or_taken(admin):
    lesson = new_lesson(admin, exercises=2)
    e1, e2 = lesson["exercises"]
    assert admin.patch(f"{L}/{lesson['id']}/exercises/{e1['id']}", {"revision": lesson["revision"], "sort_order": None}).status_code == 422
    assert admin.patch(f"{L}/{lesson['id']}/exercises/{e1['id']}", {"revision": lesson["revision"], "sort_order": 0}).status_code == 422
    r = admin.patch(f"{L}/{lesson['id']}/exercises/{e1['id']}", {"revision": lesson["revision"], "sort_order": 2})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "sort_order_taken"


# ---------- evidence locks: what learners have used keeps its meaning ----------
def attempt(lesson, which="right"):
    ex = lesson["exercises"][0]
    with connect(main.DB_PATH) as conn:
        uid = adm.add_user(conn)
        answer = next(a for a in ex["answers"] if a["is_correct"] == (which == "right"))
        conn.execute("INSERT INTO exercise_attempts(user_id, exercise_id, answer_id, is_correct, attempted_at) VALUES (?, ?, ?, ?, '2026-01-01 00:00:00')", (uid, ex["id"], answer["id"], 1 if which == "right" else 0))
    return answer


def test_an_answer_a_learner_chose_keeps_its_correctness_and_only_allows_typo_fixes(admin):
    lesson = new_lesson(admin)
    chosen = attempt(lesson, "right")
    ex = lesson["exercises"][0]
    ids = [a["id"] for a in ex["answers"]]
    url = f"{L}/{lesson['id']}/exercises/{ex['id']}"
    def with_first(text, correct=True):
        return [{"id": ids[0], "text": text, "is_correct": correct}, {"id": ids[1], "text": "wrong one", "is_correct": not correct}, {"id": ids[2], "text": "wrong two", "is_correct": False}]
    r = admin.patch(url, {"revision": lesson["revision"], "answers": with_first("a different meaning")})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "answer_in_use"
    r = admin.patch(url, {"revision": lesson["revision"], "answers": with_first("right one", False)})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "answer_in_use"
    ok(admin.patch(url, {"revision": lesson["revision"], "answers": with_first("Right one!")}))          # case / punctuation: a typo-level change is allowed
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT answer_text, is_correct FROM exercise_answers WHERE id = ?", (chosen["id"],)).fetchone()[:] == ("Right one!", 1)


def test_an_unchosen_answer_stays_free_to_change_while_a_chosen_one_is_locked(admin):
    lesson = new_lesson(admin)
    attempt(lesson, "right")
    ex = lesson["exercises"][0]
    ids = [a["id"] for a in ex["answers"]]
    r = ok(admin.patch(f"{L}/{lesson['id']}/exercises/{ex['id']}", {"revision": lesson["revision"], "answers": [
        {"id": ids[0], "text": "right one", "is_correct": True}, {"id": ids[1], "text": "a completely new distractor", "is_correct": False}, {"id": ids[2], "text": "wrong two", "is_correct": False}]}))
    assert r["exercise"]["answers"][1]["text"] == "a completely new distractor"


def test_an_exercise_with_attempts_keeps_its_item_and_difficulty(admin):
    lesson = new_lesson(admin)
    attempt(lesson)
    ex = lesson["exercises"][0]
    other = item_ids(3)[2]
    url = f"{L}/{lesson['id']}/exercises/{ex['id']}"
    for patch in ({"item_id": other}, {"difficulty": 3}):
        r = admin.patch(url, {"revision": lesson["revision"], **patch})
        assert r.status_code == 409 and r.json()["detail"]["code"] == "exercise_in_use"
    r = ok(admin.patch(url, {"revision": lesson["revision"], "prompt": "A clearer prompt", "explanation": "More help", "item_id": ex["item_id"], "difficulty": ex["difficulty"]}))
    assert r["exercise"]["prompt"] == "A clearer prompt"                                                 # wording is free; repeating the current item / difficulty is not a change


def test_the_attempt_rows_are_never_touched_by_any_edit(admin):
    lesson = new_lesson(admin)
    attempt(lesson)
    with connect(main.DB_PATH) as conn:
        before = adm.table_dump(conn)["exercise_attempts"]
    ex = lesson["exercises"][0]
    ok(admin.patch(f"{L}/{lesson['id']}", {"revision": lesson["revision"], "title": "retitled", "topics": ["greetings"]}))
    with connect(main.DB_PATH) as conn:
        assert adm.table_dump(conn)["exercise_attempts"] == before and before


# ---------- vocabulary links ----------
def test_set_the_lessons_vocabulary_in_order(admin, audit_rows):
    lesson = new_lesson(admin, exercises=0)
    items = item_ids(3)
    r = ok(admin.put(f"{L}/{lesson['id']}/vocabulary", {"revision": lesson["revision"], "item_ids": [items[2], items[0], items[1]]}))
    assert [v["item_id"] for v in r["vocabulary"]] == [items[2], items[0], items[1]] and [v["sort_order"] for v in r["vocabulary"]] == [1, 2, 3] and r["revision"] == lesson["revision"] + 1
    last = audit_rows()[-1]
    assert (last["entity_type"], last["action"], last["entity_id"]) == ("lesson_vocabulary", "update", lesson["id"]) and '"changed_fields":["vocabulary"]' in last["meta_json"]
    again = ok(admin.put(f"{L}/{lesson['id']}/vocabulary", {"revision": r["revision"], "item_ids": [items[2], items[0], items[1]]}))
    assert again["revision"] == r["revision"]                                                              # same list: no edit
    r = ok(admin.put(f"{L}/{lesson['id']}/vocabulary", {"revision": r["revision"], "item_ids": []}))
    assert r["vocabulary"] == []


@pytest.mark.parametrize("ids_", [[99999], [1, 1], ["x"]])
def test_vocabulary_links_reject_unknown_or_duplicate_items(admin, ids_):
    lesson = new_lesson(admin)
    items = item_ids(1)
    payload = [items[0] if i == 1 else i for i in ids_]
    assert admin.put(f"{L}/{lesson['id']}/vocabulary", {"revision": lesson["revision"], "item_ids": payload}).status_code == 422


def test_vocabulary_links_must_match_the_lessons_language(admin):
    lesson = new_lesson(admin)
    with connect(main.DB_PATH) as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (2, 'A1') ON CONFLICT DO NOTHING")
        spanish = conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (2, 'A1', 'word', 'hola-y')").lastrowid
    r = admin.put(f"{L}/{lesson['id']}/vocabulary", {"revision": lesson["revision"], "item_ids": [spanish]})
    assert r.status_code == 422
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM lesson_vocabulary WHERE lesson_id = ?", (lesson["id"],)).fetchone()[0] == 1


# ---------- atomicity ----------
def test_a_failing_audit_write_rolls_the_edit_back(admin, monkeypatch):
    lesson = new_lesson(admin)
    def boom(*a, **k):
        raise audit.AuditError("audit store is down")
    monkeypatch.setattr(audit, "record", boom)
    with pytest.raises(audit.AuditError):
        admin.c.patch(f"{L}/{lesson['id']}", json={"revision": lesson["revision"], "title": "must not stick"}, headers=adm.CSRF)
    row = lesson_row(lesson["id"])
    assert row["title"] != "must not stick" and row["revision"] == lesson["revision"]


def test_a_failing_audit_write_rolls_a_creation_back(admin, monkeypatch):
    def boom(*a, **k):
        raise audit.AuditError("audit store is down")
    monkeypatch.setattr(audit, "record", boom)
    with pytest.raises(audit.AuditError):
        admin.c.post(L, json=body(slug="never-created"), headers=adm.CSRF)
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM lessons WHERE slug = 'never-created'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM lesson_topics WHERE lesson_id NOT IN (SELECT id FROM lessons)").fetchone()[0] == 0


def test_a_failing_audit_write_rolls_an_exercise_back(admin, monkeypatch):
    lesson = new_lesson(admin, exercises=0)
    def boom(*a, **k):
        raise audit.AuditError("audit store is down")
    monkeypatch.setattr(audit, "record", boom)
    with pytest.raises(audit.AuditError):
        admin.c.post(f"{L}/{lesson['id']}/exercises", json={"revision": lesson["revision"], **mc("p")}, headers=adm.CSRF)
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM exercises WHERE lesson_id = ?", (lesson["id"],)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM exercise_answers WHERE exercise_id NOT IN (SELECT id FROM exercises)").fetchone()[0] == 0
    assert lesson_row(lesson["id"])["revision"] == lesson["revision"]


# ---------- the CMS never publishes, deletes or reaches learners ----------
def test_a_new_draft_is_invisible_to_learners(admin, client2):
    lesson = new_lesson(admin)
    from .conftest import register
    me = register(client2, "learner@example.com")
    assert client2.put("/api/profile", json={"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "1990-01-01"}).status_code == 200
    listed = client2.get("/api/lessons").json()["lessons"]
    assert lesson["slug"] not in [l["slug"] for l in listed] and client2.get(f"/api/lessons/{lesson['id']}").status_code == 404


def test_the_content_routes_refuse_everyone_but_admins(client, admin):
    lesson = new_lesson(admin)
    for who in (Api(), register_browser("learner", "l@example.com"), register_browser("parent", "p@example.com"), adm.demo_browser()):
        assert who.get(L).status_code in (401, 403) and who.get(f"{L}/{lesson['id']}").status_code in (401, 403)
        assert who.post(L, body(slug="intruder")).status_code in (401, 403)
        assert who.patch(f"{L}/{lesson['id']}", {"revision": lesson["revision"], "title": "pwned"}).status_code in (401, 403)
    assert lesson_row(lesson["id"])["title"] == lesson["title"]


def test_there_is_no_way_to_delete_a_lesson_or_an_exercise(admin):
    lesson = new_lesson(admin)
    ex = lesson["exercises"][0]
    for url in (f"{L}/{lesson['id']}", f"{L}/{lesson['id']}/exercises/{ex['id']}", f"{L}/{lesson['id']}/vocabulary", L):
        assert admin.delete(url).status_code in (404, 405)
    assert lesson_row(lesson["id"])["id"] == lesson["id"]


# ---------- guards the mutation pass showed needed their own assertions ----------
def test_a_stale_bump_is_refused_by_the_guarded_update_itself(admin):
    """Two admins racing: the service's early revision check can pass for both, so the UPDATE that bumps the revision must itself refuse a stale one."""
    from backend.admin import cms
    from backend.admin.errors import Conflict
    from backend.repositories import admin_content as repo
    lesson = new_lesson(admin)
    with connect(main.DB_PATH) as conn:
        assert repo.bump(conn, "lesson", lesson["id"], lesson["revision"] + 5, "2026-01-01 00:00:00") is None
        assert one(conn, "SELECT revision FROM lessons WHERE id = ?", lesson["id"]) == lesson["revision"]
        assert repo.bump(conn, "lesson", lesson["id"], lesson["revision"], "2026-01-01 00:00:00") == lesson["revision"] + 1
        with pytest.raises(Conflict) as e:
            cms.save_edit(conn, "lesson", lesson["id"], lesson["revision"], "lesson")            # the revision moved under us
        assert e.value.code == "stale_revision"


def one(conn, sql, *a):
    return conn.execute(sql, a).fetchone()[0]


def test_update_conflicts_name_their_cause(admin):
    a, b = new_lesson(admin, "name-a"), new_lesson(admin, "name-b")
    r = admin.patch(f"{L}/{b['id']}", {"revision": b["revision"], "slug": "name-a"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "slug_taken"
    r = admin.patch(f"{L}/{b['id']}", {"revision": b["revision"], "sort_order": a["sort_order"]})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "sort_order_taken"


def test_answer_edits_name_their_cause(admin):
    lesson = new_lesson(admin)
    ex = lesson["exercises"][0]
    ids = [a["id"] for a in ex["answers"]]
    url = f"{L}/{lesson['id']}/exercises/{ex['id']}"
    texts = [a["text"] for a in ex["answers"]]
    unknown = admin.patch(url, {"revision": lesson["revision"], "answers": [{"id": ids[0], "text": texts[0], "is_correct": True}, {"id": ids[1], "text": texts[1], "is_correct": False},
                                                                             {"id": ids[2], "text": texts[2], "is_correct": False}, {"id": 987654, "text": "extra", "is_correct": False}]})
    assert unknown.status_code == 422 and "unknown answer id" in unknown.text
    twice = admin.patch(url, {"revision": lesson["revision"], "answers": [{"id": ids[0], "text": texts[0], "is_correct": True}, {"id": ids[0], "text": "again", "is_correct": False},
                                                                           {"id": ids[1], "text": texts[1], "is_correct": False}, {"id": ids[2], "text": texts[2], "is_correct": False}]})
    assert twice.status_code == 422 and "used twice" in twice.text


def test_an_answer_longer_than_the_service_allows_is_refused(admin):
    lesson = new_lesson(admin, exercises=0)
    long_text = "x" * 250
    r = admin.post(f"{L}/{lesson['id']}/exercises", {"revision": lesson["revision"], "kind": "multiple_choice", "prompt": "p", "answers": [{"text": long_text, "is_correct": True}, {"text": "b", "is_correct": False}]})
    assert r.status_code == 422 and "200 characters" in r.text


def test_a_refused_publish_logs_only_the_blocking_codes(admin, audit_rows):
    unit = new_lesson(admin, "warn-and-fail", title="Shared Title")
    other = new_lesson(admin, "warn-and-fail-2", title="shared title")
    with connect(main.DB_PATH) as conn:
        conn.execute("DELETE FROM exercises WHERE lesson_id = ?", (unit["id"],))
    r = admin.post(f"/api/admin/publish/lesson/{unit['id']}", {"revision": unit["revision"]})
    assert r.status_code == 422 and {f["code"] for f in r.json()["detail"]["findings"]} >= {"lesson_no_exercises", "lesson_duplicate_title"} and other
    ev = [e for e in audit_rows() if e["action"] == "validation_failed"][-1]
    assert '"finding_codes":["lesson_no_exercises"]' in ev["meta_json"] and "duplicate" not in ev["meta_json"]

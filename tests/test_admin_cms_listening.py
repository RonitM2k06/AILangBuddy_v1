"""Phase 13D: the listening CMS (activities and their options)."""
import pytest

from backend import main
from backend.admin import audit
from backend.db import connect

from . import adm
from .adm import Api, admin, audit_rows, item_ids, new_activity, ok, register_browser  # noqa: F401

A = "/api/admin/content/listening"


def row(aid):
    with connect(main.DB_PATH) as conn:
        return dict(conn.execute("SELECT * FROM listening_activities WHERE id = ?", (aid,)).fetchone())


def body(**over):
    return {"slug": "my-activity", "language": "hi", "cefr": "A1", "topic": "food", "item_id": item_ids(1)[0], "title": "My activity", "mode": "choose_meaning", "prompt": "Listen.", "difficulty": 2, **over}


def test_create_makes_a_draft_without_options_and_audits(admin, audit_rows):
    a = ok(admin.post(A, body(age_groups=["child", "teen"])), 201)
    assert (a["status"], a["revision"], a["mode"], a["difficulty"], a["options"], a["age_groups"], a["topic"]) == ("draft", 1, "choose_meaning", 2, [], ["child", "teen"], "food")
    assert a["target"]["item_id"] == item_ids(1)[0] and a["target"]["text"] and a["target"]["meaning_en"]
    ev = audit_rows()[-1]
    assert (ev["action"], ev["entity_type"], ev["entity_id"], ev["entity_key"], ev["meta_json"]) == ("create", "listening_activity", a["id"], "my-activity", '{"revision_after":1}')


@pytest.mark.parametrize("over", [{"slug": "Bad"}, {"language": "xx"}, {"cefr": "C2"}, {"topic": "nope"}, {"item_id": 99999}, {"title": " "}, {"prompt": "p\x00"}, {"difficulty": 0}, {"difficulty": 4},
                                  {"mode": "choose_both"}, {"age_groups": ["x"]}, {"age_groups": ["teen", "teen"]}])
def test_create_rejects_bad_input(admin, audit_rows, over):
    assert admin.post(A, body(**over)).status_code == 422
    assert audit_rows() == []


def test_the_target_item_must_be_in_the_activitys_language(admin):
    with connect(main.DB_PATH) as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (2, 'A1') ON CONFLICT DO NOTHING")
        spanish = conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (2, 'A1', 'word', 'hola-z')").lastrowid
    r = admin.post(A, body(item_id=spanish))
    assert r.status_code == 422 and "different language" in r.text


def test_create_conflicts_and_list_detail(admin):
    first = ok(admin.post(A, body(sort_order=70)), 201)
    assert admin.post(A, body(sort_order=71)).json()["detail"]["code"] == "slug_taken"
    assert admin.post(A, body(slug="other", sort_order=70)).json()["detail"]["code"] == "sort_order_taken"
    page = ok(admin.get(A))
    assert page["total"] == 316 and set(page["items"][0]) >= {"id", "slug", "status", "revision", "options"}     # Hindi 15 + the new one, Marathi 54 (0033, 0035), Kannada 50 (0037, 0038), Tamil 56 (0040-0045), French 18 (0044), Bengali 50 (0048, 0049)
    assert ok(admin.get(A + "?status=draft"))["total"] == 1 and ok(admin.get(A + "?status=published"))["total"] == 315 and ok(admin.get(A + "?q=my-act"))["total"] == 1
    assert ok(admin.get(A + "?language=hi"))["total"] == 16 and ok(admin.get(A + "?language=mr"))["total"] == 54
    assert ok(admin.get(A + "?language=es"))["total"] == 0 and ok(admin.get(A + "?limit=5&offset=315"))["items"].__len__() == 1
    d = ok(admin.get(f"{A}/{first['id']}"))
    assert d["slug"] == "my-activity" and admin.get(f"{A}/99999").status_code == 404 and admin.get(A + "?limit=101").status_code == 422


def test_a_seeded_activity_detail_marks_the_target_option(admin):
    with connect(main.DB_PATH) as conn:
        aid = conn.execute("SELECT id FROM listening_activities WHERE slug = 'food-meaning' AND language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0]
    d = ok(admin.get(f"{A}/{aid}"))
    assert d["status"] == "published" and len(d["options"]) == 3 and [o["is_target"] for o in d["options"]].count(True) == 1
    assert next(o for o in d["options"] if o["is_target"])["item_id"] == d["target"]["item_id"]


# ---------- options ----------
def test_options_are_added_up_to_exactly_three(admin, audit_rows):
    a = ok(admin.post(A, body()), 201)
    items = item_ids(4)
    rev = a["revision"]
    for n, it in enumerate(items[:3], 1):
        r = ok(admin.post(f"{A}/{a['id']}/options", {"revision": rev, "item_id": it}), 201)
        rev = r["revision"]
        assert (r["option"]["sort_order"], r["option"]["item_id"], r["option"]["is_target"]) == (n, it, it == a["target"]["item_id"])
    r = admin.post(f"{A}/{a['id']}/options", {"revision": rev, "item_id": items[3]})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "option_limit"
    ev = audit_rows()[-1]
    assert (ev["action"], ev["entity_type"], ev["entity_key"]) == ("create", "listening_option", "my-activity")


def test_option_input_rules(admin):
    a = new_activity(admin)
    fresh = ok(admin.post(A, body(slug="empty-one")), 201)
    items = item_ids(3)
    assert admin.post(f"{A}/{fresh['id']}/options", {"revision": fresh["revision"], "item_id": 99999}).status_code == 422
    r = ok(admin.post(f"{A}/{fresh['id']}/options", {"revision": fresh["revision"], "item_id": items[0], "sort_order": 3}), 201)
    dup = admin.post(f"{A}/{fresh['id']}/options", {"revision": r["revision"], "item_id": items[0]})
    assert dup.status_code == 422 and "already an option" in dup.text
    taken = admin.post(f"{A}/{fresh['id']}/options", {"revision": r["revision"], "item_id": items[1], "sort_order": 3})
    assert taken.status_code == 409 and taken.json()["detail"]["code"] == "sort_order_taken"
    assert admin.post(f"{A}/{a['id']}/options", {"revision": a["revision"], "item_id": items[0], "extra": 1}).status_code == 422


def test_update_an_option(admin, audit_rows):
    a = new_activity(admin)
    spare = next(i for i in range(1, 80) if i not in [o["item_id"] for o in a["options"]] and i in _english_items())
    opt = next(o for o in a["options"] if not o["is_target"])
    r = ok(admin.patch(f"{A}/{a['id']}/options/{opt['id']}", {"revision": a["revision"], "item_id": spare, "sort_order": 9}))
    assert (r["option"]["item_id"], r["option"]["sort_order"], r["revision"]) == (spare, 9, a["revision"] + 1)
    assert audit_rows()[-1]["meta_json"].count("changed_fields") == 1 and '["item","sort_order"]' in audit_rows()[-1]["meta_json"]
    n = len(audit_rows())
    cur = ok(admin.get(f"{A}/{a['id']}"))
    same = ok(admin.patch(f"{A}/{a['id']}/options/{opt['id']}", {"revision": cur["revision"], "item_id": spare}))
    assert same["revision"] == cur["revision"] and len(audit_rows()) == n


def _english_items():
    with connect(main.DB_PATH) as conn:
        return {r[0] for r in conn.execute("SELECT item_id FROM vocabulary_translations WHERE language_id = 1")}


def test_option_edit_rejections(admin):
    a = new_activity(admin)
    o1, o2, o3 = a["options"]
    url = f"{A}/{a['id']}/options"
    assert admin.patch(f"{url}/{o1['id']}", {"revision": a["revision"], "item_id": o2["item_id"]}).status_code == 422          # already an option
    assert admin.patch(f"{url}/{o1['id']}", {"revision": a["revision"], "item_id": 99999}).status_code == 422
    assert admin.patch(f"{url}/{o1['id']}", {"revision": a["revision"], "sort_order": o2["sort_order"]}).json()["detail"]["code"] == "sort_order_taken"
    assert admin.patch(f"{url}/{o1['id']}", {"revision": a["revision"], "sort_order": None}).status_code == 422
    assert admin.patch(f"{url}/99999", {"revision": a["revision"], "sort_order": 8}).status_code == 404
    other = new_activity(admin, "other-act")
    assert admin.patch(f"{A}/{a['id']}/options/{other['options'][0]['id']}", {"revision": a["revision"], "sort_order": 8}).status_code == 404


# ---------- updating the activity ----------
def test_update_edits_fields_and_audits_names_only(admin, audit_rows):
    a = new_activity(admin)
    r = ok(admin.patch(f"{A}/{a['id']}", {"revision": a["revision"], "title": "New", "prompt": "Listen again", "difficulty": 3, "topic": "greetings", "cefr": "A1", "mode": "choose_phrase", "age_groups": ["adult"]}))
    assert (r["title"], r["difficulty"], r["topic"], r["mode"], r["age_groups"], r["revision"]) == ("New", 3, "greetings", "choose_phrase", ["adult"], a["revision"] + 1)
    ev = audit_rows()[-1]
    assert '["age_groups","difficulty","mode","prompt","title","topic"]' in ev["meta_json"] and "Listen again" not in ev["meta_json"]


@pytest.mark.parametrize("patch", [{"slug": "BAD"}, {"cefr": "C2"}, {"topic": "nope"}, {"item_id": 99999}, {"title": None}, {"prompt": " "}, {"difficulty": 5}, {"mode": "x"},
                                   {"language": "es"}, {"status": "published"}, {"sort_order": 0}])
def test_update_rejects_bad_values(admin, patch):
    a = new_activity(admin)
    before = row(a["id"])
    assert admin.patch(f"{A}/{a['id']}", {"revision": a["revision"], **patch}).status_code == 422
    assert row(a["id"]) == before


def test_stale_and_noop(admin, audit_rows):
    a = new_activity(admin)
    ok(admin.patch(f"{A}/{a['id']}", {"revision": a["revision"], "title": "First"}))
    r = admin.patch(f"{A}/{a['id']}", {"revision": a["revision"], "title": "Second"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "stale_revision" and row(a["id"])["title"] == "First"
    cur = ok(admin.get(f"{A}/{a['id']}"))
    n = len(audit_rows())
    assert ok(admin.patch(f"{A}/{a['id']}", {"revision": cur["revision"], "title": "First", "age_groups": []}))["revision"] == cur["revision"] and len(audit_rows()) == n


@pytest.mark.parametrize("status", ["published", "archived"])
def test_only_a_draft_can_be_edited(admin, audit_rows, status):
    a = new_activity(admin)
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE listening_activities SET status = ?, published_at = CASE WHEN ? = 'published' THEN 't' END, archived_at = CASE WHEN ? = 'archived' THEN 't' END WHERE id = ?", (status, status, status, a["id"]))
        before = adm.table_dump(conn)
    n = len(audit_rows())
    for r in (admin.patch(f"{A}/{a['id']}", {"revision": a["revision"], "title": "x"}), admin.post(f"{A}/{a['id']}/options", {"revision": a["revision"], "item_id": item_ids(1)[0]}),
              admin.patch(f"{A}/{a['id']}/options/{a['options'][0]['id']}", {"revision": a["revision"], "sort_order": 9})):
        assert r.status_code == 409 and r.json()["detail"]["code"] == "not_draft"
    with connect(main.DB_PATH) as conn:
        assert adm.table_dump(conn) == before and len(audit_rows()) == n


# ---------- evidence ----------
def answered(a):
    with connect(main.DB_PATH) as conn:
        u = adm.add_user(conn)
        opt = next(o for o in a["options"] if not o["is_target"])
        adm.listening_attempt(conn, u, a["id"], opt["id"], correct=0)
    return opt


def test_an_activity_learners_answered_keeps_its_target_mode_and_difficulty(admin):
    a = new_activity(admin)
    answered(a)
    spare = next(i for i in sorted(_english_items()) if i != a["target"]["item_id"])
    for patch in ({"item_id": spare}, {"mode": "choose_phrase"}, {"difficulty": 3}):
        r = admin.patch(f"{A}/{a['id']}", {"revision": a["revision"], **patch})
        assert r.status_code == 409 and r.json()["detail"]["code"] == "activity_in_use"
    ok(admin.patch(f"{A}/{a['id']}", {"revision": a["revision"], "title": "Better title", "prompt": "Clearer prompt", "item_id": a["target"]["item_id"], "mode": a["mode"], "difficulty": a["difficulty"]}))


def test_an_option_a_learner_chose_keeps_its_phrase_and_so_does_the_correct_one(admin):
    a = new_activity(admin)
    chosen = answered(a)
    target = next(o for o in a["options"] if o["is_target"])
    free = next(o for o in a["options"] if not o["is_target"] and o["id"] != chosen["id"])
    spare = next(i for i in sorted(_english_items()) if i not in [o["item_id"] for o in a["options"]])
    url = f"{A}/{a['id']}/options"
    assert admin.patch(f"{url}/{chosen['id']}", {"revision": a["revision"], "item_id": spare}).json()["detail"]["code"] == "option_in_use"
    assert admin.patch(f"{url}/{target['id']}", {"revision": a["revision"], "item_id": spare}).json()["detail"]["code"] == "activity_in_use"
    r = ok(admin.patch(f"{url}/{free['id']}", {"revision": a["revision"], "item_id": spare, "sort_order": 7}))
    assert r["option"]["item_id"] == spare
    ok(admin.patch(f"{url}/{chosen['id']}", {"revision": r["revision"], "sort_order": 8}))               # its position may still change


def test_no_edit_touches_listening_attempts(admin):
    a = new_activity(admin)
    answered(a)
    with connect(main.DB_PATH) as conn:
        before = {t: adm.table_dump(conn)[t] for t in ("listening_attempts", "audio_sessions")}
    ok(admin.patch(f"{A}/{a['id']}", {"revision": a["revision"], "title": "Retitled", "topic": "greetings"}))
    with connect(main.DB_PATH) as conn:
        assert {t: adm.table_dump(conn)[t] for t in before} == before and all(before.values())


# ---------- atomicity, access, invisibility ----------
def test_failing_audit_rolls_everything_back(admin, monkeypatch):
    a = new_activity(admin)
    def boom(*x, **k):
        raise audit.AuditError("down")
    monkeypatch.setattr(audit, "record", boom)
    spare = next(i for i in sorted(_english_items()) if i not in [o["item_id"] for o in a["options"]])
    for call in (lambda: admin.c.post(A, json=body(slug="ghost"), headers=adm.CSRF), lambda: admin.c.patch(f"{A}/{a['id']}", json={"revision": a["revision"], "title": "no"}, headers=adm.CSRF),
                 lambda: admin.c.patch(f"{A}/{a['id']}/options/{a['options'][1]['id']}", json={"revision": a["revision"], "item_id": spare}, headers=adm.CSRF)):
        with pytest.raises(audit.AuditError):
            call()
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM listening_activities WHERE slug = 'ghost'").fetchone()[0] == 0
        assert [r[0] for r in conn.execute("SELECT item_id FROM listening_options WHERE activity_id = ? ORDER BY sort_order", (a["id"],))] == [o["item_id"] for o in a["options"]]
    assert row(a["id"])["revision"] == a["revision"]


def test_routes_refuse_non_admins_and_offer_no_delete(client, admin):
    a = new_activity(admin)
    for who in (Api(), register_browser("learner", "l@example.com"), register_browser("parent", "p@example.com"), adm.demo_browser()):
        assert who.get(A).status_code in (401, 403) and who.post(A, body(slug="x")).status_code in (401, 403)
        assert who.patch(f"{A}/{a['id']}", {"revision": 1, "title": "x"}).status_code in (401, 403)
    for url in (f"{A}/{a['id']}", f"{A}/{a['id']}/options/{a['options'][0]['id']}"):
        assert admin.delete(url).status_code in (404, 405)


def test_a_draft_activity_never_reaches_a_learner(admin, client2):
    a = new_activity(admin)
    from .conftest import register
    register(client2, "learner@example.com")
    client2.put("/api/profile", json={"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "1990-01-01"})
    assert a["slug"] not in [x["slug"] for x in client2.get("/api/listening").json()["activities"]]
    assert client2.get(f"/api/listening/{a['id']}").status_code == 404

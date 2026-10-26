"""Phase 13D: the situation CMS (situations and their steps). Same protocol as lessons; the step shapes are the situation-specific part."""
import pytest

from backend import main
from backend.admin import audit
from backend.db import connect

from . import adm
from .adm import Api, admin, audit_rows, item_ids, new_situation, ok, register_browser  # noqa: F401

S = "/api/admin/content/situations"


def row(sid):
    with connect(main.DB_PATH) as conn:
        return dict(conn.execute("SELECT * FROM situations WHERE id = ?", (sid,)).fetchone())


def body(**over):
    return {"slug": "my-situation", "language": "hi", "cefr": "A1", "topic": "food", "title": "My situation", "description": "A scene.", "difficulty": 2, **over}


def step_url(s, step):
    return f"{S}/{s['id']}/steps/{step['id']}"


# ---------- create / read ----------
def test_create_makes_a_draft_with_an_audit_event(admin, audit_rows):
    s = ok(admin.post(S, body(goal="Order", setting="Cafe", partner_name="Ravi", partner_role="waiter", age_groups=["adult"])), 201)
    assert (s["status"], s["revision"], s["topic"], s["difficulty"], s["partner_name"], s["partner_role"], s["steps"], s["age_groups"]) == ("draft", 1, "food", 2, "Ravi", "waiter", [], ["adult"])
    ev = audit_rows()[-1]
    assert (ev["action"], ev["entity_type"], ev["entity_id"], ev["entity_key"], ev["meta_json"]) == ("create", "situation", s["id"], "my-situation", '{"revision_after":1}')


@pytest.mark.parametrize("over", [
    {"slug": "Bad"}, {"language": "xx"}, {"cefr": "C2"}, {"topic": "nope"}, {"title": " "}, {"description": "bad\x00"}, {"difficulty": 0}, {"difficulty": 6}, {"goal": "g\x01"},
    {"partner_name": "Ravi"}, {"partner_role": "waiter"}, {"partner_name": "R\x00", "partner_role": "x"}, {"age_groups": ["nope"]}, {"age_groups": ["teen", "teen"]},
])
def test_create_rejects_bad_input(admin, audit_rows, over):
    assert admin.post(S, body(**over)).status_code == 422
    assert audit_rows() == []
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM situations WHERE slug = 'my-situation'").fetchone()[0] == 0


def test_create_conflicts(admin):
    ok(admin.post(S, body(slug="dup", sort_order=60)), 201)
    assert admin.post(S, body(slug="dup", sort_order=61)).json()["detail"]["code"] == "slug_taken"
    assert admin.post(S, body(slug="other", sort_order=60)).json()["detail"]["code"] == "sort_order_taken"


def test_list_detail_filters_and_pagination(admin):
    s = new_situation(admin)
    page = ok(admin.get(S))
    assert page["total"] == 112 and set(page["items"][0]) >= {"id", "slug", "title", "status", "revision", "steps"}    # Hindi 8 + the new one, Marathi 14 (0033, 0035), Kannada 14 (0037, 0038), Tamil 21 (0040-0045), French 8 (0044), Bengali 14 (0048, 0049)
    assert ok(admin.get(S + "?status=draft"))["items"][0]["steps"] == 2 and ok(admin.get(S + "?status=published"))["total"] == 111
    assert ok(admin.get(S + "?language=hi"))["total"] == 9 and ok(admin.get(S + "?language=mr"))["total"] == 14
    assert ok(admin.get(S + "?q=api-situ"))["total"] == 1 and ok(admin.get(S + "?language=es"))["total"] == 0 and ok(admin.get(S + "?cefr=A1&language=hi&limit=2&offset=1"))["items"].__len__() == 2
    d = ok(admin.get(f"{S}/{s['id']}"))
    assert [(st["kind"], len(st["answers"])) for st in d["steps"]] == [("learn_phrase", 0), ("choose_response", 2)]
    assert d["steps"][1]["answers"][0]["is_correct"] is True
    assert admin.get(f"{S}/99999").status_code == 404 and admin.get(S + "?limit=0").status_code == 422


# ---------- update ----------
def test_update_edits_fields_and_bumps_the_revision(admin, audit_rows):
    s = new_situation(admin)
    r = ok(admin.patch(f"{S}/{s['id']}", {"revision": s["revision"], "title": "New", "difficulty": 4, "topic": "greetings", "goal": "Goal", "age_groups": ["teen"]}))
    assert (r["title"], r["difficulty"], r["topic"], r["goal"], r["age_groups"], r["revision"]) == ("New", 4, "greetings", "Goal", ["teen"], s["revision"] + 1)
    ev = audit_rows()[-1]
    assert '"changed_fields":["age_groups","difficulty","goal","title","topic"]' in ev["meta_json"] and "Goal" not in ev["meta_json"]


def test_stale_published_and_noop_edits(admin, audit_rows):
    s = new_situation(admin)
    ok(admin.patch(f"{S}/{s['id']}", {"revision": s["revision"], "title": "A"}))
    r = admin.patch(f"{S}/{s['id']}", {"revision": s["revision"], "title": "B"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "stale_revision" and row(s["id"])["title"] == "A"
    n = len(audit_rows())
    cur = ok(admin.get(f"{S}/{s['id']}"))
    assert ok(admin.patch(f"{S}/{s['id']}", {"revision": cur["revision"], "title": "A", "topic": "food", "age_groups": []}))["revision"] == cur["revision"] and len(audit_rows()) == n


@pytest.mark.parametrize("patch", [{"partner_name": None}, {"partner_role": None}, {"title": None}, {"difficulty": 9}, {"topic": "nope"}, {"language": "es"}, {"status": "published"}, {"slug": "BAD"}])
def test_update_rejects_bad_values(admin, patch):
    s = new_situation(admin, partner_name="Ravi", partner_role="waiter")
    before = row(s["id"])
    assert admin.patch(f"{S}/{s['id']}", {"revision": s["revision"], **patch}).status_code == 422
    assert row(s["id"]) == before


def test_the_partner_can_be_cleared_together(admin):
    s = new_situation(admin, partner_name="Ravi", partner_role="waiter")
    r = ok(admin.patch(f"{S}/{s['id']}", {"revision": s["revision"], "partner_name": None, "partner_role": None}))
    assert (r["partner_name"], r["partner_role"]) == (None, None)


@pytest.mark.parametrize("status", ["published", "archived"])
def test_only_a_draft_can_be_edited(admin, audit_rows, status):
    s = new_situation(admin)
    step = s["steps"][1]
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE situations SET status = ?, published_at = CASE WHEN ? = 'published' THEN 't' END, archived_at = CASE WHEN ? = 'archived' THEN 't' END WHERE id = ?", (status, status, status, s["id"]))
        before = adm.table_dump(conn)
    n = len(audit_rows())
    calls = [admin.patch(f"{S}/{s['id']}", {"revision": s["revision"], "title": "x"}),
             admin.post(f"{S}/{s['id']}/steps", {"revision": s["revision"], "kind": "learn_phrase", "item_id": item_ids(1)[0]}),
             admin.patch(step_url(s, step), {"revision": s["revision"], "prompt": "x"})]
    for r in calls:
        assert r.status_code == 409 and r.json()["detail"]["code"] == "not_draft"
    with connect(main.DB_PATH) as conn:
        assert adm.table_dump(conn) == before and len(audit_rows()) == n


# ---------- steps ----------
def post_step(admin, s, **over):
    return admin.post(f"{S}/{s['id']}/steps", {"revision": s["revision"], **over})


def test_every_step_kind_can_be_created_with_its_own_answer_shape(admin, audit_rows):
    s = new_situation(admin)
    it = item_ids(1)[0]
    rev = s["revision"]
    made = {}
    for kind, extra in (("learn_phrase", {"item_id": it}),
                        ("choose_response", {"prompt": "Choose", "answers": [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": False}, {"text": "c", "is_correct": False}]}),
                        ("translate", {"prompt": "Translate", "answers": [{"text": "one"}, {"text": "uno"}]}),
                        ("fill_blank", {"prompt": "Fill ___", "answers": [{"text": "madad"}]}),
                        ("conversation", {"prompt": "Say hello", "prompt_meaning": "Greeting", "answers": [{"text": "hello"}, {"text": "namaste"}]})):
        r = ok(admin.post(f"{S}/{s['id']}/steps", {"revision": rev, "kind": kind, **extra}), 201)
        rev = r["revision"]
        made[kind] = r["step"]
    assert made["choose_response"]["answers"][0]["is_correct"] is True and [a["is_correct"] for a in made["translate"]["answers"]] == [True, True]
    assert made["learn_phrase"]["answers"] == [] and made["conversation"]["prompt_meaning"] == "Greeting"
    assert [st["sort_order"] for st in ok(admin.get(f"{S}/{s['id']}"))["steps"]] == [1, 2, 3, 4, 5, 6, 7]
    ev = audit_rows()[-1]
    assert (ev["action"], ev["entity_type"], ev["entity_key"]) == ("create", "situation_step", "api-situation") and "Say hello" not in ev["meta_json"]


@pytest.mark.parametrize("kind,extra", [
    ("learn_phrase", {}), ("learn_phrase", {"item_id": 99999}), ("learn_phrase", {"item_id": "IT", "answers": [{"text": "a"}]}),
    ("choose_response", {"prompt": "p", "answers": [{"text": "a", "is_correct": True}]}),
    ("choose_response", {"prompt": "p", "answers": [{"text": "a", "is_correct": False}, {"text": "b", "is_correct": False}]}),
    ("choose_response", {"prompt": "p", "answers": [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]}),
    ("choose_response", {"prompt": "p", "answers": [{"text": "Hi!", "is_correct": True}, {"text": "hi", "is_correct": False}]}),
    ("choose_response", {"prompt": " ", "answers": [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": False}]}),
    ("translate", {"prompt": "p", "answers": []}), ("translate", {"prompt": "p", "answers": [{"text": "a", "is_correct": False}]}),
    ("translate", {"answers": [{"text": "a"}]}), ("fill_blank", {"prompt": "p\x00", "answers": [{"text": "a"}]}),
    ("conversation", {"prompt": "p", "answers": [{"text": "a"}, {"text": "A."}]}),
])
def test_step_shapes_are_enforced_on_write(admin, audit_rows, kind, extra):
    s = new_situation(admin)
    it = item_ids(1)[0]
    extra = {k: (it if v == "IT" else v) for k, v in extra.items()}
    n, steps = len(audit_rows()), len(s["steps"])
    r = post_step(admin, s, kind=kind, **extra)
    assert r.status_code == 422, r.text
    assert len(audit_rows()) == n and len(ok(admin.get(f"{S}/{s['id']}"))["steps"]) == steps and ok(admin.get(f"{S}/{s['id']}"))["revision"] == s["revision"]


def test_step_position_conflict_and_unknown_kind(admin):
    s = new_situation(admin)
    r = post_step(admin, s, kind="learn_phrase", item_id=item_ids(1)[0], sort_order=1)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "sort_order_taken"
    assert post_step(admin, s, kind="monologue", prompt="p").status_code == 422


def test_update_a_step_and_its_answers(admin, audit_rows):
    s = new_situation(admin)
    step = s["steps"][1]
    ids = [a["id"] for a in step["answers"]]
    r = ok(admin.patch(step_url(s, step), {"revision": s["revision"], "prompt": "New prompt", "prompt_meaning": "Meaning", "explanation": "Why", "sort_order": 5,
                                           "answers": [{"id": ids[1], "text": "bad reply", "is_correct": False}, {"id": ids[0], "text": "good reply!", "is_correct": True}, {"text": "third", "is_correct": False}]}))
    st = r["step"]
    assert (st["prompt"], st["prompt_meaning"], st["explanation"], st["sort_order"], r["revision"]) == ("New prompt", "Meaning", "Why", 5, s["revision"] + 1)
    assert [(a["text"], a["is_correct"]) for a in st["answers"]] == [("bad reply", False), ("good reply!", True), ("third", False)] and [a["id"] for a in st["answers"]][:2] == [ids[1], ids[0]]
    ev = audit_rows()[-1]
    assert ev["entity_type"] == "situation_step" and '"changed_fields":["answers","explanation","prompt","prompt_meaning","sort_order"]' in ev["meta_json"]


def test_step_answers_cannot_be_removed_and_a_learn_phrase_keeps_its_item(admin):
    s = new_situation(admin)
    learn, choose = s["steps"]
    ids = [a["id"] for a in choose["answers"]]
    r = admin.patch(step_url(s, choose), {"revision": s["revision"], "answers": [{"id": ids[0], "text": "good reply", "is_correct": True}]})
    assert r.status_code == 422
    assert admin.patch(step_url(s, learn), {"revision": s["revision"], "item_id": None}).status_code == 422
    assert admin.patch(step_url(s, learn), {"revision": s["revision"], "answers": [{"text": "x"}]}).status_code == 422
    assert admin.patch(step_url(s, choose), {"revision": s["revision"], "kind": "translate"}).status_code == 422
    assert admin.patch(step_url(s, learn), {"revision": s["revision"], "sort_order": 2}).json()["detail"]["code"] == "sort_order_taken"


def test_a_step_of_another_situation_is_not_found(admin):
    a, b = new_situation(admin, "sit-a"), new_situation(admin, "sit-b")
    assert admin.patch(step_url(a, b["steps"][1]), {"revision": a["revision"], "prompt": "hijack"}).status_code == 404


def test_a_noop_step_edit_changes_nothing(admin, audit_rows):
    s = new_situation(admin)
    st = s["steps"][1]
    n = len(audit_rows())
    r = ok(admin.patch(step_url(s, st), {"revision": s["revision"], "prompt": st["prompt"], "answers": [{"id": a["id"], "text": a["text"], "is_correct": a["is_correct"]} for a in st["answers"]]}))
    assert r["revision"] == s["revision"] and len(audit_rows()) == n


# ---------- evidence ----------
def test_a_chosen_step_answer_and_a_used_step_keep_their_meaning(admin):
    s = new_situation(admin)
    learn, choose = s["steps"]
    right = next(a for a in choose["answers"] if a["is_correct"])
    with connect(main.DB_PATH) as conn:
        u = adm.add_user(conn)
        conn.execute("INSERT INTO situation_step_attempts(user_id, step_id, answer_id, is_correct, attempted_at) VALUES (?, ?, ?, 1, '2026-01-01 00:00:00')", (u, choose["id"], right["id"]))
    ids = [a["id"] for a in choose["answers"]]
    def answers(text, correct=True):
        return [{"id": ids[0], "text": text, "is_correct": correct}, {"id": ids[1], "text": "bad reply", "is_correct": not correct}]
    assert admin.patch(step_url(s, choose), {"revision": s["revision"], "answers": answers("another meaning")}).json()["detail"]["code"] == "answer_in_use"
    assert admin.patch(step_url(s, choose), {"revision": s["revision"], "answers": answers("good reply", False)}).json()["detail"]["code"] == "answer_in_use"
    ok(admin.patch(step_url(s, choose), {"revision": s["revision"], "answers": answers("Good reply.")}))
    other = item_ids(3)[2]
    cur = ok(admin.get(f"{S}/{s['id']}"))
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE situation_steps SET item_id = ? WHERE id = ?", (item_ids(1)[0], choose["id"]))
    r = admin.patch(step_url(s, choose), {"revision": cur["revision"], "item_id": other})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "step_in_use"
    ok(admin.patch(step_url(s, choose), {"revision": cur["revision"], "prompt": "A better prompt"}))


def test_no_edit_touches_attempts_or_roleplay_rows(admin):
    s = new_situation(admin)
    with connect(main.DB_PATH) as conn:
        u = adm.add_user(conn)
        conn.execute("INSERT INTO situation_step_attempts(user_id, step_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, 'x', 0, '2026-01-01 00:00:00')", (u, s["steps"][1]["id"]))
        rs = adm.roleplay_session(conn, u, s["id"])
        adm.roleplay_turn(conn, u, rs, s["id"], s["steps"][1]["id"])
        before = {t: adm.table_dump(conn)[t] for t in ("situation_step_attempts", "roleplay_sessions", "roleplay_turns")}
    ok(admin.patch(f"{S}/{s['id']}", {"revision": s["revision"], "title": "Retitled", "difficulty": 3}))
    with connect(main.DB_PATH) as conn:
        assert {t: adm.table_dump(conn)[t] for t in before} == before and all(before.values())


# ---------- atomicity, access, invisibility ----------
def test_failing_audit_rolls_situation_and_step_writes_back(admin, monkeypatch):
    s = new_situation(admin)
    def boom(*a, **k):
        raise audit.AuditError("down")
    monkeypatch.setattr(audit, "record", boom)
    for call in (lambda: admin.c.post(S, json=body(slug="ghost"), headers=adm.CSRF),
                 lambda: admin.c.patch(f"{S}/{s['id']}", json={"revision": s["revision"], "title": "no"}, headers=adm.CSRF),
                 lambda: admin.c.post(f"{S}/{s['id']}/steps", json={"revision": s["revision"], "kind": "learn_phrase", "item_id": item_ids(1)[0]}, headers=adm.CSRF)):
        with pytest.raises(audit.AuditError):
            call()
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM situations WHERE slug = 'ghost'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM situation_steps WHERE situation_id = ?", (s["id"],)).fetchone()[0] == 2
    assert row(s["id"])["revision"] == s["revision"] and row(s["id"])["title"] == s["title"]


def test_situation_routes_refuse_everyone_but_admins_and_have_no_delete(client, admin):
    s = new_situation(admin)
    for who in (Api(), register_browser("learner", "l@example.com"), register_browser("parent", "p@example.com"), adm.demo_browser()):
        assert who.get(S).status_code in (401, 403) and who.post(S, body(slug="x")).status_code in (401, 403)
        assert who.patch(f"{S}/{s['id']}", {"revision": 1, "title": "x"}).status_code in (401, 403)
    for url in (f"{S}/{s['id']}", f"{S}/{s['id']}/steps/{s['steps'][0]['id']}"):
        assert admin.delete(url).status_code in (404, 405)
    assert row(s["id"])["title"] == s["title"]


def test_a_draft_situation_never_reaches_a_learner(admin, client2):
    s = new_situation(admin)
    from .conftest import register
    register(client2, "learner@example.com")
    client2.put("/api/profile", json={"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "1990-01-01"})
    assert s["slug"] not in [x["slug"] for x in client2.get("/api/situations").json()["situations"]]
    assert client2.get(f"/api/situations/{s['id']}").status_code == 404

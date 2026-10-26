"""Phase 13E: the content lifecycle (publish / unpublish / archive / restore), what learners can see at each stage, and what never changes."""
import json

import pytest

from backend import main
from backend.admin import audit
from backend.db import connect

from . import adm
from .adm import (Api, admin, audit_rows, demo_browser, forbidden_keys, item_ids, learner_browser, learner_can_open, learner_slugs, make_activity, make_lesson,  # noqa: F401
                  make_situation, new_activity, new_lesson, new_situation, ok, register_browser)
from .agekids import dob_for_age
from .test_admin_validation_api import LESSON_CASES, break_lesson

KINDS = {"lesson": ("lessons", "lessons", new_lesson), "situation": ("situations", "situations", new_situation), "listening_activity": ("listening", "listening", new_activity)}
TABLE = {"lesson": "lessons", "situation": "situations", "listening_activity": "listening_activities"}


def row(etype, i):
    with connect(main.DB_PATH) as conn:
        return dict(conn.execute(f"SELECT * FROM {TABLE[etype]} WHERE id = ?", (i,)).fetchone())


def act(admin, action, etype, i, revision):
    return admin.post(f"/api/admin/{action}/{etype}/{i}", {"revision": revision})


def make(admin, etype, slug="cycle"):
    return KINDS[etype][2](admin, slug)


# ---------- publish ----------
@pytest.mark.parametrize("etype", KINDS)
def test_publish_makes_a_valid_draft_live_with_an_audit_event(admin, audit_rows, etype):
    unit = make(admin, etype)
    n = len(audit_rows())
    r = ok(act(admin, "publish", etype, unit["id"], unit["revision"]))
    assert (r["entity_type"], r["id"], r["status"], r["revision"], r["archived_at"]) == (etype, unit["id"], "published", unit["revision"] + 1, None) and r["published_at"] and r["warnings"] == []
    db = row(etype, unit["id"])
    assert (db["status"], db["revision"], db["published_at"], db["archived_at"]) == ("published", unit["revision"] + 1, r["published_at"], None)
    ev = audit_rows()[n:]
    assert len(ev) == 1 and (ev[0]["action"], ev[0]["entity_type"], ev[0]["entity_id"], ev[0]["entity_key"], ev[0]["outcome"]) == ("publish", etype, unit["id"], "cycle", "ok")
    assert json.loads(ev[0]["meta_json"]) == {"revision_before": unit["revision"], "revision_after": unit["revision"] + 1, "status_before": "draft", "status_after": "published"}


@pytest.mark.parametrize("etype", KINDS)
def test_a_published_unit_reaches_learners_and_a_draft_does_not(admin, client2, etype):
    path, _, _ = KINDS[etype]
    learner = learner_browser("l@example.com")
    unit = make(admin, etype)
    assert unit["slug"] not in learner_slugs(learner, path) and not learner_can_open(learner, path, unit["id"])
    ok(act(admin, "publish", etype, unit["id"], unit["revision"]))
    assert unit["slug"] in learner_slugs(learner, path) and learner_can_open(learner, path, unit["id"])


@pytest.mark.parametrize("etype", KINDS)
def test_publish_applies_the_validators_and_a_refusal_changes_nothing(admin, audit_rows, etype):
    unit = make(admin, etype)
    with connect(main.DB_PATH) as conn:
        if etype == "lesson":
            conn.execute("DELETE FROM exercises WHERE lesson_id = ?", (unit["id"],))
            codes = ["lesson_no_exercises"]
        elif etype == "situation":
            conn.execute("DELETE FROM situation_steps WHERE situation_id = ?", (unit["id"],))
            codes = ["situation_no_steps"]
        else:
            conn.execute("DELETE FROM listening_options WHERE id = (SELECT MAX(id) FROM listening_options WHERE activity_id = ?)", (unit["id"],))
            codes = ["listening_option_count"]
        before = adm.table_dump(conn)
    n = len(audit_rows())
    r = act(admin, "publish", etype, unit["id"], unit["revision"])
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "validation_failed" and sorted(f["code"] for f in detail["findings"] if f["severity"] == "error") == codes
    assert all(set(f) == {"code", "severity", "entity", "message"} for f in detail["findings"])
    with connect(main.DB_PATH) as conn:
        after = adm.table_dump(conn)
    changed = {t for t in after if after[t] != before[t]}
    assert changed == {"admin_audit_log"}                                                              # nothing but the audit trail moved
    ev = audit_rows()[n:]
    assert len(ev) == 1 and (ev[0]["action"], ev[0]["outcome"], ev[0]["entity_type"], ev[0]["entity_id"]) == ("validation_failed", "rejected", etype, unit["id"])
    assert json.loads(ev[0]["meta_json"]) == {"finding_codes": codes, "status_before": "draft", "revision_before": unit["revision"]}
    assert row(etype, unit["id"])["status"] == "draft"


@pytest.mark.parametrize("case", sorted(set(LESSON_CASES) - {"dup_title", "no_item"}))
def test_publish_agrees_with_the_dry_run_rule_by_rule(admin, case):
    with connect(main.DB_PATH) as conn:
        lid = make_lesson(conn, "agree")
    unit = ok(admin.get(f"/api/admin/content/lessons/{lid}"))
    with connect(main.DB_PATH) as conn:
        break_lesson(case, conn, lid)
    dry = ok(admin.post(f"/api/admin/validate/lesson/{lid}"))
    unit = ok(admin.get(f"/api/admin/content/lessons/{lid}"))
    r = act(admin, "publish", "lesson", lid, unit["revision"])
    assert dry["ok"] is False and r.status_code == 422
    blocking = [f for f in r.json()["detail"]["findings"] if f["severity"] == "error"]
    assert blocking == [f for f in dry["findings"] if f["severity"] == "error"]
    assert row("lesson", lid)["status"] == "draft"


def test_warnings_do_not_block_and_are_returned(admin):
    with connect(main.DB_PATH) as conn:
        lid = make_lesson(conn, "warned", title="Same Title")
        other = make_lesson(conn, "warned-2", title="same title")
    unit = ok(admin.get(f"/api/admin/content/lessons/{lid}"))
    assert ok(admin.post(f"/api/admin/validate/lesson/{lid}"))["ok"] is True
    r = ok(act(admin, "publish", "lesson", lid, unit["revision"]))
    assert r["status"] == "published" and [(w["code"], w["severity"]) for w in r["warnings"]] == [("lesson_duplicate_title", "warning")]
    assert row("lesson", other)["status"] == "draft"


def test_a_dry_run_that_passes_always_publishes(admin):
    for etype in KINDS:
        unit = make(admin, etype, f"agree-{etype[:3]}")
        assert ok(admin.post(f"/api/admin/validate/{etype}/{unit['id']}"))["ok"] is True
        assert ok(act(admin, "publish", etype, unit["id"], unit["revision"]))["status"] == "published"


def test_publishing_validates_the_stored_rows_not_the_request(admin):
    """There is nothing in the request to validate: the same revision publishes or not purely on what is stored, and a later fix flips the outcome."""
    unit = new_lesson(admin)
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE exercise_answers SET is_correct = 0 WHERE exercise_id = ?", (unit["exercises"][0]["id"],))
    assert act(admin, "publish", "lesson", unit["id"], unit["revision"]).status_code == 422
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE exercise_answers SET is_correct = 1 WHERE id = ?", (unit["exercises"][0]["answers"][0]["id"],))
    assert act(admin, "publish", "lesson", unit["id"], unit["revision"]).status_code == 200


def test_a_failed_audit_write_rolls_the_publish_back(admin, monkeypatch):
    unit = new_lesson(admin)
    def boom(*a, **k):
        raise audit.AuditError("down")
    monkeypatch.setattr(audit, "record", boom)
    with pytest.raises(audit.AuditError):
        admin.c.post(f"/api/admin/publish/lesson/{unit['id']}", json={"revision": unit["revision"]}, headers=adm.CSRF)
    db = row("lesson", unit["id"])
    assert (db["status"], db["published_at"], db["revision"]) == ("draft", None, unit["revision"])


def test_a_failed_audit_write_rolls_back_every_other_transition(admin, monkeypatch):
    unit = new_lesson(admin)
    ok(act(admin, "publish", "lesson", unit["id"], unit["revision"]))
    cur = row("lesson", unit["id"])
    monkeypatch.setattr(audit, "record", lambda *a, **k: (_ for _ in ()).throw(audit.AuditError("down")))
    for action in ("unpublish", "archive"):
        with pytest.raises(audit.AuditError):
            admin.c.post(f"/api/admin/{action}/lesson/{unit['id']}", json={"revision": cur["revision"]}, headers=adm.CSRF)
        assert row("lesson", unit["id"]) == cur


# ---------- the transition table ----------
ALLOWED = {("publish", "draft"): "published", ("unpublish", "published"): "draft", ("archive", "draft"): "archived", ("archive", "published"): "archived", ("restore", "archived"): "draft"}


def force_status(etype, i, status):
    with connect(main.DB_PATH) as conn:
        conn.execute(f"UPDATE {TABLE[etype]} SET status = ?, published_at = CASE WHEN ? = 'published' THEN '2026-01-01 00:00:00' END, archived_at = CASE WHEN ? = 'archived' THEN '2026-01-01 00:00:00' END WHERE id = ?",
                     (status, status, status, i))


@pytest.mark.parametrize("etype", KINDS)
@pytest.mark.parametrize("action", ["publish", "unpublish", "archive", "restore"])
@pytest.mark.parametrize("status", ["draft", "published", "archived"])
def test_the_transition_table(admin, audit_rows, etype, action, status):
    unit = make(admin, etype)
    force_status(etype, unit["id"], status)
    before_row = row(etype, unit["id"])
    n = len(audit_rows())
    r = act(admin, action, etype, unit["id"], before_row["revision"])
    if (action, status) in ALLOWED:
        assert r.status_code == 200, r.text
        assert r.json()["status"] == ALLOWED[(action, status)] and row(etype, unit["id"])["status"] == ALLOWED[(action, status)]
        assert [e["action"] for e in audit_rows()[n:]] == [action]
    else:
        assert r.status_code == 409 and r.json()["detail"]["code"] == "invalid_transition", r.text
        assert row(etype, unit["id"]) == before_row and len(audit_rows()) == n


def test_an_archived_unit_can_never_be_published_directly(admin, audit_rows):
    unit = new_lesson(admin)
    ok(act(admin, "archive", "lesson", unit["id"], unit["revision"]))
    cur = row("lesson", unit["id"])
    n = len(audit_rows())
    r = act(admin, "publish", "lesson", unit["id"], cur["revision"])
    assert r.status_code == 409 and r.json()["detail"]["code"] == "invalid_transition" and "Restore it to a draft first" in r.json()["detail"]["message"]
    assert row("lesson", unit["id"]) == cur and len(audit_rows()) == n


def test_published_and_archived_timestamps_follow_the_state(admin):
    unit = new_lesson(admin)
    rev = unit["revision"]
    pub = ok(act(admin, "publish", "lesson", unit["id"], rev))
    assert pub["published_at"] and pub["archived_at"] is None
    arch = ok(act(admin, "archive", "lesson", unit["id"], pub["revision"]))
    assert arch["published_at"] is None and arch["archived_at"] and row("lesson", unit["id"])["archived_at"] == arch["archived_at"]
    rest = ok(act(admin, "restore", "lesson", unit["id"], arch["revision"]))
    assert (rest["status"], rest["published_at"], rest["archived_at"]) == ("draft", None, None)
    again = ok(act(admin, "publish", "lesson", unit["id"], rest["revision"]))
    assert again["published_at"] and again["revision"] == rev + 4


def test_a_draft_can_be_archived_and_restored_without_ever_being_published(admin):
    unit = new_lesson(admin)
    arch = ok(act(admin, "archive", "lesson", unit["id"], unit["revision"]))
    assert arch["status"] == "archived" and row("lesson", unit["id"])["published_at"] is None
    assert ok(act(admin, "restore", "lesson", unit["id"], arch["revision"]))["status"] == "draft"


def test_a_restored_unit_is_validated_again_before_it_can_go_live(admin):
    unit = new_lesson(admin)
    ok(act(admin, "archive", "lesson", unit["id"], unit["revision"]))
    with connect(main.DB_PATH) as conn:
        conn.execute("DELETE FROM exercises WHERE lesson_id = ?", (unit["id"],))
    cur = row("lesson", unit["id"])
    rest = ok(act(admin, "restore", "lesson", unit["id"], cur["revision"]))
    assert act(admin, "publish", "lesson", unit["id"], rest["revision"]).status_code == 422


# ---------- revisions ----------
@pytest.mark.parametrize("action,status", sorted(ALLOWED))
def test_every_transition_needs_the_current_revision(admin, audit_rows, action, status):
    unit = new_lesson(admin)
    force_status("lesson", unit["id"], status)
    cur = row("lesson", unit["id"])
    n = len(audit_rows())
    for stale in (cur["revision"] - 1, cur["revision"] + 1):
        r = act(admin, action, "lesson", unit["id"], max(stale, 1) if stale != cur["revision"] else stale + 3)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "stale_revision" and r.json()["detail"]["current_revision"] == cur["revision"]
    assert row("lesson", unit["id"]) == cur and len(audit_rows()) == n


def test_the_same_revision_cannot_publish_twice_and_the_revision_is_required(admin):
    unit = new_lesson(admin)
    ok(act(admin, "publish", "lesson", unit["id"], unit["revision"]))
    r = act(admin, "archive", "lesson", unit["id"], unit["revision"])                                   # a page opened before the publish
    assert r.status_code == 409 and r.json()["detail"]["code"] == "stale_revision"
    assert admin.post(f"/api/admin/publish/lesson/{unit['id']}", {}).status_code == 422
    assert admin.post(f"/api/admin/publish/lesson/{unit['id']}", {"revision": 0}).status_code == 422
    assert admin.post(f"/api/admin/publish/lesson/{unit['id']}", {"revision": 1, "status": "published"}).status_code == 422


def test_every_state_change_bumps_the_revision_by_one(admin):
    unit = new_lesson(admin)
    rev = unit["revision"]
    for action in ("publish", "unpublish", "archive", "restore"):
        r = ok(act(admin, action, "lesson", unit["id"], rev))
        assert r["revision"] == rev + 1
        rev = r["revision"]


# ---------- editing around the lifecycle ----------
def test_a_published_lesson_is_edited_by_unpublishing_editing_and_publishing_again(admin, audit_rows):
    unit = new_lesson(admin)
    pub = ok(act(admin, "publish", "lesson", unit["id"], unit["revision"]))
    assert admin.patch(f"/api/admin/content/lessons/{unit['id']}", {"revision": pub["revision"], "title": "Edited"}).status_code == 409
    back = ok(act(admin, "unpublish", "lesson", unit["id"], pub["revision"]))
    edited = ok(admin.patch(f"/api/admin/content/lessons/{unit['id']}", {"revision": back["revision"], "title": "Edited"}))
    assert edited["title"] == "Edited" and edited["status"] == "draft"
    again = ok(act(admin, "publish", "lesson", unit["id"], edited["revision"]))
    assert again["status"] == "published" and row("lesson", unit["id"])["title"] == "Edited"
    trail = [e["action"] for e in audit_rows() if e["entity_type"] == "lesson" and e["entity_id"] == unit["id"]]
    assert trail == ["create", "publish", "unpublish", "update", "publish"]


def test_the_full_audit_trail_of_one_lesson_reads_in_order(admin, audit_rows):
    unit = new_lesson(admin, exercises=0)
    pub_blocked = act(admin, "publish", "lesson", unit["id"], unit["revision"])
    assert pub_blocked.status_code == 422
    trail = [(e["action"], e["outcome"]) for e in audit_rows() if e["entity_type"] in ("lesson", "lesson_vocabulary") and e["entity_id"] == unit["id"]]
    assert trail == [("create", "ok"), ("update", "ok"), ("validation_failed", "rejected")]


# ---------- what archiving does to learners ----------
def learner_with_history(admin, lesson):
    """A learner who has worked through `lesson` (progress, attempts, XP, a weakness, a completed plan task), written as plain evidence rows."""
    with connect(main.DB_PATH) as conn:
        learner = adm.add_user(conn)
        adm.add_profile(conn, learner)
        adm.lesson_progress(conn, learner, lesson["id"], completed="2026-01-15 11:00:00")
        att = adm.exercise_attempt(conn, learner, lesson["exercises"][0]["id"], correct=1)
        adm.xp(conn, learner, att)
        adm.weakness(conn, learner)
        adm.daily_task(conn, learner, lid=lesson["id"], status="done")
    return learner


EVIDENCE = ["lesson_progress", "exercise_attempts", "xp_events", "weaknesses", "daily_tasks", "learner_profiles", "users", "confidence_scores", "streak_days"]


@pytest.mark.parametrize("action,setup", [("archive", None), ("unpublish", None)])
def test_leaving_the_published_state_keeps_every_piece_of_learner_evidence(admin, action, setup):
    lesson = new_lesson(admin)
    pub = ok(act(admin, "publish", "lesson", lesson["id"], lesson["revision"]))
    learner_with_history(admin, lesson)
    with connect(main.DB_PATH) as conn:
        before = {t: adm.table_dump(conn)[t] for t in EVIDENCE}
        views_before = [tuple(r) for r in conn.execute("SELECT * FROM learner_attempts ORDER BY attempt_id")]
    ok(act(admin, action, "lesson", lesson["id"], pub["revision"]))
    with connect(main.DB_PATH) as conn:
        assert {t: adm.table_dump(conn)[t] for t in EVIDENCE} == before and before["lesson_progress"] and before["exercise_attempts"]
        assert [tuple(r) for r in conn.execute("SELECT * FROM learner_attempts ORDER BY attempt_id")] == views_before and views_before
        assert conn.execute("SELECT title FROM lessons WHERE id = ?", (lesson["id"],)).fetchone()[0] == lesson["title"]          # the row, and so every historical title, is still there


def test_archiving_hides_a_lesson_from_listings_detail_progress_and_new_attempts(admin):
    lesson = new_lesson(admin)
    pub = ok(act(admin, "publish", "lesson", lesson["id"], lesson["revision"]))
    me = learner_browser("l@example.com")
    assert lesson["slug"] in learner_slugs(me, "lessons") and learner_can_open(me, "lessons", lesson["id"])
    ex = lesson["exercises"][0]
    right = next(a for a in ex["answers"] if a["is_correct"])
    assert me.post(f"/api/exercises/{ex['id']}/attempts", {"answer_id": right["id"]}).status_code == 200
    assert lesson["id"] in [p["lesson_id"] for p in me.get("/api/progress/lessons").json()["progress"]]
    ok(act(admin, "archive", "lesson", lesson["id"], pub["revision"]))
    assert lesson["slug"] not in learner_slugs(me, "lessons") and not learner_can_open(me, "lessons", lesson["id"])
    assert lesson["id"] not in [p["lesson_id"] for p in me.get("/api/progress/lessons").json()["progress"]]
    assert me.post(f"/api/exercises/{ex['id']}/attempts", {"answer_id": right["id"]}).status_code == 404
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM exercise_attempts WHERE exercise_id = ?", (ex["id"],)).fetchone()[0] == 1       # the history is still stored
        assert conn.execute("SELECT started_at IS NOT NULL FROM lesson_progress WHERE lesson_id = ?", (lesson["id"],)).fetchone()[0] == 1


def test_archived_content_is_not_in_new_plans_or_recommendations(admin):
    """A published lesson at position 1 is the 'next lesson'; once archived, neither the recommendations nor a freshly generated plan name it."""
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE lessons SET sort_order = sort_order + 100 WHERE language_id = 10 AND cefr_code = 'A1'")
    lesson = new_lesson(admin, "first-up", sort_order=1)
    pub = ok(act(admin, "publish", "lesson", lesson["id"], lesson["revision"]))
    me = learner_browser("l@example.com")
    recs = me.get("/api/recommendations").json()["recommendations"]
    assert recs[0]["target"] == {"type": "lesson", "id": lesson["id"], "title": lesson["title"]}
    ok(act(admin, "archive", "lesson", lesson["id"], pub["revision"]))
    recs = me.get("/api/recommendations").json()["recommendations"]
    assert lesson["id"] not in [r["target"]["id"] for r in recs if r["target"]["type"] == "lesson"]
    plan = me.post("/api/daily-plan/generate").json()["plan"]
    assert plan["generated"] and plan["tasks"] and lesson["id"] not in [t["target"]["id"] for t in plan["tasks"] if t["target"]["type"] == "lesson"]
    ai = me.get("/api/ai/recommendations").json()
    assert lesson["id"] not in [r["target"]["id"] for r in ai.get("recommendations", []) if r["target"]["type"] == "lesson"]


def test_a_plan_made_before_the_archive_still_names_the_lesson_it_was_built_from(admin):
    """Documented: today's stored plan is a historical record. The title stays readable by id; opening it is refused (404), and tomorrow's plan omits it."""
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE lessons SET sort_order = sort_order + 100 WHERE language_id = 10 AND cefr_code = 'A1'")
    lesson = new_lesson(admin, "plan-first", sort_order=1)
    pub = ok(act(admin, "publish", "lesson", lesson["id"], lesson["revision"]))
    me = learner_browser("l@example.com")
    plan = me.post("/api/daily-plan/generate").json()["plan"]
    assert lesson["id"] in [t["target"]["id"] for t in plan["tasks"] if t["target"]["type"] == "lesson"]
    ok(act(admin, "archive", "lesson", lesson["id"], pub["revision"]))
    again = me.get("/api/daily-plan").json()["plan"]
    task = next(t for t in again["tasks"] if t["target"]["id"] == lesson["id"])
    assert task["target"]["title"] == lesson["title"] and not learner_can_open(me, "lessons", lesson["id"])


@pytest.mark.parametrize("etype", ["situation", "listening_activity"])
def test_archiving_hides_situations_and_listening_but_keeps_their_evidence(admin, etype):
    path, _, _ = KINDS[etype]
    unit = make(admin, etype)
    pub = ok(act(admin, "publish", etype, unit["id"], unit["revision"]))
    me = learner_browser("l@example.com")
    assert unit["slug"] in learner_slugs(me, path)
    with connect(main.DB_PATH) as conn:
        u = adm.add_user(conn)
        if etype == "situation":
            adm.situation_progress(conn, u, unit["id"])
            adm.step_attempt(conn, u, unit["steps"][1]["id"])
            adm.roleplay_session(conn, u, unit["id"])
            tables = ["situation_progress", "situation_step_attempts", "roleplay_sessions"]
        else:
            adm.listening_attempt(conn, u, unit["id"], unit["options"][1]["id"] if not unit["options"][1]["is_target"] else unit["options"][0]["id"])
            tables = ["listening_attempts", "audio_sessions"]
        before = {t: adm.table_dump(conn)[t] for t in tables}
    ok(act(admin, "archive", etype, unit["id"], pub["revision"]))
    assert unit["slug"] not in learner_slugs(me, path) and not learner_can_open(me, path, unit["id"])
    with connect(main.DB_PATH) as conn:
        assert {t: adm.table_dump(conn)[t] for t in tables} == before and all(before.values())


def test_archived_situations_cannot_be_acted_on_by_learners(admin):
    unit = new_situation(admin)
    pub = ok(act(admin, "publish", "situation", unit["id"], unit["revision"]))
    me = learner_browser("l@example.com")
    learn, step = unit["steps"]
    right = next(a for a in step["answers"] if a["is_correct"])
    assert me.post(f"/api/situations/{unit['id']}/steps/{learn['id']}/responses", {}).status_code == 200
    assert me.post(f"/api/situations/{unit['id']}/steps/{step['id']}/responses", {"answer_id": right["id"]}).status_code == 200
    ok(act(admin, "archive", "situation", unit["id"], pub["revision"]))
    assert me.post(f"/api/situations/{unit['id']}/steps/{step['id']}/responses", {"answer_id": right["id"]}).status_code in (404, 409)
    assert me.post("/api/roleplay/sessions", {"situation_id": unit["id"]}).status_code in (404, 409, 422)


def test_archived_listening_cannot_be_answered(admin):
    unit = new_activity(admin)
    pub = ok(act(admin, "publish", "listening_activity", unit["id"], unit["revision"]))
    me = learner_browser("l@example.com")
    opt = unit["options"][0]
    assert me.post(f"/api/listening/{unit['id']}/attempts", {"option_id": opt["id"]}).status_code == 200
    ok(act(admin, "archive", "listening_activity", unit["id"], pub["revision"]))
    assert me.post(f"/api/listening/{unit['id']}/attempts", {"option_id": opt["id"]}).status_code == 404


# ---------- what learners see is still filtered by level and age, and never carries the answer key ----------
def test_published_cms_content_still_respects_age_targeting(admin):
    teen_only = new_lesson(admin, "teen-lesson", age_groups=["teen"])
    ok(act(admin, "publish", "lesson", teen_only["id"], teen_only["revision"]))
    adult = learner_browser("adult@example.com", dob=dob_for_age(30))
    teen = learner_browser("teen@example.com", dob=dob_for_age(14))
    child = learner_browser("child@example.com", dob=dob_for_age(6))
    assert "teen-lesson" in learner_slugs(teen, "lessons") and learner_can_open(teen, "lessons", teen_only["id"])
    for other in (adult, child):
        assert "teen-lesson" not in learner_slugs(other, "lessons") and not learner_can_open(other, "lessons", teen_only["id"])


def test_untargeted_cms_content_is_visible_to_every_age_group(admin):
    universal = new_lesson(admin, "everyone")
    ok(act(admin, "publish", "lesson", universal["id"], universal["revision"]))
    for age in (6, 14, 30):
        assert "everyone" in learner_slugs(learner_browser(f"a{age}@example.com", dob=dob_for_age(age)), "lessons")


def test_published_cms_content_still_respects_the_learners_level(admin):
    a2 = new_lesson(admin, "level-two", cefr="A2")
    ok(act(admin, "publish", "lesson", a2["id"], a2["revision"]))
    a1_learner = learner_browser("a1@example.com", level="A1")
    a2_learner = learner_browser("a2@example.com", level="A2")
    assert "level-two" not in learner_slugs(a1_learner, "lessons") and not learner_can_open(a1_learner, "lessons", a2["id"])
    assert "level-two" in learner_slugs(a2_learner, "lessons") and learner_can_open(a2_learner, "lessons", a2["id"])


def test_published_cms_content_respects_the_learners_language(admin):
    other = new_lesson(admin, "hindi-only")
    ok(act(admin, "publish", "lesson", other["id"], other["revision"]))
    with connect(main.DB_PATH) as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (2, 'A1') ON CONFLICT DO NOTHING")
    spanish = learner_browser("es@example.com", target="es")
    assert "hindi-only" not in learner_slugs(spanish, "lessons") and not learner_can_open(spanish, "lessons", other["id"])


@pytest.mark.parametrize("etype", KINDS)
def test_learner_reads_of_cms_content_never_carry_the_answer_key(admin, etype):
    path, _, _ = KINDS[etype]
    unit = make(admin, etype)
    ok(act(admin, "publish", etype, unit["id"], unit["revision"]))
    me = learner_browser("l@example.com")
    listing = me.get(f"/api/{path}").json()
    detail = me.get(f"/api/{path}/{unit['id']}").json()
    assert forbidden_keys(listing) == [] and forbidden_keys(detail) == [], (forbidden_keys(listing), forbidden_keys(detail))
    text = json.dumps(detail)
    if etype == "lesson":
        assert "right one" in text and "wrong one" in text                                               # the options are shown...
        assert '"is_correct"' not in text                                                                 # ...with nothing saying which is right
    if etype == "situation":
        assert "good reply" in text and "bad reply" in text and '"is_correct"' not in text


def test_a_typed_exercise_answer_is_not_in_any_learner_read(admin):
    lesson = new_lesson(admin, exercises=0)
    r = ok(admin.post(f"/api/admin/content/lessons/{lesson['id']}/exercises", {"revision": lesson["revision"], "kind": "translation", "prompt": "Say hello", "item_id": item_ids(1)[0],
                                                                               "answers": [{"text": "SECRET-ACCEPTED-ANSWER"}]}), 201)
    ok(act(admin, "publish", "lesson", lesson["id"], r["revision"]))
    me = learner_browser("l@example.com")
    blob = json.dumps([me.get("/api/lessons").json(), me.get(f"/api/lessons/{lesson['id']}").json(), me.get("/api/recommendations").json(), me.get("/api/daily-plan").json()])
    assert "SECRET-ACCEPTED-ANSWER" not in blob


# ---------- the seeded curriculum round-trips ----------
def test_a_seeded_lesson_can_go_through_the_whole_lifecycle_and_back(admin):
    with connect(main.DB_PATH) as conn:
        lid = conn.execute("SELECT id FROM lessons WHERE slug = 'greetings' AND language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0]
        rev = conn.execute("SELECT revision FROM lessons WHERE id = ?", (lid,)).fetchone()[0]
    me = learner_browser("l@example.com")
    assert "greetings" in learner_slugs(me, "lessons")
    r = ok(act(admin, "unpublish", "lesson", lid, rev))
    assert "greetings" not in learner_slugs(me, "lessons")
    r = ok(act(admin, "archive", "lesson", lid, r["revision"]))
    r = ok(act(admin, "restore", "lesson", lid, r["revision"]))
    assert "greetings" not in learner_slugs(me, "lessons")
    r = ok(act(admin, "publish", "lesson", lid, r["revision"]))
    assert r["status"] == "published" and r["warnings"] == [] and "greetings" in learner_slugs(me, "lessons")


def test_transitions_on_one_unit_leave_every_other_unit_alone(admin):
    a, b = new_lesson(admin, "iso-a"), new_lesson(admin, "iso-b")
    with connect(main.DB_PATH) as conn:
        before = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM lessons WHERE id <> ?", (a["id"],))}
    ok(act(admin, "publish", "lesson", a["id"], a["revision"]))
    with connect(main.DB_PATH) as conn:
        assert {r["id"]: dict(r) for r in conn.execute("SELECT * FROM lessons WHERE id <> ?", (a["id"],))} == before
    assert row("lesson", b["id"])["status"] == "draft"


# ---------- errors and access ----------
def test_lifecycle_errors(admin):
    assert act(admin, "publish", "lesson", 99999, 1).status_code == 404
    assert act(admin, "archive", "situation", 99999, 1).status_code == 404
    assert act(admin, "restore", "listening_activity", 99999, 1).status_code == 404
    assert act(admin, "publish", "vocabulary", 1, 1).status_code == 422
    assert act(admin, "publish", "lessons", 1, 1).status_code == 422
    assert act(admin, "publish", "lesson", "abc", 1).status_code == 422
    assert admin.post("/api/admin/destroy/lesson/1", {"revision": 1}).status_code in (404, 405)
    assert admin.post("/api/admin/delete/lesson/1", {"revision": 1}).status_code in (404, 405)


def test_lifecycle_routes_refuse_non_admins_and_change_nothing(client, admin):
    unit = new_lesson(admin)
    before = row("lesson", unit["id"])
    for who in (Api(), register_browser("learner", "l@example.com"), register_browser("parent", "p@example.com"), demo_browser()):
        for action in ("publish", "unpublish", "archive", "restore"):
            assert act(who, action, "lesson", unit["id"], unit["revision"]).status_code in (401, 403)
    assert row("lesson", unit["id"]) == before


def test_a_refused_publish_logs_only_the_blocking_codes_not_the_warnings(admin, audit_rows):
    unit = new_lesson(admin, "warn-and-fail", title="Shared Title")
    new_lesson(admin, "warn-and-fail-2", title="shared title")
    with connect(main.DB_PATH) as conn:
        conn.execute("DELETE FROM exercises WHERE lesson_id = ?", (unit["id"],))
    r = act(admin, "publish", "lesson", unit["id"], unit["revision"])
    assert r.status_code == 422 and {f["code"] for f in r.json()["detail"]["findings"]} >= {"lesson_no_exercises", "lesson_duplicate_title"}
    ev = [e for e in audit_rows() if e["action"] == "validation_failed"][-1]
    assert json.loads(ev["meta_json"])["finding_codes"] == ["lesson_no_exercises"]

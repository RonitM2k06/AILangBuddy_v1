"""Phase 13B: the audit service and the audit read API. Behaviour is asserted from the database and the HTTP responses, never from a mock."""
import inspect
import re
import sqlite3

import pytest

from backend import main
from backend.admin import audit
from backend.admin.codes import FIELD_NAMES
from backend.auth.service import User
from backend.db import connect

from . import adm
from .adm import Api, admin, audit_rows, register_browser  # noqa: F401  (fixtures)

CANARIES = ["canary-answer-text-1", "canary@private.example", "canary-password-hash", "canary-session-token", "canary tutor message", "sk-canary-api-key"]


def actor(conn, handle="adm_test"):
    uid = adm.add_user(conn, "admin", handle)
    return User(uid, handle, "Admin", f"{handle}@example.com", frozenset({"admin"}))


# ---------- record() ----------
def test_record_stores_the_session_actor_the_entity_and_clean_meta(db_path):
    with connect(db_path) as conn:
        a = actor(conn)
        audit.record(conn, a, "publish", "lesson", 7, "food", {"revision_before": 3, "revision_after": 4, "status_before": "draft", "status_after": "published",
                                                                 "changed_fields": ["title", "description", "title"], "finding_codes": ["slug_invalid", "lesson_no_exercises"]}, request_id="req1")
        row = dict(conn.execute("SELECT * FROM admin_audit_log").fetchone())
    assert (row["actor_user_id"], row["actor_label"], row["action"], row["entity_type"], row["entity_id"], row["entity_key"], row["outcome"], row["request_id"]) == \
           (a.id, "adm_test", "publish", "lesson", 7, "food", "ok", "req1")
    assert row["meta_json"] == '{"changed_fields":["description","title"],"finding_codes":["lesson_no_exercises","slug_invalid"],"revision_after":4,"revision_before":3,"status_after":"published","status_before":"draft"}'


def test_the_actor_cannot_be_named_by_a_caller_supplied_value(db_path):
    sig = inspect.signature(audit.record)
    assert "actor" in sig.parameters and not any(n in sig.parameters for n in ("actor_id", "actor_label", "user_id", "handle", "body"))
    with connect(db_path) as conn:
        for forged in ({"id": 1, "handle": "admin"}, None, "admin", 1, type("X", (), {"id": None, "handle": "h"})()):
            with pytest.raises(audit.AuditError, match="authenticated user"):
                audit.record(conn, forged, "create", "lesson", 1)
        assert conn.execute("SELECT COUNT(*) FROM admin_audit_log").fetchone()[0] == 0


@pytest.mark.parametrize("key", ["answer_text", "answer", "email", "password", "password_hash", "token", "session", "message", "transcript", "text", "api_key", "title", "reason", "learner_id", "path"])
def test_meta_refuses_every_key_outside_the_allow_list(db_path, key):
    with connect(db_path) as conn:
        a = actor(conn)
        with pytest.raises(audit.AuditError, match="not allowed"):
            audit.record(conn, a, "update", "exercise", 1, meta={key: CANARIES[0]})
        assert conn.execute("SELECT COUNT(*) FROM admin_audit_log").fetchone()[0] == 0


@pytest.mark.parametrize("meta", [
    {"revision_before": -1}, {"revision_after": "4"}, {"revision_before": True}, {"revision_after": 1.5}, {"revision_before": None},
    {"changed_fields": "title"}, {"changed_fields": [CANARIES[0] + " with spaces"]}, {"changed_fields": ["Title"]}, {"changed_fields": ["x" * 65]}, {"changed_fields": [1]},
    {"changed_fields": sorted(FIELD_NAMES)[:1] * 51}, {"changed_fields": ["a,b"]}, {"changed_fields": ['"quoted"']},
    {"changed_fields": ["canary-answer-text-1"]}, {"changed_fields": ["not_a_cms_field"]},                       # looks like an identifier, is not a known field name
    {"finding_codes": ["Has Space"]}, {"finding_codes": "none"}, {"finding_codes": ["not_a_finding_code"]}, {"finding_codes": ["sk-canary-api-key"]},
    {"status_before": "deleted"}, {"status_after": "Published"}, {"status_after": 1},
])
def test_meta_values_are_strictly_typed(db_path, meta):
    with connect(db_path) as conn:
        a = actor(conn)
        with pytest.raises(audit.AuditError):
            audit.record(conn, a, "update", "lesson", 1, meta=meta)
        assert conn.execute("SELECT COUNT(*) FROM admin_audit_log").fetchone()[0] == 0


def test_changed_fields_carry_names_only_never_values(db_path):
    with connect(db_path) as conn:
        a = actor(conn)
        audit.record(conn, a, "update", "lesson", 1, meta={"changed_fields": ["title"]})
        meta = conn.execute("SELECT meta_json FROM admin_audit_log").fetchone()[0]
    assert meta == '{"changed_fields":["title"]}'


@pytest.mark.parametrize("args", [("delete", "lesson", "ok"), ("publish", "users", "ok"), ("publish", "lesson", "maybe"), ("destroy", "lesson", "ok"), ("publish", "password", "ok"), ("create", "", "ok")])
def test_unknown_actions_entities_and_outcomes_are_refused_before_the_database(db_path, args):
    action, entity, outcome = args
    with connect(db_path) as conn:
        a = actor(conn)
        with pytest.raises(audit.AuditError):
            audit.record(conn, a, action, entity, 1, outcome=outcome)


def test_the_python_whitelists_match_the_database_checks(db_path):
    with connect(db_path) as conn:
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'admin_audit_log'").fetchone()[0]
    def checked(column):
        return set(re.findall(r"'([a-z_]+)'", re.search(column + r"\s+TEXT\s+NOT NULL CHECK \(\w+ IN \(([^)]*)\)", sql).group(1)))
    assert checked("action") == set(audit.ACTIONS) and checked("entity_type") == set(audit.ENTITY_TYPES)
    assert "delete" not in audit.ACTIONS


# ---------- atomicity ----------
def test_a_failed_audit_insert_rolls_the_content_change_back(db_path):
    with pytest.raises(audit.AuditError):
        with connect(db_path) as conn:
            a = actor(conn)
            conn.execute("UPDATE lessons SET title = 'changed by the admin' WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code = 'hi')")
            audit.record(conn, a, "update", "lesson", 1, meta={"title": "not allowed"})
    with connect(db_path) as conn:
        assert conn.execute("SELECT title FROM lessons WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0] != "changed by the admin"
        assert conn.execute("SELECT COUNT(*) FROM admin_audit_log").fetchone()[0] == 0


def test_a_failure_after_the_audit_insert_rolls_the_event_back_too(db_path):
    with pytest.raises(RuntimeError):
        with connect(db_path) as conn:
            a = actor(conn)
            audit.record(conn, a, "update", "lesson", 1)
            raise RuntimeError("the change failed after the event was written")
    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM admin_audit_log").fetchone()[0] == 0


def test_a_successful_change_and_its_event_commit_together(db_path):
    with connect(db_path) as conn:
        a = actor(conn)
        conn.execute("UPDATE lessons SET title = 'new title' WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code = 'hi')")
        audit.record(conn, a, "update", "lesson", 1, meta={"changed_fields": ["title"]})
    with connect(db_path) as conn:
        assert conn.execute("SELECT title FROM lessons WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0] == "new title"
        assert conn.execute("SELECT COUNT(*) FROM admin_audit_log").fetchone()[0] == 1


def test_a_rejected_event_survives_the_rollback_of_the_change_it_describes(db_path):
    with connect(db_path) as conn:
        a = actor(conn)
    with pytest.raises(RuntimeError):
        with connect(db_path) as conn:
            conn.execute("UPDATE lessons SET title = 'never committed' WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code = 'hi')")
            raise RuntimeError("validation failed")
    audit.record_rejected(db_path, a, "validation_failed", "lesson", 1, "food", {"finding_codes": ["lesson_no_exercises"]}, request_id="r9")
    with connect(db_path) as conn:
        assert conn.execute("SELECT title FROM lessons WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0] != "never committed"
        row = dict(conn.execute("SELECT * FROM admin_audit_log").fetchone())
    assert (row["outcome"], row["action"], row["meta_json"], row["request_id"], row["actor_label"]) == ("rejected", "validation_failed", '{"finding_codes":["lesson_no_exercises"]}', "r9", "adm_test")


def test_canary_values_never_reach_the_log(db_path):
    with connect(db_path) as conn:
        a = actor(conn)
    for canary in CANARIES:
        for meta in ({"answer_text": canary}, {"changed_fields": [canary]}, {"finding_codes": [canary]}, {"status_after": canary}, {"revision_after": canary}):
            with pytest.raises(audit.AuditError):
                with connect(db_path) as conn:
                    audit.record(conn, a, "update", "exercise", 1, meta=meta)
    with connect(db_path) as conn:
        dump = " ".join(str(tuple(r)) for r in conn.execute("SELECT * FROM admin_audit_log"))
    assert dump == "" and not any(c in dump for c in CANARIES)


# ---------- list / get ----------
def _stamp(db_path):
    """Give the seeded events distinct times without touching the immutable table: events are re-inserted with explicit timestamps."""
    with connect(db_path) as conn:
        a, b = actor(conn, "adm_a"), actor(conn, "adm_b")
        for who, action, entity, eid, outcome, at in [(a, "create", "lesson", 1, "ok", "2026-02-01 08:00:00"), (a, "publish", "lesson", 1, "ok", "2026-02-02 08:00:00"),
                                                      (b, "validation_failed", "situation", 2, "rejected", "2026-02-03 08:00:00"), (b, "update", "topic", 3, "ok", "2026-02-04 08:00:00"),
                                                      (a, "archive", "listening_activity", 4, "ok", "2026-02-05 23:59:59")]:
            conn.execute("INSERT INTO admin_audit_log(occurred_at, actor_user_id, actor_label, action, entity_type, entity_id, entity_key, outcome) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (at, who.id, who.handle, action, entity, eid, f"k{eid}", outcome))


def test_list_events_filters_orders_and_paginates(db_path):
    _stamp(db_path)
    total, items = audit.list_events(db_path, {}, 25, 0)
    assert total == 5 and [e["entity_id"] for e in items] == [4, 3, 2, 1, 1]                       # newest first
    assert [e["entity_id"] for e in audit.list_events(db_path, {}, 2, 1)[1]] == [3, 2]
    assert audit.list_events(db_path, {}, 2, 10) == (5, [])
    cases = [({"actor": "adm_a"}, 3), ({"actor": "adm_b"}, 2), ({"entity_type": "lesson"}, 2), ({"entity_id": 1}, 2), ({"action": "publish"}, 1),
             ({"outcome": "rejected"}, 1), ({"from": "2026-02-03"}, 3), ({"to": "2026-02-03"}, 2), ({"from": "2026-02-02", "to": "2026-02-05"}, 3),
             ({"from": "2026-02-05 23:59:59"}, 1), ({"to": "2026-02-05 23:59:59"}, 4), ({"actor": "nobody"}, 0),
             ({"actor": "adm_a", "action": "archive", "outcome": "ok", "entity_type": "listening_activity", "entity_id": 4}, 1)]
    for filters, expected in cases:
        total, items = audit.list_events(db_path, filters, 100, 0)
        assert total == expected == len(items), filters


def test_get_event_returns_the_event_without_internal_columns(db_path):
    _stamp(db_path)
    event = audit.get_event(db_path, 1)
    assert set(event) == {"id", "occurred_at", "actor", "action", "entity_type", "entity_id", "entity_key", "outcome", "meta", "request_id"}
    assert event["actor"] == "adm_a" and audit.get_event(db_path, 999) is None


def test_reading_the_log_writes_nothing(db_path):
    _stamp(db_path)
    with connect(db_path) as conn:
        before = [tuple(r) for r in conn.execute("SELECT * FROM admin_audit_log")]
    audit.list_events(db_path, {}, 25, 0)
    audit.get_event(db_path, 1)
    with connect(db_path) as conn:
        assert [tuple(r) for r in conn.execute("SELECT * FROM admin_audit_log")] == before


# ---------- the audit API ----------
def seed_via_service(admin_api):
    with connect(main.DB_PATH) as conn:
        who = conn.execute("SELECT id, handle FROM users WHERE handle <> 'demo-alex' ORDER BY id LIMIT 1").fetchone()
        a = User(who[0], who[1], "Admin", None, frozenset({"admin"}))
        for i, (action, entity, outcome) in enumerate([("create", "lesson", "ok"), ("publish", "lesson", "ok"), ("validation_failed", "situation", "rejected")], 1):
            audit.record(conn, a, action, entity, i, f"k{i}", {"revision_after": i}, outcome, request_id=f"r{i}")


def test_audit_list_api_shape_filters_and_pagination(admin):
    seed_via_service(admin)
    r = admin.get("/api/admin/audit")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert set(body) == {"items", "total", "limit", "offset"} and (body["total"], body["limit"], body["offset"]) == (3, 25, 0)
    assert set(body["items"][0]) == {"id", "occurred_at", "actor", "action", "entity_type", "entity_id", "entity_key", "outcome", "meta", "request_id"}
    assert set(body["items"][0]["meta"]) == {"revision_before", "revision_after", "changed_fields", "finding_codes", "status_before", "status_after"}
    assert [e["entity_id"] for e in body["items"]] == [3, 2, 1]
    assert admin.get("/api/admin/audit?action=publish").json()["total"] == 1
    assert admin.get("/api/admin/audit?outcome=rejected").json()["items"][0]["entity_type"] == "situation"
    assert admin.get("/api/admin/audit?entity_type=lesson&entity_id=2").json()["total"] == 1
    assert admin.get("/api/admin/audit?limit=2&offset=1").json()["items"][0]["entity_id"] == 2
    assert admin.get("/api/admin/audit?from=2999-01-01").json()["total"] == 0


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "limit=x", "offset=-1", "action=delete", "entity_type=users", "outcome=maybe", "entity_id=0", "from=yesterday", "to=2026-13-1", "actor=" + "a" * 65])
def test_audit_list_api_rejects_bad_parameters(admin, query):
    assert admin.get("/api/admin/audit?" + query).status_code == 422


def test_audit_api_returns_one_event_or_404(admin):
    seed_via_service(admin)
    r = admin.get("/api/admin/audit/2")
    assert r.status_code == 200 and r.json()["action"] == "publish" and r.json()["request_id"] == "r2" and r.json()["meta"]["revision_after"] == 2
    assert admin.get("/api/admin/audit/999").status_code == 404
    assert admin.get("/api/admin/audit/abc").status_code == 422


def test_the_audit_api_is_read_only_and_reading_does_not_log(admin, audit_rows):
    seed_via_service(admin)
    before = audit_rows()
    admin.get("/api/admin/audit")
    admin.get("/api/admin/audit/1")
    for method in ("post", "put", "patch", "delete"):
        for url in ("/api/admin/audit", "/api/admin/audit/1"):
            assert getattr(admin, method)(url).status_code in (404, 405), (method, url)
    assert audit_rows() == before


def test_no_audit_response_exposes_an_account_id_or_raw_json(admin):
    seed_via_service(admin)
    text = admin.get("/api/admin/audit").text
    assert "actor_user_id" not in text and "meta_json" not in text and "password" not in text and "@" not in text


def test_non_admins_cannot_read_the_audit_log(client, admin):
    seed_via_service(admin)
    learner = register_browser("learner", "l@example.com")
    parent = register_browser("parent", "p@example.com")
    for who in (learner, parent, adm.demo_browser(), Api()):
        assert who.get("/api/admin/audit").status_code in (401, 403)
        assert who.get("/api/admin/audit/1").status_code in (401, 403)
    assert Api().get("/api/admin/audit").status_code == 401
    assert learner.get("/api/admin/audit").status_code == 403 and parent.get("/api/admin/audit").status_code == 403

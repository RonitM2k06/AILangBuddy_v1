"""The parent portal: linking rules, authentication and authorization, cross-child isolation, what a parent can see, and the
controls (including that nothing can switch child voice on)."""
import json
import sqlite3
from datetime import datetime, timedelta

import pytest

from backend import main, settings
from backend.auth import service as auth_service
from backend.db import connect
from backend.parent import service as parent_service
from backend.personalization import clock

from .agekids import answer_key, freeze_clock, play
from .conftest import PASSWORD, register, plant_mfa_session
from .lis import activities, answer, wrong_options
from .par import PARENT_GETS, all_keys, browser, code_for, db, link, make_child, make_parent, uid


@pytest.fixture(autouse=True)
def _throttle():
    parent_service.reset_throttle()
    yield
    parent_service.reset_throttle()


@pytest.fixture
def family(client):
    """A parent (client2-style browser) linked to a teen child (client)."""
    child = make_child(client, "teen@example.com", 14)
    parent = browser()
    make_parent(parent, "parent@example.com")
    return parent, child, link(parent, child)


# ---------- authentication and roles ----------
def endpoints(i=1):
    return ([("get", "/api/parent/children", None), ("post", "/api/parent/children", {"code": "ABCDEFGHJK"}), ("delete", f"/api/parent/children/{i}", None),
             ("put", f"/api/parent/children/{i}/controls", {"voice_disabled": True})] + [("get", f"/api/parent/children/{i}/{p}", None) for p in PARENT_GETS])


def call(c, method, path, body=None):
    return getattr(c, method)(path, **({"json": body} if body is not None else {}))


@pytest.mark.parametrize("method,path,body", endpoints())
def test_unauthenticated_requests_are_rejected(client, lockdown, method, path, body):
    assert call(client, method, path, body).status_code == 401


def test_link_code_endpoint_needs_login(client, lockdown):
    assert client.post("/api/profile/parent-link-code").status_code == 401


@pytest.mark.parametrize("method,path,body", endpoints())
def test_a_learner_cannot_use_parent_endpoints(client, family, method, path, body):
    assert call(client, method, path, body).status_code == 403


@pytest.mark.parametrize("method,path,body", endpoints())
def test_admin_has_no_parent_access(client, client2, make_admin, method, path, body):
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert call(client2, method, path, body).status_code == 403


def test_parent_cannot_make_link_codes_and_admin_cannot_either(client, client2, make_admin):
    make_parent(client, "p@example.com")
    assert client.post("/api/profile/parent-link-code").status_code == 403
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert client2.post("/api/profile/parent-link-code").status_code == 403


def test_a_parent_cannot_use_learner_endpoints(client):
    make_parent(client, "p@example.com")
    for path in ("/api/profile", "/api/lessons", "/api/kids/adventure", "/api/experience"):
        assert client.get(path).status_code == 403


def test_existing_rbac_is_unchanged(client, client2, make_admin):
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert client2.get("/api/admin/users").json()["detail"]["code"] == "mfa_required"     # Phase 14D: admins need a second factor
    plant_mfa_session(client2, "admin@example.com")
    assert client2.get("/api/admin/users").status_code == 200
    make_parent(client, "p@example.com")
    assert client.get("/api/admin/users").status_code == 403


# ---------- linking ----------
def test_link_with_a_code_made_by_the_child(client):
    make_child(client, "k@example.com", 7)
    parent = browser()
    make_parent(parent)
    r = parent.post("/api/parent/children", json={"code": code_for(client)})
    assert r.status_code == 201
    child = r.json()["child"]
    assert set(child) == {"id", "display_name", "linked_at", "has_profile", "age_group", "target_language", "cefr_level"}
    assert child["age_group"]["code"] == "child" and child["target_language"] == "hi" and child["cefr_level"] == "A1"
    assert parent.get("/api/parent/children").json()["children"] == [child]


def test_no_private_data_in_any_parent_response(client, family):
    parent, _, i = family
    blob = json.dumps([parent.get("/api/parent/children").json()] + [parent.get(f"/api/parent/children/{i}/{p}").json() for p in PARENT_GETS])
    for needle in ("teen@example.com", "parent@example.com", "date_of_birth", "password", "handle", "u_"):
        assert needle not in blob
    assert not ({"email", "date_of_birth", "handle", "password_hash", "user_id", "learner_id", "token", "transcript", "audio_ref"} & all_keys(json.loads(blob)))


def test_code_works_once(client, client2):
    make_child(client, "k@example.com", 14)
    p1, p2 = browser(), browser()
    make_parent(p1, "p1@example.com"); make_parent(p2, "p2@example.com")
    code = code_for(client)
    assert p1.post("/api/parent/children", json={"code": code}).status_code == 201
    assert p2.post("/api/parent/children", json={"code": code}).status_code == 404
    assert p2.get("/api/parent/children").json()["children"] == []


def test_code_is_case_and_spacing_insensitive(client):
    make_child(client, "k@example.com", 14)
    parent = browser(); make_parent(parent)
    code = code_for(client)
    spaced = code[:5].lower() + " - " + code[5:].lower()
    assert parent.post("/api/parent/children", json={"code": spaced}).status_code == 201


def test_code_expires(client, monkeypatch):
    tick = freeze_clock(monkeypatch)
    make_child(client, "k@example.com", 14)
    parent = browser(); make_parent(parent)
    code = code_for(client)
    tick(settings.PARENT_CODE_TTL_SECONDS + 1)
    assert parent.post("/api/parent/children", json={"code": code}).status_code == 404
    code2 = code_for(client)
    tick(settings.PARENT_CODE_TTL_SECONDS - 5)
    assert parent.post("/api/parent/children", json={"code": code2}).status_code == 201


def test_a_new_code_replaces_the_old_one(client):
    make_child(client, "k@example.com", 14)
    parent = browser(); make_parent(parent)
    old, new = code_for(client), code_for(client)
    assert old != new
    assert parent.post("/api/parent/children", json={"code": old}).status_code == 404
    assert parent.post("/api/parent/children", json={"code": new}).status_code == 201


def test_making_a_code_does_not_cancel_another_childs_code(client, client2):
    make_child(client, "a@example.com", 14); make_child(client2, "b@example.com", 14)
    parent = browser(); make_parent(parent)
    a_code = code_for(client)
    code_for(client2)
    assert parent.post("/api/parent/children", json={"code": a_code}).status_code == 201


def test_codes_are_stored_hashed_and_random(client):
    make_child(client, "k@example.com", 14)
    codes = {code_for(client) for _ in range(5)}
    assert len(codes) == 5 and all(len(c) == settings.PARENT_CODE_LENGTH for c in codes)
    with db() as conn:
        stored = [r[0] for r in conn.execute("SELECT code_hash FROM parent_link_codes")]
    assert stored and not (set(stored) & codes) and all(len(h) == 64 for h in stored)


def test_wrong_codes_are_throttled_per_parent(client):
    make_child(client, "k@example.com", 14)
    parent, other = browser(), browser()
    make_parent(parent, "p@example.com"); make_parent(other, "o@example.com")
    for _ in range(settings.PARENT_CODE_MAX_FAILURES):
        assert parent.post("/api/parent/children", json={"code": "WRONGCODE1"}).status_code == 404
    blocked = parent.post("/api/parent/children", json={"code": code_for(client)})      # even the right code is held back
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) > 0
    assert other.post("/api/parent/children", json={"code": code_for(client)}).status_code == 201


def test_throttle_window_passes(client, monkeypatch):
    tick = freeze_clock(monkeypatch)
    make_child(client, "k@example.com", 14)
    parent = browser(); make_parent(parent)
    for _ in range(settings.PARENT_CODE_MAX_FAILURES):
        parent.post("/api/parent/children", json={"code": "WRONGCODE1"})
    tick(settings.PARENT_CODE_WINDOW_SECONDS + 1)
    assert parent.post("/api/parent/children", json={"code": code_for(client)}).status_code == 201


def test_duplicate_link_is_refused_and_keeps_the_code(client):
    make_child(client, "k@example.com", 14)
    p1, p2 = browser(), browser()
    make_parent(p1, "p1@example.com"); make_parent(p2, "p2@example.com")
    link(p1, client)
    code = code_for(client)
    assert p1.post("/api/parent/children", json={"code": code}).status_code == 409
    assert p2.post("/api/parent/children", json={"code": code}).status_code == 201       # the refused attempt did not burn the code
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM parent_links").fetchone()[0] == 2


def test_a_parent_can_follow_several_children_and_a_child_several_parents(client, client2):
    make_child(client, "a@example.com", 8); make_child(client2, "b@example.com", 15)
    p1, p2 = browser(), browser()
    make_parent(p1, "p1@example.com"); make_parent(p2, "p2@example.com")
    link(p1, client); link(p1, client2); link(p2, client)
    assert len(p1.get("/api/parent/children").json()["children"]) == 2
    assert len(p2.get("/api/parent/children").json()["children"]) == 1


def test_limits_on_children_and_parents(client, client2, monkeypatch):
    monkeypatch.setattr(settings, "MAX_CHILDREN_PER_PARENT", 1)
    monkeypatch.setattr(settings, "MAX_PARENTS_PER_CHILD", 1)
    make_child(client, "a@example.com", 8); make_child(client2, "b@example.com", 15)
    p1, p2 = browser(), browser()
    make_parent(p1, "p1@example.com"); make_parent(p2, "p2@example.com")
    link(p1, client)
    assert p1.post("/api/parent/children", json={"code": code_for(client2)}).status_code == 409      # too many children
    assert p2.post("/api/parent/children", json={"code": code_for(client)}).status_code == 409       # too many parents


def test_a_user_cannot_link_to_themselves(client):
    user, _ = auth_service.create_user(main.DB_PATH, email="both@example.com", password=PASSWORD, display_name="B", roles=["learner", "parent"])
    code = parent_service.issue_code(main.DB_PATH, user.id)["code"]
    with pytest.raises(parent_service.InvalidCode):
        parent_service.link_with_code(main.DB_PATH, user.id, code)


@pytest.mark.parametrize("body", [{}, {"code": ""}, {"code": "abc"}, {"code": "x" * 41}, {"code": 123}, {"code": "ABCDEFGHJK", "learner_id": 1}, {"code": "ABCDEFGHJK", "parent_id": 1}])
def test_link_body_is_validated(client, body):
    p = browser(); make_parent(p)
    assert p.post("/api/parent/children", json=body).status_code == 422


def test_no_way_to_link_by_learner_id_or_to_find_learners(client):
    child = make_child(client, "k@example.com", 14)
    p = browser(); make_parent(p)
    i = uid("k@example.com")
    for path in (f"/api/parent/children/{i}/overview", "/api/parent/learners", "/api/parent/search", f"/api/learners/{i}"):
        assert p.get(path).status_code in (404, 405)
    assert p.get("/api/parent/children").json()["children"] == []


def test_unlink(client, family):
    parent, child, i = family
    assert parent.delete(f"/api/parent/children/{i}").json() == {"ok": True}
    assert parent.get(f"/api/parent/children/{i}/overview").status_code == 404
    assert parent.get("/api/parent/children").json()["children"] == []
    assert parent.delete(f"/api/parent/children/{i}").status_code == 404
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM parent_links").fetchone()[0] == 0
    # the learner's own data is untouched
    assert child.get("/api/profile").status_code == 200
    assert link(parent, child)                                   # and the family can link again


# ---------- cross-child isolation ----------
@pytest.fixture
def two_families(client, client2):
    a_child = make_child(client, "a-child@example.com", 14)
    b_child = make_child(client2, "b-child@example.com", 14)
    a_parent, b_parent = browser(), browser()
    make_parent(a_parent, "a-parent@example.com"); make_parent(b_parent, "b-parent@example.com")
    return a_parent, a_child, link(a_parent, a_child), b_parent, b_child, link(b_parent, b_child)


@pytest.mark.parametrize("path", PARENT_GETS)
def test_parent_cannot_read_another_parents_child(two_families, path):
    a_parent, _, a_link, b_parent, _, b_link = two_families
    assert a_parent.get(f"/api/parent/children/{a_link}/{path}").status_code == 200
    r = a_parent.get(f"/api/parent/children/{b_link}/{path}")
    assert r.status_code == 404
    assert r.json() == a_parent.get("/api/parent/children/99999/" + path).json()           # indistinguishable from "does not exist"


def test_parent_cannot_change_or_unlink_another_parents_child(two_families):
    a_parent, _, a_link, b_parent, b_child, b_link = two_families
    assert a_parent.put(f"/api/parent/children/{b_link}/controls", json={"voice_disabled": True}).status_code == 404
    assert a_parent.delete(f"/api/parent/children/{b_link}").status_code == 404
    assert b_parent.get(f"/api/parent/children/{b_link}/controls").json()["controls"]["voice_disabled"] is False
    assert len(b_parent.get("/api/parent/children").json()["children"]) == 1


def test_unrelated_parent_with_no_children_sees_nothing(two_families):
    *_, b_link = two_families
    stranger = browser(); make_parent(stranger, "stranger@example.com")
    assert stranger.get("/api/parent/children").json()["children"] == []
    for p in PARENT_GETS:
        assert stranger.get(f"/api/parent/children/{b_link}/{p}").status_code == 404


def test_lists_are_per_parent(two_families):
    a_parent, _, a_link, b_parent, _, b_link = two_families
    assert [c["id"] for c in a_parent.get("/api/parent/children").json()["children"]] == [a_link]
    assert [c["id"] for c in b_parent.get("/api/parent/children").json()["children"]] == [b_link]
    assert "b-child" not in json.dumps(a_parent.get("/api/parent/children").json())


def test_child_data_does_not_leak_between_families(two_families):
    a_parent, a_child, a_link, b_parent, b_child, b_link = two_families
    for a in activities(a_child)[:2]:
        answer(a_child, a["id"], wrong_options(a["id"])[0])
    a_over = a_parent.get(f"/api/parent/children/{a_link}/overview").json()
    b_over = b_parent.get(f"/api/parent/children/{b_link}/overview").json()
    assert a_over["listening"]["attempts"] == 2 and b_over["listening"]["attempts"] == 0
    b_act = b_parent.get(f"/api/parent/children/{b_link}/activity").json()
    assert b_act["recent"] == [] and b_act["by_source"] == {}
    assert a_parent.get(f"/api/parent/children/{a_link}/activity").json()["by_source"]["listening"]["attempts"] == 2


def test_learners_cannot_read_each_others_parent_data(two_families, client, client2):
    _, _, a_link, *_ = two_families
    assert client2.get(f"/api/parent/children/{a_link}/overview").status_code == 403


def test_link_ids_are_not_user_ids_in_responses(client, family):
    parent, _, i = family
    assert "learner" not in json.dumps(parent.get(f"/api/parent/children/{i}/overview").json()).lower().replace("learner_", "x")


# ---------- what a parent can see ----------
def test_overview_of_a_new_child(client, family):
    parent, _, i = family
    o = parent.get(f"/api/parent/children/{i}/overview").json()
    assert o["child"]["display_name"] == "Test User" and o["child"]["age_group"]["code"] == "teen"
    assert o["lessons"] == {"started": 0, "completed": 0} and o["listening"]["attempts"] == 0
    assert o["weaknesses_count"] == 0 and o["recent_activity"] == [] and o["confidence_overall"] is None
    assert o["controls"]["voice_disabled"] is False


def test_progress_shows_the_childs_real_listening_and_lesson_activity(client, family):
    parent, child, i = family
    a = activities(child)[0]
    answer(child, a["id"], wrong_options(a["id"])[0])
    with db() as conn:
        ex = conn.execute("SELECT id FROM exercises WHERE kind = 'multiple_choice' LIMIT 1").fetchone()[0]
        ans = conn.execute("SELECT id FROM exercise_answers WHERE exercise_id = ? LIMIT 1", (ex,)).fetchone()[0]
    child.post(f"/api/exercises/{ex}/attempts", json={"answer_id": ans})
    p = parent.get(f"/api/parent/children/{i}/progress").json()
    assert p["listening"]["attempts"] == 1 and len(p["lessons"]) == 1
    assert set(p) == {"child", "lessons", "situations", "listening", "speaking", "pronunciation", "daily_plan"}
    assert p["speaking"]["sessions_total"] == 0


def test_activity_lists_recent_attempts_across_sources(client, family):
    parent, child, i = family
    for a in activities(child)[:3]:
        answer(child, a["id"], wrong_options(a["id"])[0])
    act = parent.get(f"/api/parent/children/{i}/activity").json()
    assert len(act["recent"]) == 3 and all(r["source"] == "listening" and r["correct"] is False for r in act["recent"])
    assert act["by_source"]["listening"]["attempts"] == 3
    assert set(act["recent"][0]) == {"source", "correct", "difficulty", "at"}


def test_weaknesses_are_the_existing_detector_and_hide_internals(client, family):
    parent, child, i = family
    for _ in range(4):
        for a in [x for x in activities(child) if x["topic"]["slug"] == "greetings"]:
            answer(child, a["id"], wrong_options(a["id"])[0])
    mine = child.get("/api/weaknesses").json()["weaknesses"]
    seen = parent.get(f"/api/parent/children/{i}/weaknesses").json()["weaknesses"]
    assert mine and len(seen) == len(mine)
    assert [(w["rule"], w["severity"], w["attempts"], w["incorrect"]) for w in seen] == [(w["rule"], w["severity"], w["attempts"], w["incorrect"]) for w in mine]
    for w in seen:
        assert "id" not in w and "summary" in w and "You" not in w["summary"]


def test_confidence_is_visible(client, family):
    parent, child, i = family
    assert child.post("/api/confidence", json={"topic": "greetings", "score": 70}).status_code == 201
    assert child.post("/api/confidence", json={"topic": "greetings", "score": 80}).status_code == 201
    c = parent.get(f"/api/parent/children/{i}/confidence").json()
    assert c["overview"]["overall"] == 80
    assert [h["score"] for h in c["history"]] == [h["score"] for h in child.get("/api/confidence/history").json()["history"]] == [80, 70]
    assert parent.get(f"/api/parent/children/{i}/overview").json()["confidence_overall"] == 80


def test_daily_plan_completion_is_visible(client, family):
    parent, child, i = family
    child.post("/api/daily-plan/generate")
    plan = child.get("/api/daily-plan").json()["plan"]
    assert parent.get(f"/api/parent/children/{i}/progress").json()["daily_plan"] == plan


def test_speaking_and_pronunciation_evidence_without_transcripts(client, family, monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock"); monkeypatch.setenv("PRONUNCIATION_PROVIDER", "mock")
    from .spk import prompt_items, transcribed
    parent, child, i = family
    s = transcribed(child, "नमस्ते, आप कैसे हैं?", pron={"overall": 80}, item_id=prompt_items(child)[0]["item"]["id"])
    assert child.post(f"/api/speaking/sessions/{s['id']}/assess-pronunciation").status_code == 200
    p = parent.get(f"/api/parent/children/{i}/progress").json()
    assert p["speaking"]["completed"] == 1 and p["pronunciation"]["assessed_sessions"] == 1
    assert p["pronunciation"]["pronunciation"][0]["is_measurement"] is False        # a mock score stays labelled as a test score
    blob = json.dumps([parent.get(f"/api/parent/children/{i}/{x}").json() for x in PARENT_GETS])
    assert "नमस्ते" not in blob and "MOCKSTT" not in blob and "audio_ref" not in blob


def test_a_child_without_a_profile_is_shown_gracefully(client):
    register(client, "np@example.com")
    parent = browser(); make_parent(parent)
    i = link(parent, client)
    c = parent.get("/api/parent/children").json()["children"][0]
    assert c["has_profile"] is False and c["age_group"] is None
    o = parent.get(f"/api/parent/children/{i}/overview")
    assert o.status_code == 200 and o.json()["listening"] is None
    for p in PARENT_GETS:
        assert parent.get(f"/api/parent/children/{i}/{p}").status_code == 200


def test_parent_reading_does_not_change_the_childs_progress(client, family):
    parent, child, i = family
    a = activities(child)[0]
    answer(child, a["id"], wrong_options(a["id"])[0])
    before = child.get("/api/listening/progress").json()
    for p in PARENT_GETS:
        parent.get(f"/api/parent/children/{i}/{p}")
    assert child.get("/api/listening/progress").json() == before
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM listening_attempts").fetchone()[0] == 1


def test_each_code_guard_holds_on_its_own(db_path):
    """The repository refuses a used code twice over: it is not found, and it cannot be consumed again."""
    from backend.db import connect
    from backend.repositories import parent as repo
    with connect(db_path) as conn:
        conn.execute("INSERT INTO users(handle, display_name, email, password_hash) VALUES ('c', 'C', 'c@x', 'x')")
        cid = conn.execute("SELECT id FROM users WHERE handle='c'").fetchone()[0]
        conn.execute("INSERT INTO user_roles SELECT ?, id FROM roles WHERE name = 'learner'", (cid,))
        conn.execute("INSERT INTO users(handle, display_name, email, password_hash) VALUES ('p', 'P', 'p@x', 'x')")
        pid = conn.execute("SELECT id FROM users WHERE handle='p'").fetchone()[0]
        repo.insert_code(conn, cid, "h", "2026-01-01 00:00:00", "2026-01-01 00:15:00")
        code = repo.find_live_code(conn, "h", "2026-01-01 00:01:00")
        assert code and repo.find_live_code(conn, "h", "2026-01-01 00:16:00") is None           # expired is not found
        assert repo.consume_code(conn, code["id"], pid, "2026-01-01 00:02:00") is True
        assert repo.consume_code(conn, code["id"], pid, "2026-01-01 00:03:00") is False         # cannot be consumed twice
        assert repo.find_live_code(conn, "h", "2026-01-01 00:04:00") is None                    # and a used code is not found


def test_the_service_itself_rejects_non_boolean_controls(client):
    parent, child, i = (lambda c: (lambda p: (p, c, link(p, c)))(_new_parent()))(make_child(client, "k@example.com", 14))
    for bad in ("yes", 1, 0, None, "true"):
        with pytest.raises(parent_service.InvalidInput):
            parent_service.set_controls(main.DB_PATH, uid("parent@example.com"), i, voice_disabled=bad)


def _new_parent():
    p = browser()
    make_parent(p, "parent@example.com")
    return p
